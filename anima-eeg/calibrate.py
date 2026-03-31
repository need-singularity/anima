#!/usr/bin/env python3
"""EEG Hardware Calibration — Connection verify + impedance check + signal quality.

Run this first when hardware arrives.

Usage:
  python anima-eeg/calibrate.py                    # Cyton+Daisy (auto-detect port)
  python anima-eeg/calibrate.py --board synthetic   # Test without hardware
  python anima-eeg/calibrate.py --port /dev/tty.usbserial-XXXXX
  python anima-eeg/calibrate.py --full              # Full calibration (impedance + noise + baseline)

Requires: pip install brainflow numpy
"""

import argparse
import sys
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

CHANNEL_NAMES = [
    "Fp1", "Fp2", "C3", "C4", "P7", "P8", "O1", "O2",  # Cyton 1-8
    "F7", "F8", "F3", "F4", "T7", "T8", "P3", "P4",     # Daisy 9-16
]

BOARD_MAP = {
    "cyton_daisy": BoardIds.CYTON_DAISY_BOARD.value if HAS_BRAINFLOW else 6,
    "cyton": BoardIds.CYTON_BOARD.value if HAS_BRAINFLOW else 0,
    "synthetic": BoardIds.SYNTHETIC_BOARD.value if HAS_BRAINFLOW else -1,
}


def detect_serial_port():
    """Auto-detect OpenBCI serial port."""
    import glob
    patterns = [
        "/dev/tty.usbserial-*",    # macOS
        "/dev/ttyUSB*",             # Linux
        "COM*",                     # Windows
    ]
    for pattern in patterns:
        ports = glob.glob(pattern)
        if ports:
            return ports[0]
    return None


def check_connection(board_name="cyton_daisy", serial_port=None):
    """Step 1: Verify hardware connection."""
    print("\n═══ Step 1: Connection Check ═══")

    if not HAS_BRAINFLOW:
        print("  ❌ brainflow not installed: pip install brainflow")
        return None

    if board_name != "synthetic" and not serial_port:
        serial_port = detect_serial_port()
        if serial_port:
            print(f"  Auto-detected port: {serial_port}")
        else:
            print("  ⚠️  No serial port detected. Plug in OpenBCI dongle.")
            print("     Or use --board synthetic for testing.")
            return None

    params = BrainFlowInputParams()
    if serial_port:
        params.serial_port = serial_port

    board_id = BOARD_MAP.get(board_name)
    board = BoardShim(board_id, params)

    try:
        board.prepare_session()
        print(f"  ✅ Board connected: {board_name}")
        print(f"     Board ID: {board_id}")
        print(f"     Sample rate: {BoardShim.get_sampling_rate(board_id)} Hz")
        print(f"     EEG channels: {len(BoardShim.get_eeg_channels(board_id))}")
        return board
    except Exception as e:
        print(f"  ❌ Connection failed: {e}")
        return None


def check_signal_quality(board, duration=5.0):
    """Step 2: Check signal quality on all channels."""
    print(f"\n═══ Step 2: Signal Quality ({duration}s) ═══")

    board_id = board.get_board_id()
    eeg_channels = BoardShim.get_eeg_channels(board_id)
    sample_rate = BoardShim.get_sampling_rate(board_id)

    board.start_stream()
    time.sleep(duration)
    data = board.get_board_data()
    board.stop_stream()

    n_channels = min(len(eeg_channels), len(CHANNEL_NAMES))
    results = []

    print(f"\n  {'Ch':<5} {'Name':<5} {'Mean':>8} {'Std':>8} {'Range':>10} {'Quality'}")
    print(f"  {'─'*5} {'─'*5} {'─'*8} {'─'*8} {'─'*10} {'─'*10}")

    for i in range(n_channels):
        ch_data = data[eeg_channels[i]]
        mean = np.mean(ch_data)
        std = np.std(ch_data)
        rng = np.ptp(ch_data)

        # Quality heuristics
        if std < 1.0:
            quality = "❌ FLAT"
        elif std > 500:
            quality = "⚠️  NOISY"
        elif abs(mean) > 1000:
            quality = "⚠️  OFFSET"
        else:
            quality = "✅ OK"

        results.append({
            "channel": CHANNEL_NAMES[i],
            "mean": float(mean),
            "std": float(std),
            "range": float(rng),
            "quality": quality,
        })

        print(f"  {i+1:<5} {CHANNEL_NAMES[i]:<5} {mean:>8.1f} {std:>8.1f} {rng:>10.1f} {quality}")

    good = sum(1 for r in results if "OK" in r["quality"])
    print(f"\n  Summary: {good}/{n_channels} channels OK")

    return results


def check_noise_floor(board, duration=3.0):
    """Step 3: Measure 50/60Hz line noise."""
    print(f"\n═══ Step 3: Noise Floor ({duration}s) ═══")

    board_id = board.get_board_id()
    eeg_channels = BoardShim.get_eeg_channels(board_id)
    sample_rate = BoardShim.get_sampling_rate(board_id)

    board.start_stream()
    time.sleep(duration)
    data = board.get_board_data()
    board.stop_stream()

    ch_data = data[eeg_channels[0]]  # Use first channel
    n = len(ch_data)

    if n < sample_rate:
        print("  ⚠️  Not enough data for frequency analysis")
        return

    # FFT
    freqs = np.fft.rfftfreq(n, 1.0 / sample_rate)
    fft = np.abs(np.fft.rfft(ch_data))

    # Check 50Hz and 60Hz power
    for noise_freq in [50, 60]:
        idx = np.argmin(np.abs(freqs - noise_freq))
        nearby = fft[max(0, idx-2):idx+3]
        baseline = np.median(fft[10:idx-10])
        ratio = np.max(nearby) / (baseline + 1e-10)

        if ratio > 5:
            print(f"  ⚠️  {noise_freq}Hz noise detected (ratio: {ratio:.1f}x)")
            print(f"     → Use notch filter or check grounding")
        else:
            print(f"  ✅ {noise_freq}Hz clean (ratio: {ratio:.1f}x)")

    # Overall noise RMS
    rms = np.sqrt(np.mean(ch_data ** 2))
    print(f"  RMS noise (Ch1): {rms:.1f} µV")


def baseline_recording(board, duration=10.0, tag="eyes_closed"):
    """Step 4: Record baseline (eyes closed, relaxed)."""
    print(f"\n═══ Step 4: Baseline Recording ({duration}s, {tag}) ═══")
    print(f"  Please close your eyes and relax...")
    time.sleep(2)
    print(f"  Recording...")

    board_id = board.get_board_id()
    eeg_channels = BoardShim.get_eeg_channels(board_id)
    sample_rate = BoardShim.get_sampling_rate(board_id)

    board.start_stream()
    time.sleep(duration)
    data = board.get_board_data()
    board.stop_stream()

    # Save baseline
    out_dir = Path("anima-eeg/data")
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    fname = out_dir / f"baseline_{tag}_{ts}.npy"
    np.save(fname, data[eeg_channels])
    print(f"  ✅ Saved: {fname}")
    print(f"     Shape: {data[eeg_channels].shape} ({len(eeg_channels)} ch × {data.shape[1]} samples)")

    # Quick alpha check (eyes closed should show strong alpha)
    ch_data = data[eeg_channels[6]]  # O1 (occipital — best for alpha)
    n = len(ch_data)
    freqs = np.fft.rfftfreq(n, 1.0 / sample_rate)
    fft = np.abs(np.fft.rfft(ch_data))

    alpha_mask = (freqs >= 8) & (freqs <= 13)
    beta_mask = (freqs >= 13) & (freqs <= 30)
    alpha_power = np.mean(fft[alpha_mask])
    beta_power = np.mean(fft[beta_mask])
    ratio = alpha_power / (beta_power + 1e-10)

    if ratio > 1.5:
        print(f"  ✅ Alpha dominant (α/β = {ratio:.2f}) — expected for eyes closed")
    else:
        print(f"  ⚠️  Alpha weak (α/β = {ratio:.2f}) — check electrode placement at O1/O2")

    return fname


def run_calibration(board_name="cyton_daisy", serial_port=None, full=False):
    """Run full calibration sequence."""
    print("╔═══════════════════════════════════════╗")
    print("║   Anima EEG — Hardware Calibration    ║")
    print("╚═══════════════════════════════════════╝")

    board = check_connection(board_name, serial_port)
    if board is None:
        return

    try:
        quality = check_signal_quality(board)

        if full:
            check_noise_floor(board)
            baseline_recording(board, duration=10, tag="eyes_closed")
            print("\n  Now open your eyes...")
            time.sleep(2)
            baseline_recording(board, duration=10, tag="eyes_open")

        print("\n═══ Calibration Complete ═══")
        good = sum(1 for r in quality if "OK" in r["quality"])
        total = len(quality)
        if good == total:
            print(f"  ✅ All {total} channels OK — ready for experiments!")
        elif good >= total * 0.75:
            print(f"  ⚠️  {good}/{total} channels OK — usable, check bad channels")
        else:
            print(f"  ❌ {good}/{total} channels OK — re-seat electrodes")

    finally:
        board.release_session()


def calibrate_neural_mapper(board_name="synthetic", serial_port=None, duration=60):
    """EEG→Ψ 매핑 자동 캘리브레이션 (Ridge 회귀).

    EEG 밴드 파워와 의식 엔진 Psi 상태를 동시 수집하여
    NeuralCorrelateMapper를 Ridge 회귀로 학습합니다.

    Returns:
        dict: R2, RMSE, per-dimension accuracy, mapper path
    """
    import pickle
    print("\n═══ Neural Correlate Mapper Calibration ═══")
    print(f"  Board: {board_name}, Duration: {duration}s")

    # EEG 수집 준비
    try:
        from analyze import compute_band_power
    except ImportError:
        print("  ❌ analyze.py not found")
        return None

    # 의식 엔진 (시뮬레이션 가능)
    try:
        from consciousness_engine import ConsciousnessEngine
        engine = ConsciousnessEngine(cell_dim=64, hidden_dim=128, initial_cells=8, max_cells=32, n_factions=8)
        has_engine = True
    except ImportError:
        has_engine = False

    # NeuralCorrelateMapper
    try:
        from neural_correlate_mapper import NeuralCorrelateMapper
        mapper = NeuralCorrelateMapper()
        has_mapper = True
    except ImportError:
        has_mapper = False
        print("  ⚠️ NeuralCorrelateMapper not available, collecting data only")

    # EEG 보드 연결
    board = check_connection(board_name, serial_port)
    if board is None:
        return None

    try:
        sample_rate = BoardShim.get_sampling_rate(board.board_id) if HAS_BRAINFLOW else 250
        eeg_channels = BoardShim.get_eeg_channels(board.board_id) if HAS_BRAINFLOW else list(range(8))

        eeg_samples = []
        psi_samples = []

        print(f"  Recording {duration}s of paired EEG + Ψ data...")
        start = time.time()
        step = 0
        while time.time() - start < duration:
            time.sleep(1.0)
            step += 1

            # EEG 밴드 파워
            data = board.get_current_board_data(sample_rate)
            if data.shape[1] < sample_rate // 2:
                continue
            ch_data = data[eeg_channels[0]] if len(eeg_channels) > 0 else np.random.randn(sample_rate)
            bp = compute_band_power(ch_data, sample_rate)
            eeg_vec = [bp.delta, bp.theta, bp.alpha, bp.beta, bp.gamma]
            eeg_samples.append(eeg_vec)

            # Ψ 상태
            if has_engine:
                result = engine.step(None)
                psi_vec = [
                    getattr(result, 'phi_iit', 0.5),
                    getattr(result, 'phi_proxy', 0.5),
                    0.5,  # tension proxy
                    0.5,  # entropy proxy
                    0.5,  # creativity proxy
                ]
            else:
                psi_vec = [np.random.random() for _ in range(5)]
            psi_samples.append(psi_vec)

            if step % 10 == 0:
                elapsed = time.time() - start
                print(f"    [{step}s / {duration}s] {elapsed/duration*100:.0f}%")

        print(f"  Collected {len(eeg_samples)} paired samples")

        if len(eeg_samples) < 10:
            print("  ❌ Too few samples")
            return None

        X = np.array(eeg_samples)
        Y = np.array(psi_samples)

        # Ridge 회귀 피팅
        if has_mapper:
            mapper.fit(X, Y)

            # 평가
            Y_pred = mapper.predict(X)
            ss_res = np.sum((Y - Y_pred) ** 2, axis=0)
            ss_tot = np.sum((Y - Y.mean(axis=0)) ** 2, axis=0) + 1e-8
            r2_per_dim = 1 - ss_res / ss_tot
            r2_mean = float(np.mean(r2_per_dim))
            rmse = float(np.sqrt(np.mean((Y - Y_pred) ** 2)))

            # 저장
            out_path = Path("anima-eeg/config/neural_mapper.pkl")
            out_path.parent.mkdir(parents=True, exist_ok=True)
            with open(out_path, 'wb') as f:
                pickle.dump(mapper, f)

            dim_names = ['Φ(IIT)', 'Φ(proxy)', 'tension', 'entropy', 'creativity']
            print(f"\n  ═══ Calibration Results ═══")
            print(f"  R²(mean): {r2_mean:.3f}  RMSE: {rmse:.4f}")
            for i, name in enumerate(dim_names):
                bar = '█' * int(r2_per_dim[i] * 20)
                print(f"    {name:12s} R²={r2_per_dim[i]:.3f} {bar}")
            print(f"\n  Saved: {out_path}")

            return {'R2': r2_mean, 'RMSE': rmse, 'per_dim_R2': r2_per_dim.tolist(), 'path': str(out_path)}
        else:
            # 데이터만 저장
            out_path = Path("anima-eeg/config/calibration_data.npz")
            out_path.parent.mkdir(parents=True, exist_ok=True)
            np.savez(out_path, eeg=X, psi=Y)
            print(f"  Saved raw data: {out_path}")
            return {'samples': len(eeg_samples), 'path': str(out_path)}
    finally:
        board.release_session()


def main():
    parser = argparse.ArgumentParser(description="EEG Hardware Calibration")
    parser.add_argument("--board", default="cyton_daisy", choices=list(BOARD_MAP.keys()))
    parser.add_argument("--port", default=None, help="Serial port (auto-detect if omitted)")
    parser.add_argument("--full", action="store_true", help="Full calibration with baseline recording")
    parser.add_argument("--calibrate-mapper", action="store_true", help="Calibrate EEG→Ψ neural mapper")
    parser.add_argument("--duration", type=int, default=60, help="Mapper calibration duration (seconds)")
    args = parser.parse_args()

    if args.calibrate_mapper:
        calibrate_neural_mapper(args.board, args.port, args.duration)
    else:
        run_calibration(args.board, args.port, args.full)


if __name__ == "__main__":
    main()
