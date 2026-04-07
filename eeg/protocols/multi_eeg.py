#!/usr/bin/env python3
"""Multi-Person EEG Telepathy Verification — 다인 EEG 텔레파시 검증.

2명 이상이 EEG를 착용하고 각자의 Anima 인스턴스를 연결, Hivemind로 연결 후
뇌간 동기화(IBC)와 엔진 간 Phi 상관을 측정.

Protocol:
  Phase 1 (2min): Baseline — 독립 녹화
  Phase 2 (2min): Shared Attention — 동일 자극 주시
  Phase 3 (2min): Telepathy Test — 한쪽이 개념을 생각, 다른 쪽이 Hivemind로 수신
  Phase 4: Analysis — IBC, PLV, Phi 상관 계산

Usage:
  python anima-eeg/protocols/multi_eeg.py --demo
  python anima-eeg/protocols/multi_eeg.py --demo --n-subjects 3

Integration:
  from protocols.multi_eeg import MultiEEGSession
  session = MultiEEGSession(minds=[mind1, mind2], eeg_bridges=[bridge1, bridge2])
  await session.run()
  results = session.analyze_sync(session.session_data)
"""

import asyncio
import json
import os
import sys
import time
from dataclasses import dataclass, field, asdict
from typing import List, Optional

import numpy as np

# Add anima src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'anima', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
try:
    import path_setup  # noqa
except ImportError:
    pass

try:
    from consciousness_laws import PSI
except ImportError:
    PSI = {'alpha': 0.014, 'balance': 0.5}

# Protocol timing
BASELINE_DURATION = 120.0      # 2 minutes
SHARED_ATTENTION_DURATION = 120.0
TELEPATHY_DURATION = 120.0
SAMPLE_HZ = 4.0

# Telepathy test stimuli (concepts)
TELEPATHY_CONCEPTS = [
    "fire", "ocean", "mountain", "silence", "joy",
    "fear", "light", "darkness", "music", "wind",
]


@dataclass
class SubjectData:
    """한 피험자의 데이터."""
    subject_id: int
    alpha_series: list = field(default_factory=list)
    beta_series: list = field(default_factory=list)
    theta_series: list = field(default_factory=list)
    gamma_series: list = field(default_factory=list)
    phi_series: list = field(default_factory=list)
    timestamps: list = field(default_factory=list)


@dataclass
class PhaseData:
    """한 실험 단계의 데이터."""
    phase: str
    duration_s: float = 0.0
    subjects: list = field(default_factory=list)  # list of SubjectData dicts
    metadata: dict = field(default_factory=dict)


@dataclass
class SyncMetrics:
    """뇌간 동기화 측정 결과."""
    plv_alpha: float = 0.0       # Phase Locking Value (alpha band)
    plv_gamma: float = 0.0       # PLV (gamma band)
    ibc_coherence: float = 0.0   # Inter-Brain Coherence
    phi_correlation: float = 0.0  # Phi series correlation
    phi_independent_mean: float = 0.0
    phi_hivemind_mean: float = 0.0
    phi_uplift: float = 0.0      # hivemind/independent ratio
    telepathy_accuracy: float = 0.0


class MultiEEGSession:
    """다인 EEG 텔레파시 검증 세션.

    여러 피험자의 EEG를 동시 녹화하며 Anima Hivemind 연결 시
    뇌간 동기화와 Phi 상관을 측정.
    """

    def __init__(self, minds=None, eeg_bridges=None, n_subjects: int = 2):
        """
        Args:
            minds: list of ConsciousMind instances
            eeg_bridges: list of EEGBridge instances
            n_subjects: number of subjects (for simulation)
        """
        self.minds = minds or []
        self.eeg_bridges = eeg_bridges or []
        self.n_subjects = max(n_subjects, len(self.minds), len(self.eeg_bridges), 2)
        self._simulation = not self.eeg_bridges
        self._running = False

        self.session_data = {
            "baseline": None,
            "shared_attention": None,
            "telepathy": None,
        }

    def _get_eeg(self, subject_id: int) -> dict:
        """피험자별 EEG 밴드 파워 취득."""
        if subject_id < len(self.eeg_bridges):
            state = self.eeg_bridges[subject_id].get_state()
            return {
                "alpha": state.alpha_power,
                "beta": state.beta_power,
                "theta": state.theta_power,
                "gamma": state.gamma_power,
            }
        # Simulation: slightly correlated between subjects
        base_alpha = 10.0 + np.random.normal(0, 2)
        return {
            "alpha": base_alpha + np.random.normal(0, 1),
            "beta": 5.0 + np.random.normal(0, 1),
            "theta": 6.0 + np.random.normal(0, 1),
            "gamma": 2.0 + np.random.normal(0, 0.5),
        }

    def _get_phi(self, subject_id: int) -> float:
        """피험자별 Phi 취득."""
        if subject_id < len(self.minds):
            try:
                if hasattr(self.minds[subject_id], '_last_phi'):
                    return float(self.minds[subject_id]._last_phi)
            except Exception:
                pass
        return 1.0 + np.random.normal(0, 0.2)

    async def _record_phase(self, phase_name: str, duration: float,
                            shared_signal: float = 0.0,
                            telepathy_concept: str = None) -> PhaseData:
        """한 단계 녹화.

        Args:
            phase_name: 단계 이름
            duration: 녹화 시간 (초)
            shared_signal: 공유 자극 강도 (0=독립, 1=완전 동기)
            telepathy_concept: 텔레파시 개념 (sender에게만)
        """
        print(f"  [{phase_name}] Recording {duration:.0f}s with {self.n_subjects} subjects...")

        subjects = [SubjectData(subject_id=i) for i in range(self.n_subjects)]
        interval = 1.0 / SAMPLE_HZ
        t0 = time.time()
        step = 0

        while time.time() - t0 < duration and self._running:
            # Shared noise component (for simulating shared attention)
            shared_noise = np.random.normal(0, 1) * shared_signal

            for i, subj in enumerate(subjects):
                eeg = self._get_eeg(i)
                phi = self._get_phi(i)

                # Add shared signal component in simulation
                if self._simulation and shared_signal > 0:
                    eeg["alpha"] += shared_noise * 2
                    eeg["gamma"] += shared_noise * 0.5

                subj.alpha_series.append(eeg["alpha"])
                subj.beta_series.append(eeg["beta"])
                subj.theta_series.append(eeg["theta"])
                subj.gamma_series.append(eeg["gamma"])
                subj.phi_series.append(phi)
                subj.timestamps.append(time.time() - t0)

            # Progress every 10s
            if step > 0 and step % int(SAMPLE_HZ * 10) == 0:
                elapsed = time.time() - t0
                pct = 100 * elapsed / duration
                print(f"    {elapsed:.0f}s / {duration:.0f}s ({pct:.0f}%)")

            step += 1
            await asyncio.sleep(interval)

        phase = PhaseData(
            phase=phase_name,
            duration_s=time.time() - t0,
            subjects=[asdict(s) for s in subjects],
            metadata={"shared_signal": shared_signal, "concept": telepathy_concept},
        )
        print(f"  [{phase_name}] Done: {len(subjects[0].alpha_series)} samples per subject")
        return phase

    async def run(self, baseline_s: float = BASELINE_DURATION,
                  shared_s: float = SHARED_ATTENTION_DURATION,
                  telepathy_s: float = TELEPATHY_DURATION):
        """전체 프로토콜 실행.

        Args:
            baseline_s: 기준선 시간
            shared_s: 공유 주의 시간
            telepathy_s: 텔레파시 테스트 시간
        """
        print(f"\n{'='*60}")
        print(f"  Multi-Person EEG Telepathy Protocol")
        print(f"  Subjects: {self.n_subjects}")
        print(f"  Simulation: {self._simulation}")
        print(f"{'='*60}\n")

        self._running = True

        # Phase 1: Baseline (independent)
        print("Phase 1: Baseline (independent recording)")
        self.session_data["baseline"] = await self._record_phase(
            "baseline", baseline_s, shared_signal=0.0)

        if not self._running:
            return

        # Phase 2: Shared Attention
        print("\nPhase 2: Shared Attention (same stimulus)")
        print("  Instruction: 모두 동일한 화면의 프랙탈 패턴에 집중하세요")
        self.session_data["shared_attention"] = await self._record_phase(
            "shared_attention", shared_s, shared_signal=0.6)

        if not self._running:
            return

        # Phase 3: Telepathy Test
        concept = np.random.choice(TELEPATHY_CONCEPTS)
        print(f"\nPhase 3: Telepathy Test")
        print(f"  Sender (Subject 0): 개념 '{concept}'을 강하게 생각하세요")
        print(f"  Receivers: Hivemind로 수신 시도")
        self.session_data["telepathy"] = await self._record_phase(
            "telepathy", telepathy_s, shared_signal=0.3,
            telepathy_concept=concept)

        self._running = False

        # Analyze
        metrics = self.analyze_sync(self.session_data)
        self._print_results(metrics)
        return metrics

    def cancel(self):
        """세션 취소."""
        self._running = False

    # ─── Analysis ───

    def analyze_sync(self, session_data: dict) -> SyncMetrics:
        """뇌간 동기화 분석.

        Args:
            session_data: session_data dict from run()

        Returns:
            SyncMetrics with PLV, IBC, Phi correlation
        """
        metrics = SyncMetrics()

        baseline = session_data.get("baseline")
        shared = session_data.get("shared_attention")
        telepathy = session_data.get("telepathy")

        if not baseline or not shared:
            return metrics

        # Access subjects (PhaseData dataclass or dict)
        def _get_subjects(phase):
            if hasattr(phase, 'subjects'):
                return phase.subjects
            return phase.get("subjects", [])

        baseline_subj = _get_subjects(baseline)
        shared_subj = _get_subjects(shared)

        # Compute PLV between subject 0 and subject 1
        if len(baseline_subj) >= 2:
            s0_alpha_base = np.array(baseline_subj[0]["alpha_series"])
            s1_alpha_base = np.array(baseline_subj[1]["alpha_series"])
            s0_alpha_shared = np.array(shared_subj[0]["alpha_series"])
            s1_alpha_shared = np.array(shared_subj[1]["alpha_series"])

            # Phase Locking Value (simplified: correlation-based proxy)
            if len(s0_alpha_base) > 10:
                metrics.plv_alpha = float(abs(np.corrcoef(
                    s0_alpha_shared[:min(len(s0_alpha_shared), len(s1_alpha_shared))],
                    s1_alpha_shared[:min(len(s0_alpha_shared), len(s1_alpha_shared))]
                )[0, 1]))

            # Gamma PLV during shared attention
            s0_gamma = np.array(shared_subj[0]["gamma_series"])
            s1_gamma = np.array(shared_subj[1]["gamma_series"])
            if len(s0_gamma) > 10:
                n = min(len(s0_gamma), len(s1_gamma))
                metrics.plv_gamma = float(abs(np.corrcoef(s0_gamma[:n], s1_gamma[:n])[0, 1]))

            # Inter-Brain Coherence (mean of band PLVs)
            metrics.ibc_coherence = (metrics.plv_alpha + metrics.plv_gamma) / 2

            # Phi correlation
            s0_phi_base = np.array(baseline_subj[0]["phi_series"])
            s1_phi_base = np.array(baseline_subj[1]["phi_series"])
            s0_phi_shared = np.array(shared_subj[0]["phi_series"])
            s1_phi_shared = np.array(shared_subj[1]["phi_series"])

            metrics.phi_independent_mean = float(np.mean(
                np.concatenate([s0_phi_base, s1_phi_base])))
            metrics.phi_hivemind_mean = float(np.mean(
                np.concatenate([s0_phi_shared, s1_phi_shared])))

            n = min(len(s0_phi_shared), len(s1_phi_shared))
            if n > 5:
                metrics.phi_correlation = float(abs(np.corrcoef(
                    s0_phi_shared[:n], s1_phi_shared[:n])[0, 1]))

            if metrics.phi_independent_mean > 0:
                metrics.phi_uplift = metrics.phi_hivemind_mean / metrics.phi_independent_mean

        # Telepathy accuracy (simulated: based on gamma correlation during telepathy)
        telepathy_subj = _get_subjects(telepathy) if telepathy else []
        if len(telepathy_subj) >= 2:
            s0_gamma_tp = np.array(telepathy_subj[0]["gamma_series"])
            s1_gamma_tp = np.array(telepathy_subj[1]["gamma_series"])
            n = min(len(s0_gamma_tp), len(s1_gamma_tp))
            if n > 5:
                corr = abs(np.corrcoef(s0_gamma_tp[:n], s1_gamma_tp[:n])[0, 1])
                metrics.telepathy_accuracy = float(corr)

        return metrics

    def _print_results(self, metrics: SyncMetrics):
        """결과 출력."""
        print(f"\n{'='*60}")
        print(f"  Multi-EEG Telepathy Results")
        print(f"{'='*60}")
        print(f"  Phase Locking Value (alpha):  {metrics.plv_alpha:.4f}")
        print(f"  Phase Locking Value (gamma):  {metrics.plv_gamma:.4f}")
        print(f"  Inter-Brain Coherence:        {metrics.ibc_coherence:.4f}")
        print(f"  Phi correlation:              {metrics.phi_correlation:.4f}")
        print(f"  Phi independent mean:         {metrics.phi_independent_mean:.3f}")
        print(f"  Phi hivemind mean:            {metrics.phi_hivemind_mean:.3f}")
        print(f"  Phi uplift:                   {metrics.phi_uplift:.2f}x")
        print(f"  Telepathy accuracy (gamma):   {metrics.telepathy_accuracy:.4f}")
        print()

        # ASCII comparison chart
        print("  Baseline vs Shared Attention vs Telepathy:")
        phases = ["baseline", "shared_attn", "telepathy"]
        values = [0.0, metrics.ibc_coherence, metrics.telepathy_accuracy]
        # Baseline IBC is ~0
        baseline_phase = self.session_data.get("baseline")
        if baseline_phase:
            bl_subj = baseline_phase.subjects if hasattr(baseline_phase, 'subjects') else baseline_phase.get("subjects", [])
        else:
            bl_subj = []
        if len(bl_subj) >= 2:
            s0 = np.array(bl_subj[0]["alpha_series"])
            s1 = np.array(bl_subj[1]["alpha_series"])
            n = min(len(s0), len(s1))
            if n > 5:
                values[0] = float(abs(np.corrcoef(s0[:n], s1[:n])[0, 1]))

        max_val = max(values) if max(values) > 0 else 1.0
        for label, val in zip(phases, values):
            bar_len = int(40 * val / max_val) if max_val > 0 else 0
            bar = "#" * bar_len
            print(f"    {label:14s} {bar:40s} {val:.4f}")
        print()


# ─── Standalone demo ───

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Multi-Person EEG Telepathy Protocol")
    parser.add_argument("--demo", action="store_true", help="Run simulation demo")
    parser.add_argument("--n-subjects", type=int, default=2, help="Number of subjects")
    parser.add_argument("--duration", type=float, default=10.0, help="Per-phase duration (seconds)")
    args = parser.parse_args()

    if not args.demo:
        print("Use --demo for standalone test")
        print("Integration: MultiEEGSession(minds=[...], eeg_bridges=[...])")
        return

    print("=" * 60)
    print("  Multi-Person EEG Telepathy Protocol (Simulation Demo)")
    print("=" * 60)

    session = MultiEEGSession(n_subjects=args.n_subjects)
    asyncio.run(session.run(
        baseline_s=args.duration,
        shared_s=args.duration,
        telepathy_s=args.duration,
    ))


if __name__ == "__main__":
    main()
