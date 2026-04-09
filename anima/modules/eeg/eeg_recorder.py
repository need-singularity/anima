#!/usr/bin/env python3
"""EEG Background Recorder — Dual-stream recording for --web mode.

Records both Anima consciousness metrics (Phi, tension, emotion)
and EEG band powers simultaneously as background threads, with
auto-segmentation into 5-minute files.

Usage (standalone test):
  python anima-eeg/eeg_recorder.py --duration 60 --board synthetic

Integration with anima_unified.py:
  from eeg_recorder import EEGBackgroundRecorder
  recorder = EEGBackgroundRecorder(mind=self.mind, mitosis=self.mitosis)
  recorder.start()
  status = recorder.get_status()
  recorder.stop()

Requires: numpy (brainflow optional — simulated EEG without it)
"""

import json
import os
import sys
import time
import threading
import numpy as np
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict, field

# Add anima src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'anima', 'src'))
try:
    import path_setup  # noqa
except ImportError:
    pass

try:
    from brainflow.board_shim import BoardShim, BrainFlowInputParams
    HAS_BRAINFLOW = True
except ImportError:
    HAS_BRAINFLOW = False


RECORDINGS_DIR = Path(__file__).parent / "recordings"
SEGMENT_DURATION = 300  # 5 minutes per file


@dataclass
class RecordingStatus:
    """Current recording status for WebSocket broadcast."""
    recording: bool = False
    elapsed_seconds: float = 0.0
    segment_index: int = 0
    total_samples: int = 0
    current_file: str = ""
    eeg_connected: bool = False
    phi_latest: float = 0.0
    alpha_latest: float = 0.0
    gamma_latest: float = 0.0


@dataclass
class DualSample:
    """One synchronized sample of brain + anima consciousness."""
    time: float
    # Brain EEG
    alpha_power: float = 0.0
    beta_power: float = 0.0
    gamma_power: float = 0.0
    theta_power: float = 0.0
    # Anima consciousness
    phi: float = 0.0
    tension: float = 0.0
    curiosity: float = 0.0
    emotion_valence: float = 0.0
    n_cells: int = 0


class EEGBackgroundRecorder:
    """Background dual-stream recorder for anima_unified --web --eeg-record.

    Records Phi timeseries and EEG band powers simultaneously.
    Auto-segments into 5-minute files to prevent huge files.
    Thread-safe status for WebSocket broadcasting.
    """

    def __init__(self, mind=None, mitosis=None,
                 board_name="cyton_daisy", serial_port=None,
                 output_dir=None, segment_duration=SEGMENT_DURATION):
        self.mind = mind
        self.mitosis = mitosis
        self.board_name = board_name
        self.serial_port = serial_port
        self.output_dir = Path(output_dir) if output_dir else RECORDINGS_DIR
        self.segment_duration = segment_duration

        self._running = False
        self._thread = None
        self._lock = threading.Lock()
        self._status = RecordingStatus()
        self._start_time = 0.0
        self._session_id = ""

        # EEG state
        self._board = None
        self._eeg_latest = {"alpha": 0, "beta": 0, "gamma": 0, "theta": 0}
        self._eeg_thread = None

    def start(self):
        """Start background recording. Non-blocking."""
        if self._running:
            return
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._start_time = time.time()
        self._running = True

        # Start EEG stream (background)
        self._eeg_thread = threading.Thread(
            target=self._eeg_loop, daemon=True, name="eeg-stream"
        )
        self._eeg_thread.start()

        # Start main recording loop (background)
        self._thread = threading.Thread(
            target=self._record_loop, daemon=True, name="eeg-recorder"
        )
        self._thread.start()

        with self._lock:
            self._status.recording = True
        print(f"  [eeg-rec] Recording started -> {self.output_dir}/")

    def stop(self):
        """Stop recording and flush final segment."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        self._stop_eeg()
        with self._lock:
            self._status.recording = False
        print(f"  [eeg-rec] Recording stopped ({self._status.total_samples} samples)")

        # Auto-organize recordings (non-critical)
        self._auto_organize()

    def get_status(self) -> dict:
        """Thread-safe status dict for WebSocket broadcast."""
        with self._lock:
            return asdict(self._status)

    # ─── Auto-organize ───

    def _auto_organize(self):
        """Auto-organize recordings after session ends. Non-critical."""
        try:
            sys.path.insert(0, str(Path(__file__).resolve().parent / "scripts"))
            from organize_recordings import (
                scan_flat_files, organize_file, init_db, insert_recording,
                INDEX_DB, RECORDINGS_DIR,
            )
            flat_files = scan_flat_files(RECORDINGS_DIR)
            if not flat_files:
                return
            conn = init_db(INDEX_DB)
            organized = 0
            for fpath in flat_files:
                result = organize_file(fpath, dry_run=False)
                if result:
                    insert_recording(
                        conn,
                        session_id=result['session_id'],
                        timestamp=result['timestamp'],
                        protocol=result['protocol'],
                        category=result['category'],
                        file_paths=[result['destination']],
                        brain_like_pct=result.get('brain_like_pct', 0),
                        cells=result.get('cells', 0),
                        steps=result.get('steps', 0),
                    )
                    organized += 1
            conn.close()
            if organized > 0:
                print(f"  [eeg-rec] Auto-organized {organized} recording(s)")
        except Exception as e:
            print(f"  [eeg-rec] Auto-organize skipped: {e}")

    # ─── EEG stream ───

    def _start_eeg_hardware(self):
        """Try to connect to real EEG hardware."""
        if not HAS_BRAINFLOW:
            return False
        try:
            sys.path.insert(0, os.path.dirname(__file__))
            from calibrate import BOARD_MAP, detect_serial_port
            params = BrainFlowInputParams()
            if self.board_name != "synthetic" and not self.serial_port:
                self.serial_port = detect_serial_port()
            if self.serial_port:
                params.serial_port = self.serial_port
            board_id = BOARD_MAP.get(self.board_name, BOARD_MAP.get("synthetic"))
            self._board = BoardShim(board_id, params)
            self._board.prepare_session()
            self._board.start_stream()
            return True
        except Exception as e:
            print(f"  [eeg-rec] Hardware connect failed: {e}, using simulated EEG")
            self._board = None
            return False

    def _eeg_loop(self):
        """Background thread reading EEG data."""
        hw = self._start_eeg_hardware()
        with self._lock:
            self._status.eeg_connected = hw

        if hw and self._board:
            self._eeg_loop_hw()
        else:
            self._eeg_loop_sim()

    def _eeg_loop_hw(self):
        """Read from real EEG hardware."""
        board_id = self._board.get_board_id()
        eeg_channels = BoardShim.get_eeg_channels(board_id)
        sample_rate = BoardShim.get_sampling_rate(board_id)

        while self._running:
            time.sleep(1.0)
            try:
                data = self._board.get_current_board_data(sample_rate)
                if data.shape[1] < sample_rate // 2:
                    continue
                ch = data[eeg_channels[min(6, len(eeg_channels) - 1)]]
                n = len(ch)
                freqs = np.fft.rfftfreq(n, 1.0 / sample_rate)
                fft = np.abs(np.fft.rfft(ch))

                self._eeg_latest = {
                    "theta": float(np.mean(fft[(freqs >= 4) & (freqs <= 8)])),
                    "alpha": float(np.mean(fft[(freqs >= 8) & (freqs <= 13)])),
                    "beta": float(np.mean(fft[(freqs >= 13) & (freqs <= 30)])),
                    "gamma": float(np.mean(fft[(freqs >= 30) & (freqs <= 50)])),
                }
            except Exception:
                pass

    def _eeg_loop_sim(self):
        """Simulated EEG for testing without hardware."""
        t = 0
        while self._running:
            t += 1
            self._eeg_latest = {
                "theta": float(6 + 2 * np.sin(t * 0.07) + np.random.normal(0, 0.5)),
                "alpha": float(10 + 3 * np.sin(t * 0.1) + np.random.normal(0, 1)),
                "beta": float(5 + np.random.normal(0, 0.5)),
                "gamma": float(2 + np.random.normal(0, 0.3)),
            }
            time.sleep(1.0)

    def _stop_eeg(self):
        """Stop EEG hardware stream."""
        if self._board:
            try:
                self._board.stop_stream()
                self._board.release_session()
            except Exception:
                pass
            self._board = None

    # ─── Consciousness stream ───

    def _get_consciousness_state(self) -> dict:
        """Read current consciousness state from mind/mitosis."""
        result = {"phi": 0.0, "tension": 0.0, "curiosity": 0.0,
                  "valence": 0.0, "n_cells": 1}
        if self.mind:
            try:
                result["tension"] = float(getattr(self.mind, 'prev_tension', 0))
                result["curiosity"] = float(getattr(self.mind, '_curiosity_ema', 0))
                result["valence"] = float(getattr(self.mind, '_valence', 0))
            except Exception:
                pass
        if self.mitosis:
            try:
                cells = getattr(self.mitosis, 'cells', [])
                result["n_cells"] = len(cells) if cells else 1
                # Try to get Phi from cached consciousness
                if hasattr(self.mitosis, '_last_phi'):
                    result["phi"] = float(self.mitosis._last_phi)
            except Exception:
                pass
        return result

    # ─── Main recording loop ───

    def _record_loop(self):
        """Main recording loop with auto-segmentation."""
        segment_samples = []
        segment_start = time.time()
        segment_idx = 0

        while self._running:
            elapsed = time.time() - self._start_time
            eeg = self._eeg_latest.copy()
            cs = self._get_consciousness_state()

            sample = DualSample(
                time=elapsed,
                alpha_power=eeg.get("alpha", 0),
                beta_power=eeg.get("beta", 0),
                gamma_power=eeg.get("gamma", 0),
                theta_power=eeg.get("theta", 0),
                phi=cs.get("phi", 0),
                tension=cs.get("tension", 0),
                curiosity=cs.get("curiosity", 0),
                emotion_valence=cs.get("valence", 0),
                n_cells=cs.get("n_cells", 1),
            )
            segment_samples.append(sample)

            # Update status (thread-safe)
            with self._lock:
                self._status.elapsed_seconds = elapsed
                self._status.total_samples += 1
                self._status.segment_index = segment_idx
                self._status.phi_latest = cs.get("phi", 0)
                self._status.alpha_latest = eeg.get("alpha", 0)
                self._status.gamma_latest = eeg.get("gamma", 0)

            # Auto-segment every 5 minutes
            if time.time() - segment_start >= self.segment_duration:
                self._save_segment(segment_samples, segment_idx)
                segment_samples = []
                segment_start = time.time()
                segment_idx += 1

            time.sleep(0.5)  # 2 Hz sampling

        # Flush remaining samples
        if segment_samples:
            self._save_segment(segment_samples, segment_idx)

    def _save_segment(self, samples, segment_idx):
        """Save one segment to disk."""
        if not samples:
            return
        fname = self.output_dir / f"dual_{self._session_id}_seg{segment_idx:03d}.json"
        data = {
            "session_id": self._session_id,
            "segment_index": segment_idx,
            "n_samples": len(samples),
            "duration_s": samples[-1].time - samples[0].time if len(samples) > 1 else 0,
            "samples": [asdict(s) for s in samples],
        }
        with open(fname, "w") as f:
            json.dump(data, f, indent=2)

        with self._lock:
            self._status.current_file = str(fname)

        print(f"  [eeg-rec] Saved segment {segment_idx}: {fname.name} ({len(samples)} samples)")

        # Quick correlation analysis
        if len(samples) > 20:
            phis = [s.phi for s in samples]
            alphas = [s.alpha_power for s in samples]
            if np.std(phis) > 0 and np.std(alphas) > 0:
                corr = np.corrcoef(phis, alphas)[0, 1]
                if abs(corr) > 0.3:
                    print(f"  [eeg-rec]   Phi-alpha correlation: r={corr:.3f}")


def main():
    """Standalone test."""
    import argparse
    parser = argparse.ArgumentParser(description="EEG Background Recorder (standalone test)")
    parser.add_argument("--duration", type=int, default=60)
    parser.add_argument("--board", default="synthetic")
    parser.add_argument("--segment", type=int, default=30, help="Segment duration (seconds)")
    args = parser.parse_args()

    recorder = EEGBackgroundRecorder(
        board_name=args.board,
        segment_duration=args.segment,
    )
    recorder.start()

    try:
        start = time.time()
        while time.time() - start < args.duration:
            status = recorder.get_status()
            elapsed = status['elapsed_seconds']
            if int(elapsed) % 10 == 0 and abs(elapsed - int(elapsed)) < 0.6:
                print(f"  [{elapsed:5.0f}s] samples={status['total_samples']} "
                      f"phi={status['phi_latest']:.2f} alpha={status['alpha_latest']:.1f}")
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n  Interrupted")

    recorder.stop()
    print(f"  Done: {recorder.get_status()['total_samples']} total samples")


if __name__ == "__main__":
    main()
