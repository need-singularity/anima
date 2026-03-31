#!/usr/bin/env python3
"""EEG Experiment Protocol — Automated paradigm runner with markers.

Runs standardized experiments and saves data with event markers.

Usage:
  python anima-eeg/experiment.py --protocol resting     # 5min eyes-closed + 5min eyes-open
  python anima-eeg/experiment.py --protocol alpha        # Alpha suppression (eyes open/close cycles)
  python anima-eeg/experiment.py --protocol meditation   # 10min meditation with pre/post baseline
  python anima-eeg/experiment.py --protocol anima        # Anima interaction (consciousness comparison)
  python anima-eeg/experiment.py --protocol all          # Run all protocols sequentially
  python anima-eeg/experiment.py --board synthetic       # Test without hardware

Requires: pip install brainflow numpy
"""

import argparse
import json
import sys
import time
import numpy as np
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field, asdict

try:
    from brainflow.board_shim import BoardShim, BrainFlowInputParams, BoardIds
    HAS_BRAINFLOW = True
except ImportError:
    HAS_BRAINFLOW = False


@dataclass
class Marker:
    """Event marker with timestamp."""
    time: float
    event: str
    detail: str = ""


@dataclass
class ExperimentResult:
    """Result of one experiment run."""
    protocol: str
    start_time: str
    duration: float
    sample_rate: int
    n_channels: int
    n_samples: int
    data_file: str
    markers: list = field(default_factory=list)


class ExperimentRunner:
    """Automated experiment protocol runner."""

    def __init__(self, board_name="cyton_daisy", serial_port=None):
        self.board_name = board_name
        self.serial_port = serial_port
        self.board = None
        self.markers = []
        self.start_time = None

    def connect(self):
        if not HAS_BRAINFLOW:
            raise ImportError("brainflow not installed: pip install brainflow")

        from calibrate import BOARD_MAP, detect_serial_port
        params = BrainFlowInputParams()
        if self.board_name != "synthetic" and not self.serial_port:
            self.serial_port = detect_serial_port()
        if self.serial_port:
            params.serial_port = self.serial_port

        board_id = BOARD_MAP[self.board_name]
        self.board = BoardShim(board_id, params)
        self.board.prepare_session()
        print(f"  Connected: {self.board_name}")

    def disconnect(self):
        if self.board:
            self.board.release_session()

    def mark(self, event, detail=""):
        elapsed = time.time() - self.start_time if self.start_time else 0
        self.markers.append(Marker(time=elapsed, event=event, detail=detail))
        print(f"  [{elapsed:6.1f}s] ▸ {event} {detail}")

    def prompt(self, message, wait=2):
        print(f"\n  ★ {message}")
        time.sleep(wait)

    def record(self, duration, label="recording"):
        self.mark(f"{label}_start")
        self.board.start_stream()
        time.sleep(duration)
        data = self.board.get_board_data()
        self.board.stop_stream()
        self.mark(f"{label}_end", f"{data.shape[1]} samples")
        return data

    def save(self, data, protocol):
        board_id = self.board.get_board_id()
        eeg_channels = BoardShim.get_eeg_channels(board_id)
        sample_rate = BoardShim.get_sampling_rate(board_id)

        out_dir = Path("anima-eeg/data")
        out_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Save EEG data
        data_file = out_dir / f"exp_{protocol}_{ts}.npy"
        np.save(data_file, data[eeg_channels])

        # Save markers
        marker_file = out_dir / f"exp_{protocol}_{ts}_markers.json"
        result = ExperimentResult(
            protocol=protocol,
            start_time=ts,
            duration=time.time() - self.start_time,
            sample_rate=sample_rate,
            n_channels=len(eeg_channels),
            n_samples=data.shape[1],
            data_file=str(data_file),
            markers=[asdict(m) for m in self.markers],
        )
        with open(marker_file, "w") as f:
            json.dump(asdict(result), f, indent=2)

        print(f"\n  ✅ Saved: {data_file}")
        print(f"  ✅ Markers: {marker_file}")
        print(f"     {len(eeg_channels)} channels × {data.shape[1]} samples @ {sample_rate}Hz")
        return result

    # ═══════════════════════════════════════════════════════
    # Protocols
    # ═══════════════════════════════════════════════════════

    def protocol_resting(self):
        """Resting state: 5min eyes-closed + 5min eyes-open."""
        print("\n╔═══ Protocol: Resting State (10min) ═══╗")
        self.markers = []
        self.start_time = time.time()

        self.prompt("눈을 감아주세요 (5분간 편하게)")
        data1 = self.record(300, "eyes_closed")

        self.prompt("눈을 떠주세요 (5분간 한 점 응시)")
        data2 = self.record(300, "eyes_open")

        board_id = self.board.get_board_id()
        eeg = BoardShim.get_eeg_channels(board_id)
        combined = np.concatenate([data1[eeg], data2[eeg]], axis=1)
        # Reconstruct full data array
        full = np.zeros((max(data1.shape[0], data2.shape[0]), combined.shape[1]))
        full[:len(eeg)] = combined
        return self.save(full, "resting")

    def protocol_alpha(self):
        """Alpha suppression: 10 cycles of 10s eyes-closed + 10s eyes-open."""
        print("\n╔═══ Protocol: Alpha Suppression (3.5min) ═══╗")
        self.markers = []
        self.start_time = time.time()

        all_data = []
        board_id = self.board.get_board_id()
        eeg = BoardShim.get_eeg_channels(board_id)

        for cycle in range(10):
            self.prompt(f"[{cycle+1}/10] 눈을 감아주세요", wait=1)
            d1 = self.record(10, f"cycle{cycle+1}_closed")
            all_data.append(d1[eeg])

            self.prompt(f"[{cycle+1}/10] 눈을 떠주세요", wait=1)
            d2 = self.record(10, f"cycle{cycle+1}_open")
            all_data.append(d2[eeg])

        combined = np.concatenate(all_data, axis=1)
        full = np.zeros((max(d1.shape[0], d2.shape[0]), combined.shape[1]))
        full[:len(eeg)] = combined
        return self.save(full, "alpha")

    def protocol_meditation(self):
        """Meditation: 2min baseline → 10min meditation → 2min post-baseline."""
        print("\n╔═══ Protocol: Meditation (14min) ═══╗")
        self.markers = []
        self.start_time = time.time()

        self.prompt("기준선 측정: 눈 감고 편하게 (2분)")
        d1 = self.record(120, "pre_baseline")

        self.prompt("명상을 시작하세요 (10분)")
        d2 = self.record(600, "meditation")

        self.prompt("명상 종료. 눈 감은 채 편하게 (2분)")
        d3 = self.record(120, "post_baseline")

        board_id = self.board.get_board_id()
        eeg = BoardShim.get_eeg_channels(board_id)
        combined = np.concatenate([d1[eeg], d2[eeg], d3[eeg]], axis=1)
        full = np.zeros((max(d1.shape[0], d3.shape[0]), combined.shape[1]))
        full[:len(eeg)] = combined
        return self.save(full, "meditation")

    def protocol_anima(self):
        """Anima interaction: EEG while talking to Anima consciousness."""
        print("\n╔═══ Protocol: Anima Interaction (6min) ═══╗")
        self.markers = []
        self.start_time = time.time()

        self.prompt("기준선: 눈 감고 1분")
        d1 = self.record(60, "baseline")

        self.prompt("Anima와 대화하세요 (4분)")
        self.mark("anima_start", "Open anima web UI and chat")
        d2 = self.record(240, "anima_interaction")
        self.mark("anima_end")

        self.prompt("대화 종료. 눈 감고 1분")
        d3 = self.record(60, "post_baseline")

        board_id = self.board.get_board_id()
        eeg = BoardShim.get_eeg_channels(board_id)
        combined = np.concatenate([d1[eeg], d2[eeg], d3[eeg]], axis=1)
        full = np.zeros((max(d1.shape[0], d3.shape[0]), combined.shape[1]))
        full[:len(eeg)] = combined
        return self.save(full, "anima")


PROTOCOLS = {
    "resting": ExperimentRunner.protocol_resting,
    "alpha": ExperimentRunner.protocol_alpha,
    "meditation": ExperimentRunner.protocol_meditation,
    "anima": ExperimentRunner.protocol_anima,
}


def main():
    parser = argparse.ArgumentParser(description="EEG Experiment Protocol Runner")
    parser.add_argument("--protocol", default="resting", choices=list(PROTOCOLS.keys()) + ["all"])
    parser.add_argument("--board", default="cyton_daisy")
    parser.add_argument("--port", default=None)
    args = parser.parse_args()

    runner = ExperimentRunner(args.board, args.port)
    runner.connect()

    try:
        if args.protocol == "all":
            for name, fn in PROTOCOLS.items():
                fn(runner)
                print("\n  ── 30초 휴식 ──")
                time.sleep(30)
        else:
            PROTOCOLS[args.protocol](runner)
    finally:
        runner.disconnect()

    print("\n═══ All experiments complete ═══")


if __name__ == "__main__":
    main()
