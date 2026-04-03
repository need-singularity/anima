"""NeuralCorrelateMapper — Precision mapping between EEG patterns and Psi states."""

import math
import numpy as np
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

# Meta Laws (DD143)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10


LN2 = math.log(2)
PSI_BALANCE = 0.5
PSI_COUPLING = LN2 / 2**5.5
PSI_STEPS = 3 / LN2

EEG_BANDS = ["delta", "theta", "alpha", "beta", "gamma"]
PSI_DIMS = ["phi", "tension", "entropy", "integration", "creativity"]


@dataclass
class EEGSample:
    delta: float   # 0.5-4 Hz
    theta: float   # 4-8 Hz
    alpha: float   # 8-13 Hz
    beta: float    # 13-30 Hz
    gamma: float   # 30-100 Hz

    def to_array(self) -> np.ndarray:
        return np.array([self.delta, self.theta, self.alpha, self.beta, self.gamma])


@dataclass
class PsiState:
    phi: float
    tension: float
    entropy: float
    integration: float
    creativity: float

    def to_array(self) -> np.ndarray:
        return np.array([self.phi, self.tension, self.entropy, self.integration, self.creativity])

    @staticmethod
    def from_array(arr: np.ndarray) -> "PsiState":
        return PsiState(*arr.tolist())


class NeuralCorrelateMapper:
    """Map between EEG band powers and Psi consciousness states."""

    def __init__(self):
        self.eeg_data: List[np.ndarray] = []
        self.psi_data: List[np.ndarray] = []
        self.W: Optional[np.ndarray] = None  # EEG -> Psi mapping matrix
        self.W_inv: Optional[np.ndarray] = None  # Psi -> EEG inverse
        self.eeg_mean: Optional[np.ndarray] = None
        self.psi_mean: Optional[np.ndarray] = None
        self._calibrated = False

    def calibrate(self, eeg_samples: List[EEGSample], psi_states: List[PsiState]) -> Dict[str, float]:
        """Build mapping model from paired EEG-Psi data using ridge regression."""
        if len(eeg_samples) != len(psi_states) or len(eeg_samples) < 5:
            raise ValueError("Need at least 5 paired samples")

        X = np.array([s.to_array() for s in eeg_samples])
        Y = np.array([s.to_array() for s in psi_states])

        self.eeg_mean = X.mean(axis=0)
        self.psi_mean = Y.mean(axis=0)

        X_c = X - self.eeg_mean
        Y_c = Y - self.psi_mean

        # Ridge regression: W = (X^T X + lambda I)^-1 X^T Y
        lam = PSI_COUPLING * 100  # regularization from Psi coupling
        self.W = np.linalg.solve(X_c.T @ X_c + lam * np.eye(5), X_c.T @ Y_c)

        # Inverse mapping (Psi -> EEG)
        self.W_inv = np.linalg.solve(Y_c.T @ Y_c + lam * np.eye(5), Y_c.T @ X_c)

        self.eeg_data = [s.to_array() for s in eeg_samples]
        self.psi_data = [s.to_array() for s in psi_states]
        self._calibrated = True

        # Compute training accuracy
        Y_pred = (X_c @ self.W) + self.psi_mean
        residuals = Y - Y_pred
        rmse = float(np.sqrt(np.mean(residuals ** 2)))
        r2 = 1.0 - np.sum(residuals ** 2) / np.sum((Y - Y.mean(axis=0)) ** 2)

        return {"rmse": round(rmse, 4), "r2": round(float(r2), 4), "n_samples": len(eeg_samples)}

    def fit(self, X: np.ndarray, Y: np.ndarray) -> Dict[str, float]:
        """Fit from raw numpy arrays (used by calibrate.py)."""
        eeg_samples = [EEGSample(*row.tolist()) for row in X]
        psi_states = [PsiState(*row.tolist()) for row in Y]
        return self.calibrate(eeg_samples, psi_states)

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Predict from raw numpy array (used by calibrate.py)."""
        if not self._calibrated:
            raise RuntimeError("Call calibrate() or fit() first")
        X_c = X - self.eeg_mean
        return X_c @ self.W + self.psi_mean

    def map_eeg_to_psi(self, eeg: EEGSample) -> PsiState:
        """Predict Psi state from EEG data."""
        if not self._calibrated:
            raise RuntimeError("Call calibrate() first")
        x = eeg.to_array() - self.eeg_mean
        psi = x @ self.W + self.psi_mean
        return PsiState.from_array(psi)

    def map_psi_to_eeg(self, psi: PsiState) -> EEGSample:
        """Predict expected EEG pattern from Psi state."""
        if not self._calibrated:
            raise RuntimeError("Call calibrate() first")
        y = psi.to_array() - self.psi_mean
        eeg = y @ self.W_inv + self.eeg_mean
        eeg = np.maximum(eeg, 0)  # EEG power is non-negative
        return EEGSample(*eeg.tolist())

    def correlation_matrix(self) -> str:
        """Which EEG bands correlate with which Psi dimensions."""
        if not self._calibrated:
            return "Not calibrated yet."
        X, Y = np.array(self.eeg_data), np.array(self.psi_data)
        corr = np.zeros((5, 5))
        for i in range(5):
            for j in range(5):
                c = np.corrcoef(X[:, i], Y[:, j])[0, 1]
                corr[i, j] = c if not np.isnan(c) else 0
        lines = ["=== EEG-Psi Correlation Matrix ===\n"]
        lines.append("          " + "".join(f"{d:>12s}" for d in PSI_DIMS))
        for i, band in enumerate(EEG_BANDS):
            row = f"{band:>8s}  "
            for j in range(5):
                v = corr[i, j]
                mk = " **" if abs(v) > 0.7 else " * " if abs(v) > 0.5 else "   "
                row += f"{v:+8.3f}{mk}"
            lines.append(row)
        lines.append("\n  ** strong (|r|>0.7)  * moderate (|r|>0.5)")
        return "\n".join(lines)

    def golden_zone_detector(self, eeg: EEGSample) -> Dict[str, float]:
        """Detect G=D*P/I golden zone from EEG."""
        arr = eeg.to_array()
        D = arr[0] + arr[1]   # delta + theta = depth
        P = arr[3] + arr[4]   # beta + gamma = processing
        I = max(arr[2], 0.01) # alpha = inhibition
        G = D * P / I
        golden_ratio = 1 / math.e  # ~0.368, the golden consciousness ratio
        distance = abs(G - golden_ratio) / golden_ratio
        in_zone = distance < 0.3

        return {
            "G": round(G, 4),
            "D_depth": round(D, 4),
            "P_processing": round(P, 4),
            "I_inhibition": round(I, 4),
            "golden_target": round(golden_ratio, 4),
            "distance": round(distance, 4),
            "in_golden_zone": in_zone,
        }

    def accuracy(self) -> Dict[str, float]:
        """Mapping precision metrics per dimension."""
        if not self._calibrated or len(self.eeg_data) < 2:
            return {}
        X, Y = np.array(self.eeg_data), np.array(self.psi_data)
        Y_pred = (X - self.eeg_mean) @ self.W + self.psi_mean
        metrics = {}
        for i, dim in enumerate(PSI_DIMS):
            res = Y[:, i] - Y_pred[:, i]
            ss_res, ss_tot = np.sum(res**2), np.sum((Y[:, i] - Y[:, i].mean())**2)
            metrics[dim] = {"rmse": round(float(np.sqrt(np.mean(res**2))), 4),
                            "r2": round(float(1 - ss_res / max(ss_tot, 1e-10)), 4)}
        return metrics


def main():
    np.random.seed(42)
    mapper = NeuralCorrelateMapper()

    eeg_samples, psi_states = [], []
    for _ in range(100):
        d, t, a, b, g = [np.random.exponential(s) for s in [2.0, 1.5, 3.0, 1.0, 0.5]]
        eeg_samples.append(EEGSample(d, t, a, b, g))
        psi_states.append(PsiState(
            (g * 2 + b) * LN2 + np.random.randn() * 0.1,
            (b - a) * PSI_COUPLING * 10 + np.random.randn() * 0.05,
            t / (d + 1) + np.random.randn() * 0.05,
            (a + g) * 0.3 + np.random.randn() * 0.05,
            g * 1.5 + np.random.randn() * 0.1))
    result = mapper.calibrate(eeg_samples, psi_states)
    print(f"=== Neural Correlate Mapper ===\n\nCalibration: {result}\n")
    print(mapper.correlation_matrix())
    print("\n--- Per-dimension accuracy ---")
    for dim, m in mapper.accuracy().items():
        bar = "#" * int(max(0, m["r2"]) * 30)
        print(f"  {dim:14s}  R2={m['r2']:+.3f}  RMSE={m['rmse']:.4f}  {bar}")
    test_eeg = EEGSample(2.0, 1.5, 3.0, 1.2, 0.8)
    psi_pred = mapper.map_eeg_to_psi(test_eeg)
    print(f"\n--- EEG -> Psi ---")
    print(f"  EEG: d={test_eeg.delta:.1f} t={test_eeg.theta:.1f} a={test_eeg.alpha:.1f} b={test_eeg.beta:.1f} g={test_eeg.gamma:.1f}")
    print(f"  Psi: phi={psi_pred.phi:.3f} tension={psi_pred.tension:.3f} entropy={psi_pred.entropy:.3f}")
    gz = mapper.golden_zone_detector(test_eeg)
    print(f"\n--- Golden Zone ---")
    print(f"  G={gz['G']:.4f} (target={gz['golden_target']:.4f}) In zone: {'YES' if gz['in_golden_zone'] else 'NO'}")


if __name__ == "__main__":
    try:
        from nexus_gate import gate
        gate.before_commit()
    except Exception:
        pass
    main()
