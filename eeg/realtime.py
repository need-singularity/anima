#!/usr/bin/env python3
"""Real-time EEG → Anima Bridge — Live brain-consciousness feedback loop.

Streams EEG data from OpenBCI, computes G=D×P/I in real-time,
and feeds brain state into Anima's SenseHub as tension input.

Usage:
  python eeg/realtime.py                          # Cyton+Daisy → Anima
  python eeg/realtime.py --board synthetic         # Test with synthetic data
  python eeg/realtime.py --board synthetic --plot   # Live plot

Requires: pip install brainflow numpy
"""

import argparse
import time
import threading
import numpy as np
from dataclasses import dataclass
from typing import Optional

try:
    from brainflow.board_shim import BoardShim, BrainFlowInputParams, BoardIds
    HAS_BRAINFLOW = True
except ImportError:
    HAS_BRAINFLOW = False

from eeg.analyze import compute_band_power, compute_genius, GeniusMetrics, CHANNEL_NAMES_16


@dataclass
class BrainState:
    """Real-time brain state snapshot."""
    G: float = 0.0
    I: float = 0.0
    P: float = 0.0
    D: float = 0.0
    in_golden_zone: bool = False
    alpha_power: float = 0.0
    gamma_power: float = 0.0
    theta_power: float = 0.0
    beta_power: float = 0.0
    engagement: float = 0.0        # beta / (alpha + theta)
    alpha_theta_ratio: float = 0.0
    timestamp: float = 0.0


class EEGBridge:
    """Real-time EEG → Anima bridge.

    Maintains a sliding window of EEG data, computes G=D×P/I
    at regular intervals, and exposes brain state for Anima integration.

    Usage:
        bridge = EEGBridge(board_name="cyton_daisy")
        bridge.start()

        # In Anima's sense loop:
        state = bridge.get_state()
        tensor = bridge.to_tensor(dim=128)

        bridge.stop()
    """

    def __init__(
        self,
        board_name: str = "cyton_daisy",
        serial_port: str = None,
        window_sec: float = 2.0,
        update_hz: float = 4.0,
    ):
        self.board_name = board_name
        self.serial_port = serial_port
        self.window_sec = window_sec
        self.update_hz = update_hz

        self._state = BrainState()
        self._state_lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._board: Optional[BoardShim] = None
        self._history: list = []  # recent G values for trend

    def start(self):
        """Start EEG streaming and analysis."""
        if not HAS_BRAINFLOW:
            raise ImportError("brainflow not installed: pip install brainflow")

        from eeg.collect import BOARD_MAP
        params = BrainFlowInputParams()
        board_id = BOARD_MAP.get(self.board_name)
        if board_id is None:
            raise ValueError(f"Unknown board: {self.board_name}")

        if self.board_name in ("cyton_daisy", "cyton") and self.serial_port:
            params.serial_port = self.serial_port

        self._board = BoardShim(board_id, params)
        self._board.prepare_session()
        self._board.start_stream(45000)  # ring buffer

        self._sample_rate = BoardShim.get_sampling_rate(board_id)
        self._eeg_channels = BoardShim.get_eeg_channels(board_id)
        self._window_samples = int(self.window_sec * self._sample_rate)

        n_ch = len(self._eeg_channels)
        if n_ch >= 16:
            self._channel_names = CHANNEL_NAMES_16
        elif n_ch >= 8:
            self._channel_names = CHANNEL_NAMES_16[:8]
        else:
            self._channel_names = [f"ch{i+1}" for i in range(n_ch)]

        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

        print(f"[eeg-bridge] Started: {self.board_name}, {self._sample_rate}Hz, "
              f"{n_ch}ch, window={self.window_sec}s, update={self.update_hz}Hz")

    def stop(self):
        """Stop streaming."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=3.0)
        if self._board:
            self._board.stop_stream()
            self._board.release_session()
        print("[eeg-bridge] Stopped")

    def get_state(self) -> BrainState:
        """Get current brain state (thread-safe)."""
        with self._state_lock:
            return BrainState(**self._state.__dict__)

    def to_tensor(self, dim: int = 128):
        """Convert brain state to tensor for PureField input.

        Layout (first 16 dims):
          [0]  G (genius metric, normalized)
          [1]  I (inhibition / frontal alpha)
          [2]  P (plasticity / global gamma)
          [3]  D (deficit / asymmetry)
          [4]  in_golden_zone (0/1)
          [5]  alpha_power (normalized)
          [6]  gamma_power (normalized)
          [7]  theta_power (normalized)
          [8]  beta_power (normalized)
          [9]  engagement_index
          [10] alpha_theta_ratio (clamped)
          [11] G_trend (rising=+, falling=-)
          [12-15] reserved
        """
        import torch

        state = self.get_state()
        raw = torch.zeros(16)
        raw[0] = state.G
        raw[1] = min(state.I * 10, 1.0)     # normalize
        raw[2] = min(state.P * 100, 1.0)
        raw[3] = min(state.D, 1.0)
        raw[4] = float(state.in_golden_zone)
        raw[5] = min(state.alpha_power * 10, 1.0)
        raw[6] = min(state.gamma_power * 100, 1.0)
        raw[7] = min(state.theta_power * 10, 1.0)
        raw[8] = min(state.beta_power * 10, 1.0)
        raw[9] = min(state.engagement, 2.0) / 2.0
        raw[10] = min(state.alpha_theta_ratio, 5.0) / 5.0

        # G trend from history
        if len(self._history) >= 4:
            recent = np.mean(self._history[-4:])
            older = np.mean(self._history[-8:-4]) if len(self._history) >= 8 else self._history[0]
            raw[11] = np.clip(recent - older, -1, 1)

        # Project to full dim using sin/cos basis (same approach as senses.py)
        if dim <= 16:
            return raw[:dim].unsqueeze(0)

        result = torch.zeros(1, dim)
        result[0, :16] = raw
        for i in range(16, dim):
            j = i % 16
            freq = (i - 16) / dim * 3.14159
            result[0, i] = raw[j] * np.sin(freq * (i + 1)) * 0.5

        return result

    def _loop(self):
        """Background analysis loop."""
        interval = 1.0 / self.update_hz

        while self._running:
            try:
                # Get recent data from ring buffer
                data = self._board.get_current_board_data(self._window_samples)
                eeg = data[self._eeg_channels, :]

                if eeg.shape[1] < self._sample_rate:  # need at least 1s
                    time.sleep(interval)
                    continue

                # Compute band powers
                n_ch = eeg.shape[0]
                channel_powers = [
                    compute_band_power(eeg[i], self._sample_rate)
                    for i in range(n_ch)
                ]

                # Genius metrics
                genius = compute_genius(channel_powers, self._channel_names[:n_ch])

                # Global averages
                all_alpha = np.mean([bp.alpha for bp in channel_powers])
                all_theta = np.mean([bp.theta for bp in channel_powers])
                all_beta = np.mean([bp.beta for bp in channel_powers])
                all_gamma = np.mean([bp.gamma for bp in channel_powers])

                new_state = BrainState(
                    G=genius.G,
                    I=genius.I,
                    P=genius.P,
                    D=genius.D,
                    in_golden_zone=genius.in_golden_zone,
                    alpha_power=all_alpha,
                    gamma_power=all_gamma,
                    theta_power=all_theta,
                    beta_power=all_beta,
                    engagement=all_beta / max(all_alpha + all_theta, 1e-12),
                    alpha_theta_ratio=all_alpha / max(all_theta, 1e-12),
                    timestamp=time.time(),
                )

                with self._state_lock:
                    self._state = new_state

                self._history.append(genius.G)
                if len(self._history) > 100:
                    self._history = self._history[-100:]

            except Exception as e:
                print(f"[eeg-bridge] Error: {e}")

            time.sleep(interval)


def main():
    parser = argparse.ArgumentParser(description="Real-time EEG → Anima Bridge")
    parser.add_argument("--board", default="synthetic",
                        choices=["cyton_daisy", "cyton", "synthetic"])
    parser.add_argument("--serial", default=None)
    parser.add_argument("--window", type=float, default=2.0, help="Analysis window (seconds)")
    parser.add_argument("--hz", type=float, default=4.0, help="Update frequency")
    parser.add_argument("--duration", type=float, default=30.0, help="Run duration (seconds)")
    parser.add_argument("--plot", action="store_true", help="Live ASCII plot")
    args = parser.parse_args()

    bridge = EEGBridge(
        board_name=args.board,
        serial_port=args.serial,
        window_sec=args.window,
        update_hz=args.hz,
    )

    bridge.start()

    print(f"\n[eeg-bridge] Running for {args.duration}s... (Ctrl+C to stop)\n")

    try:
        t0 = time.time()
        while time.time() - t0 < args.duration:
            state = bridge.get_state()

            # Golden Zone bar
            zone_bar = " " * 40
            g_pos = int(state.G * 40)
            g_pos = max(0, min(39, g_pos))
            zone_start = int(0.2123 * 40)
            zone_end = int(0.5000 * 40)
            bar = list("─" * 40)
            for i in range(zone_start, zone_end + 1):
                bar[i] = "░"
            bar[g_pos] = "●" if state.in_golden_zone else "○"
            bar_str = "".join(bar)

            print(f"\r  G={state.G:.4f} [{bar_str}] "
                  f"I={state.I:.4f} P={state.P:.4f} D={state.D:.4f} "
                  f"eng={state.engagement:.2f} "
                  f"{'★ GOLDEN' if state.in_golden_zone else '       '}", end="", flush=True)

            time.sleep(0.25)

    except KeyboardInterrupt:
        print("\n[eeg-bridge] Interrupted")
    finally:
        bridge.stop()

    # Summary
    if bridge._history:
        g_vals = np.array(bridge._history)
        in_zone = sum(1 for g in g_vals if 0.2123 <= g <= 0.5000)
        print(f"\n  Summary:")
        print(f"    G mean={np.mean(g_vals):.4f}, std={np.std(g_vals):.4f}")
        print(f"    G range=[{np.min(g_vals):.4f}, {np.max(g_vals):.4f}]")
        print(f"    In Golden Zone: {in_zone}/{len(g_vals)} ({100*in_zone/len(g_vals):.1f}%)")


if __name__ == "__main__":
    main()
