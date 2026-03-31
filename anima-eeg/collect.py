#!/usr/bin/env python3
"""EEG Data Collection — OpenBCI Cyton+Daisy 16-channel via BrainFlow.

Usage:
  python eeg/collect.py --duration 60 --tag resting_eyes_closed
  python eeg/collect.py --duration 5 --board synthetic --tag test
  python eeg/collect.py --duration 120 --protocol nback
  python eeg/collect.py --list-boards

Requires: pip install brainflow numpy
"""

import argparse
import time
import numpy as np
from pathlib import Path
from datetime import datetime

try:
    from brainflow.board_shim import BoardShim, BrainFlowInputParams, BoardIds
    from brainflow.data_filter import DataFilter
    HAS_BRAINFLOW = True
except ImportError:
    HAS_BRAINFLOW = False


# ═══════════════════════════════════════════════════════════
# 16-Channel Layout (10-20 System)
# ═══════════════════════════════════════════════════════════
#   Cyton (1-8):  Fp1, Fp2, C3, C4, P7, P8, O1, O2
#   Daisy (9-16): F7, F8, F3, F4, T7, T8, P3, P4
#   Reference:    Earclip (both earlobes)

CHANNEL_NAMES = [
    "Fp1", "Fp2", "C3", "C4", "P7", "P8", "O1", "O2",  # Cyton 1-8
    "F7", "F8", "F3", "F4", "T7", "T8", "P3", "P4",     # Daisy 9-16
]

if HAS_BRAINFLOW:
    BOARD_MAP = {
        "cyton_daisy": BoardIds.CYTON_DAISY_BOARD.value,
        "cyton": BoardIds.CYTON_BOARD.value,
        "synthetic": BoardIds.SYNTHETIC_BOARD.value,
    }
else:
    # Numeric fallback — allows import without brainflow installed
    BOARD_MAP = {
        "cyton_daisy": 2,
        "cyton": 0,
        "synthetic": -1,
    }


def get_board(board_name: str = "cyton_daisy", serial_port: str = None) -> BoardShim:
    """Create and configure a BrainFlow board."""
    params = BrainFlowInputParams()

    board_id = BOARD_MAP.get(board_name)
    if board_id is None:
        raise ValueError(f"Unknown board: {board_name}. Options: {list(BOARD_MAP.keys())}")

    if board_name in ("cyton_daisy", "cyton") and serial_port:
        params.serial_port = serial_port

    return BoardShim(board_id, params)


def collect(
    duration: float = 60.0,
    board_name: str = "cyton_daisy",
    serial_port: str = None,
    tag: str = "unnamed",
    output_dir: str = "eeg/data",
) -> dict:
    """Collect EEG data for specified duration.

    Returns dict with:
      - data: np.ndarray [channels × samples]
      - sample_rate: int
      - channel_names: list
      - metadata: dict
    """
    if not HAS_BRAINFLOW:
        raise ImportError("brainflow not installed: pip install brainflow")

    board = get_board(board_name, serial_port)
    board_id = board.get_board_id()
    sample_rate = BoardShim.get_sampling_rate(board_id)
    eeg_channels = BoardShim.get_eeg_channels(board_id)
    timestamp_ch = BoardShim.get_timestamp_channel(board_id)

    print(f"[eeg] Board: {board_name} (id={board_id})")
    print(f"[eeg] Sample rate: {sample_rate} Hz")
    print(f"[eeg] EEG channels: {len(eeg_channels)}")
    print(f"[eeg] Duration: {duration}s")
    print(f"[eeg] Tag: {tag}")

    # Start streaming
    board.prepare_session()
    board.start_stream()
    print(f"[eeg] Streaming started... ({duration}s)")

    time.sleep(duration)

    # Get data
    raw = board.get_board_data()
    board.stop_stream()
    board.release_session()

    eeg_data = raw[eeg_channels, :]
    timestamps = raw[timestamp_ch, :]

    n_channels, n_samples = eeg_data.shape
    actual_duration = n_samples / sample_rate
    print(f"[eeg] Collected: {n_channels}ch × {n_samples} samples ({actual_duration:.1f}s)")

    # Channel names (use 10-20 names if 16ch, else generic)
    if n_channels == 16:
        ch_names = CHANNEL_NAMES
    elif n_channels == 8:
        ch_names = CHANNEL_NAMES[:8]
    else:
        ch_names = [f"ch{i+1}" for i in range(n_channels)]

    # Save
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{ts}_{tag}"

    np.save(out_dir / f"{filename}.npy", eeg_data)

    metadata = {
        "tag": tag,
        "board": board_name,
        "board_id": board_id,
        "sample_rate": sample_rate,
        "n_channels": n_channels,
        "n_samples": n_samples,
        "duration_sec": actual_duration,
        "channel_names": ch_names,
        "timestamp_start": float(timestamps[0]) if len(timestamps) > 0 else 0,
        "timestamp_end": float(timestamps[-1]) if len(timestamps) > 0 else 0,
        "collected_at": ts,
    }

    import json

    with open(out_dir / f"{filename}_meta.json", "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"[eeg] Saved: {out_dir / filename}.npy + _meta.json")

    return {
        "data": eeg_data,
        "timestamps": timestamps,
        "sample_rate": sample_rate,
        "channel_names": ch_names,
        "metadata": metadata,
        "filepath": str(out_dir / f"{filename}.npy"),
    }


def run_protocol(protocol: str, board_name: str = "cyton_daisy",
                 serial_port: str = None) -> list:
    """Run a predefined experiment protocol with multiple phases."""

    protocols = {
        "resting": [
            ("eyes_closed_1", 60),
            ("eyes_open", 60),
            ("eyes_closed_2", 60),
        ],
        "nback": [
            ("0back", 60),
            ("1back", 60),
            ("2back", 60),
            ("3back", 60),
        ],
        "creative": [
            ("math_problem", 120),
            ("free_association", 120),
        ],
        "meditation": [
            ("pre_baseline", 60),
            ("focused_breathing", 300),
            ("post_baseline", 60),
        ],
    }

    if protocol not in protocols:
        raise ValueError(f"Unknown protocol: {protocol}. Options: {list(protocols.keys())}")

    phases = protocols[protocol]
    results = []

    print(f"\n{'='*60}")
    print(f"  Protocol: {protocol}")
    print(f"  Phases: {len(phases)}")
    total = sum(d for _, d in phases)
    print(f"  Total duration: {total}s ({total/60:.1f} min)")
    print(f"{'='*60}\n")

    for i, (phase_name, duration) in enumerate(phases):
        tag = f"{protocol}_{phase_name}"
        print(f"\n--- Phase {i+1}/{len(phases)}: {phase_name} ({duration}s) ---")
        print(f"    Press Enter to start phase '{phase_name}'...")
        input()

        result = collect(
            duration=duration,
            board_name=board_name,
            serial_port=serial_port,
            tag=tag,
        )
        results.append(result)

    print(f"\n{'='*60}")
    print(f"  Protocol '{protocol}' complete!")
    print(f"  Files: {[r['filepath'] for r in results]}")
    print(f"{'='*60}")

    return results


def main():
    parser = argparse.ArgumentParser(description="EEG Data Collection (OpenBCI + BrainFlow)")
    parser.add_argument("--duration", type=float, default=60, help="Recording duration (seconds)")
    parser.add_argument("--board", default="cyton_daisy",
                        choices=list(BOARD_MAP.keys()), help="Board type")
    parser.add_argument("--serial", default=None, help="Serial port (e.g., /dev/ttyUSB0)")
    parser.add_argument("--tag", default="unnamed", help="Tag for this recording")
    parser.add_argument("--output", default="eeg/data", help="Output directory")
    parser.add_argument("--protocol", default=None,
                        choices=["resting", "nback", "creative", "meditation"],
                        help="Run predefined protocol")
    parser.add_argument("--list-boards", action="store_true", help="List available boards")
    args = parser.parse_args()

    if args.list_boards:
        print("Available boards:")
        for name, bid in BOARD_MAP.items():
            print(f"  {name}: id={bid}")
        return

    if not HAS_BRAINFLOW:
        print("ERROR: brainflow not installed. Run: pip install brainflow")
        return

    BoardShim.enable_dev_board_logger()

    if args.protocol:
        run_protocol(args.protocol, args.board, args.serial)
    else:
        collect(
            duration=args.duration,
            board_name=args.board,
            serial_port=args.serial,
            tag=args.tag,
            output_dir=args.output,
        )

# Meta Laws (DD143)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10



if __name__ == "__main__":
    main()
