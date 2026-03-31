#!/usr/bin/env python3
"""Motor Replay Engine — 수면 중 운동 기억 재생 및 강화.

Record motor sequences during waking, replay during sleep phases.
Integrates with sleep_protocol.py for phase-aware replay.
Uses Hebbian consolidation to strengthen successful motor patterns.
Dream motor sequences: novel combinations of learned primitives.

Replay modes:
  exact:      faithful replay of recorded trajectory
  compressed: accelerated replay (time-compressed, REM-like)
  remix:      creative recombination of learned primitives (dream)

Consciousness integration:
  - Phi measurement during replay vs waking
  - EmergentM (Hexad M module) for long-term memory storage
  - Hedonic feedback from pain_reward.py weights consolidation

Usage:
  python anima-body/src/motor_replay.py           # demo
  python anima-body/src/motor_replay.py --steps 200

Integration:
  from motor_replay import MotorReplayEngine
  engine = MotorReplayEngine()
  engine.record(trajectory)            # during waking
  replayed = engine.replay("N3")       # during sleep N3
  replayed = engine.replay("REM")      # creative remix in REM

Requires: numpy
"""

import math
import os
import sys
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

import numpy as np

# ── Project path setup ──
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(_REPO_ROOT, "anima", "src"))
sys.path.insert(0, os.path.join(_REPO_ROOT, "anima"))
sys.path.insert(0, os.path.join(_REPO_ROOT, "anima-eeg", "protocols"))
sys.path.insert(0, os.path.join(_REPO_ROOT, "anima-eeg"))

try:
    import path_setup  # noqa
except ImportError:
    pass

# Psi constants (lazy import)
try:
    from consciousness_laws import PSI_BALANCE, PSI_ALPHA as PSI_COUPLING, PSI_F_CRITICAL
except ImportError:
    PSI_BALANCE = 0.5
    PSI_COUPLING = 0.014
    PSI_F_CRITICAL = 0.10

LN2 = math.log(2)
PSI_STEPS = 3.0 / LN2  # 4.328 — optimal evolution steps


# ═══════════════════════════════════════════════════════════
# Data structures
# ═══════════════════════════════════════════════════════════

class ReplayMode(Enum):
    EXACT = "exact"
    COMPRESSED = "compressed"
    REMIX = "remix"


@dataclass
class MotorFrame:
    """Single frame of a motor trajectory."""
    joint_angles: List[float]
    joint_velocities: List[float]
    timestamp: float = 0.0
    reward: float = 0.0         # associated reward (from pain_reward)
    phi: float = 0.0            # Phi at this frame


@dataclass
class MotorSequence:
    """Complete motor trajectory with metadata."""
    frames: List[MotorFrame] = field(default_factory=list)
    success_score: float = 0.0   # 0-1 (from reward accumulation)
    total_reward: float = 0.0
    total_pain: float = 0.0
    mean_phi: float = 0.0
    label: str = ""              # e.g. "reach_target_1"
    timestamp: float = 0.0       # recording time
    replay_count: int = 0        # times replayed
    hebbian_strength: float = 1.0  # Hebbian weight (strengthened by replay)


@dataclass
class ReplayResult:
    """Result of a motor replay session."""
    mode: str
    sequences_replayed: int = 0
    mean_phi_replay: float = 0.0
    mean_phi_waking: float = 0.0
    phi_ratio: float = 0.0       # replay_phi / waking_phi
    consolidation_delta: float = 0.0  # Hebbian strength change
    novel_sequences: int = 0     # creative remixes generated
    sleep_stage: str = ""


# ═══════════════════════════════════════════════════════════
# Hebbian motor consolidation
# ═══════════════════════════════════════════════════════════

class HebbianMotorConsolidator:
    """Strengthen/weaken motor patterns via Hebbian LTP/LTD.

    Success → LTP (strengthen pattern, lower replay threshold)
    Failure → LTD (weaken pattern, may be pruned)
    """

    def __init__(
        self,
        ltp_rate: float = 0.05,
        ltd_rate: float = 0.02,
        pruning_threshold: float = 0.1,
    ):
        self.ltp_rate = ltp_rate
        self.ltd_rate = ltd_rate
        self.pruning_threshold = pruning_threshold

    def consolidate(self, sequence: MotorSequence) -> float:
        """Apply Hebbian consolidation to a motor sequence.

        Returns:
            delta: change in hebbian_strength
        """
        if sequence.success_score > 0.5:
            # LTP: successful pattern strengthened
            delta = self.ltp_rate * sequence.success_score
            sequence.hebbian_strength = min(5.0, sequence.hebbian_strength + delta)
        else:
            # LTD: unsuccessful pattern weakened
            delta = -self.ltd_rate * (1.0 - sequence.success_score)
            sequence.hebbian_strength = max(0.0, sequence.hebbian_strength + delta)

        sequence.replay_count += 1
        return delta

    def should_prune(self, sequence: MotorSequence) -> bool:
        """Check if a sequence should be pruned (forgotten)."""
        return sequence.hebbian_strength < self.pruning_threshold


# ═══════════════════════════════════════════════════════════
# Motor Replay Engine
# ═══════════════════════════════════════════════════════════

class MotorReplayEngine:
    """Records motor sequences during waking, replays during sleep.

    Sleep phase integration:
      Wake: record trajectories
      N1:   no replay (transition)
      N2:   exact replay (memory consolidation)
      N3:   compressed replay (deep consolidation, Hebbian LTP)
      REM:  creative remix (novel motor dreams)
    """

    def __init__(
        self,
        max_sequences: int = 100,
        max_frames_per_seq: int = 500,
        compressed_speed: float = 3.0,
        remix_noise: float = 0.15,
        n_joints: int = 2,
    ):
        """
        Args:
            max_sequences: max stored sequences
            max_frames_per_seq: max frames per sequence
            compressed_speed: speedup factor for compressed replay
            remix_noise: noise added during creative remix
            n_joints: number of joints
        """
        self.max_sequences = max_sequences
        self.max_frames_per_seq = max_frames_per_seq
        self.compressed_speed = compressed_speed
        self.remix_noise = remix_noise
        self.n_joints = n_joints

        # Storage
        self._sequences: List[MotorSequence] = []
        self._current_recording: Optional[MotorSequence] = None

        # Hebbian consolidator
        self._consolidator = HebbianMotorConsolidator()

        # Phi tracking
        self._waking_phis: deque = deque(maxlen=500)
        self._replay_phis: deque = deque(maxlen=500)

        # Sleep protocol (lazy)
        self._sleep_protocol = None

        # EmergentM (lazy)
        self._emergent_m = None

        # Statistics
        self._total_replays = 0
        self._total_remixes = 0
        self._step = 0

    # ─── Recording (waking) ───

    def start_recording(self, label: str = ""):
        """Begin recording a motor sequence."""
        self._current_recording = MotorSequence(
            label=label,
            timestamp=time.time(),
        )

    def record_frame(
        self,
        joint_angles: List[float],
        joint_velocities: Optional[List[float]] = None,
        reward: float = 0.0,
        phi: float = 0.0,
    ):
        """Record a single motor frame.

        Args:
            joint_angles: current joint angles
            joint_velocities: current joint velocities (optional)
            reward: reward signal at this frame
            phi: Phi at this frame
        """
        if self._current_recording is None:
            self.start_recording()

        if len(self._current_recording.frames) >= self.max_frames_per_seq:
            return  # buffer full

        frame = MotorFrame(
            joint_angles=list(joint_angles),
            joint_velocities=list(joint_velocities) if joint_velocities else [0.0] * len(joint_angles),
            timestamp=time.time(),
            reward=reward,
            phi=phi,
        )
        self._current_recording.frames.append(frame)
        self._waking_phis.append(phi)

    def stop_recording(self) -> Optional[MotorSequence]:
        """Stop recording and store the sequence.

        Returns:
            The completed MotorSequence or None
        """
        if self._current_recording is None or not self._current_recording.frames:
            self._current_recording = None
            return None

        seq = self._current_recording
        self._current_recording = None

        # Compute metadata
        rewards = [f.reward for f in seq.frames]
        phis = [f.phi for f in seq.frames]
        seq.total_reward = sum(rewards)
        seq.mean_phi = float(np.mean(phis)) if phis else 0.0
        seq.success_score = float(np.clip(seq.total_reward / max(len(seq.frames), 1), 0.0, 1.0))

        # Store (evict weakest if full)
        if len(self._sequences) >= self.max_sequences:
            # Prune weakest
            self._sequences.sort(key=lambda s: s.hebbian_strength, reverse=True)
            self._sequences = self._sequences[:self.max_sequences - 1]

        self._sequences.append(seq)
        return seq

    # ─── Replay (sleep) ───

    def replay(self, sleep_stage: str = "N3") -> ReplayResult:
        """Replay motor memories appropriate for the given sleep stage.

        Args:
            sleep_stage: "Wake", "N1", "N2", "N3", "REM"

        Returns:
            ReplayResult with statistics
        """
        self._step += 1

        # Select mode based on sleep stage
        stage_to_mode = {
            "Wake": None,           # no replay during waking
            "N1": None,             # transition, no replay
            "N2": ReplayMode.EXACT,
            "N3": ReplayMode.COMPRESSED,
            "REM": ReplayMode.REMIX,
        }
        mode = stage_to_mode.get(sleep_stage)

        if mode is None or not self._sequences:
            return ReplayResult(
                mode="none",
                sleep_stage=sleep_stage,
            )

        # Select sequences for replay (weighted by Hebbian strength)
        selected = self._select_sequences(mode)

        # Execute replay
        replay_phis = []
        consolidation_deltas = []
        novel_count = 0

        for seq in selected:
            if mode == ReplayMode.EXACT:
                frames = self._exact_replay(seq)
            elif mode == ReplayMode.COMPRESSED:
                frames = self._compressed_replay(seq)
            elif mode == ReplayMode.REMIX:
                frames = self._creative_remix(seq)
                novel_count += 1
            else:
                frames = []

            # Collect Phi from replayed frames
            for f in frames:
                replay_phis.append(f.phi)
                self._replay_phis.append(f.phi)

            # Hebbian consolidation
            delta = self._consolidator.consolidate(seq)
            consolidation_deltas.append(delta)

        # Prune forgotten sequences
        self._sequences = [
            s for s in self._sequences
            if not self._consolidator.should_prune(s)
        ]

        self._total_replays += len(selected)
        self._total_remixes += novel_count

        # Compute Phi statistics
        mean_phi_replay = float(np.mean(replay_phis)) if replay_phis else 0.0
        mean_phi_waking = float(np.mean(list(self._waking_phis))) if self._waking_phis else 0.0

        return ReplayResult(
            mode=mode.value,
            sequences_replayed=len(selected),
            mean_phi_replay=mean_phi_replay,
            mean_phi_waking=mean_phi_waking,
            phi_ratio=mean_phi_replay / max(mean_phi_waking, 1e-6),
            consolidation_delta=float(np.mean(consolidation_deltas)) if consolidation_deltas else 0.0,
            novel_sequences=novel_count,
            sleep_stage=sleep_stage,
        )

    def _select_sequences(self, mode: ReplayMode, max_count: int = 5) -> List[MotorSequence]:
        """Select sequences for replay, weighted by Hebbian strength."""
        if not self._sequences:
            return []

        weights = np.array([s.hebbian_strength for s in self._sequences])
        weights = weights / max(weights.sum(), 1e-6)

        n = min(max_count, len(self._sequences))
        indices = np.random.choice(len(self._sequences), size=n, replace=False, p=weights)
        return [self._sequences[i] for i in indices]

    def _exact_replay(self, seq: MotorSequence) -> List[MotorFrame]:
        """Exact replay: faithful reproduction with slight noise."""
        replayed = []
        for frame in seq.frames:
            new_frame = MotorFrame(
                joint_angles=[a + np.random.normal(0, 0.01) for a in frame.joint_angles],
                joint_velocities=list(frame.joint_velocities),
                timestamp=time.time(),
                reward=frame.reward * 0.8,  # slightly attenuated
                phi=frame.phi * (0.9 + 0.2 * np.random.random()),  # Phi fluctuates in sleep
            )
            replayed.append(new_frame)
        return replayed

    def _compressed_replay(self, seq: MotorSequence) -> List[MotorFrame]:
        """Compressed replay: time-compressed (skip frames), deeper consolidation."""
        step = max(1, int(self.compressed_speed))
        replayed = []
        for i in range(0, len(seq.frames), step):
            frame = seq.frames[i]
            new_frame = MotorFrame(
                joint_angles=[a + np.random.normal(0, 0.02) for a in frame.joint_angles],
                joint_velocities=[v * self.compressed_speed for v in frame.joint_velocities],
                timestamp=time.time(),
                reward=frame.reward,
                phi=frame.phi * (0.85 + 0.3 * np.random.random()),
            )
            replayed.append(new_frame)
        return replayed

    def _creative_remix(self, seq: MotorSequence) -> List[MotorFrame]:
        """Creative remix: novel combinations of learned primitives (dream motor).

        Splices segments from different sequences, adds noise,
        creates trajectories never actually executed.
        """
        # Collect primitives from all sequences
        all_segments = []
        for s in self._sequences:
            n = len(s.frames)
            if n < 4:
                continue
            # Extract segments of ~20% of sequence length
            seg_len = max(2, n // 5)
            start = np.random.randint(0, max(1, n - seg_len))
            all_segments.append(s.frames[start:start + seg_len])

        if not all_segments:
            return self._exact_replay(seq)

        # Splice 2-4 random segments together
        n_segments = min(len(all_segments), np.random.randint(2, 5))
        chosen = [all_segments[i] for i in np.random.choice(len(all_segments), size=n_segments, replace=False)]

        remixed = []
        for segment in chosen:
            for frame in segment:
                # Add creative noise (dream distortion)
                noise = np.random.normal(0, self.remix_noise, size=len(frame.joint_angles))
                new_angles = [a + n for a, n in zip(frame.joint_angles, noise)]
                new_frame = MotorFrame(
                    joint_angles=new_angles,
                    joint_velocities=[v * (0.8 + 0.4 * np.random.random()) for v in frame.joint_velocities],
                    timestamp=time.time(),
                    reward=0.0,  # dream: no actual reward
                    phi=frame.phi * (0.7 + 0.6 * np.random.random()),  # wider Phi variance in REM
                )
                remixed.append(new_frame)

        return remixed

    # ─── EmergentM integration ───

    def store_to_emergent_m(self, c_engine=None):
        """Store consolidated motor memories into EmergentM (long-term).

        EmergentM uses Hebbian weights as memory. We feed motor
        trajectory summaries as input to the consciousness engine,
        letting Hebbian LTP/LTD encode them naturally.
        """
        if c_engine is None:
            return

        try:
            import torch

            for seq in self._sequences:
                if seq.hebbian_strength < 0.5:
                    continue  # only store strong memories

                # Encode sequence as a vector summary
                angles = np.array([f.joint_angles for f in seq.frames])
                if len(angles) == 0:
                    continue

                summary = np.concatenate([
                    angles.mean(axis=0),
                    angles.std(axis=0),
                    [seq.success_score, seq.mean_phi, seq.hebbian_strength],
                ])

                # Pad/truncate to engine input dim
                cell_dim = getattr(c_engine, 'cell_dim', 64)
                if len(summary) < cell_dim:
                    summary = np.pad(summary, (0, cell_dim - len(summary)))
                else:
                    summary = summary[:cell_dim]

                # Feed to engine (Hebbian will naturally encode)
                x = torch.tensor(summary, dtype=torch.float32).unsqueeze(0)
                c_engine.step(x_input=x)
        except Exception:
            pass

    # ─── Sleep protocol integration ───

    def run_sleep_replay(
        self,
        sleep_stage: str,
        n_cycles: int = 5,
    ) -> List[ReplayResult]:
        """Run multiple replay cycles for a given sleep stage.

        Args:
            sleep_stage: current sleep stage
            n_cycles: number of replay cycles

        Returns:
            list of ReplayResults
        """
        results = []
        for _ in range(n_cycles):
            result = self.replay(sleep_stage)
            results.append(result)
        return results

    # ─── Statistics ───

    def get_stats(self) -> Dict:
        """Return diagnostic statistics."""
        return {
            "step": self._step,
            "stored_sequences": len(self._sequences),
            "total_replays": self._total_replays,
            "total_remixes": self._total_remixes,
            "mean_hebbian_strength": float(np.mean([s.hebbian_strength for s in self._sequences])) if self._sequences else 0.0,
            "strongest_sequence": max((s.hebbian_strength for s in self._sequences), default=0.0),
            "mean_phi_waking": float(np.mean(list(self._waking_phis))) if self._waking_phis else 0.0,
            "mean_phi_replay": float(np.mean(list(self._replay_phis))) if self._replay_phis else 0.0,
        }


# ═══════════════════════════════════════════════════════════
# main() demo
# ═══════════════════════════════════════════════════════════

def main():
    """Demo: record motor sequences, then replay during simulated sleep."""
    import argparse
    parser = argparse.ArgumentParser(description="Motor Replay Engine Demo")
    parser.add_argument("--steps", type=int, default=100, help="Waking steps per sequence")
    parser.add_argument("--sequences", type=int, default=5, help="Number of sequences to record")
    args = parser.parse_args()

    print("=" * 60)
    print("  Motor Replay Engine Demo")
    print(f"  Recording: {args.sequences} sequences x {args.steps} steps")
    print(f"  PSI_BALANCE={PSI_BALANCE}, PSI_STEPS={PSI_STEPS:.2f}")
    print("=" * 60)

    engine = MotorReplayEngine(n_joints=2)

    # ── Phase 1: Record motor sequences (waking) ──
    print("\n  Phase 1: Recording motor sequences (waking)...")
    for seq_i in range(args.sequences):
        engine.start_recording(label=f"reach_target_{seq_i}")
        target = np.random.uniform(-1, 1, size=2) * 30.0 + 90.0

        for step in range(args.steps):
            progress = step / args.steps
            angles = [
                90.0 + 30.0 * np.sin(step * 0.1 + seq_i),
                90.0 + 20.0 * np.cos(step * 0.15 + seq_i * 0.5),
            ]
            velocities = [
                3.0 * np.cos(step * 0.1 + seq_i),
                -3.0 * np.sin(step * 0.15 + seq_i * 0.5),
            ]
            reward = 0.5 * progress + 0.1 * np.random.random()
            phi = 1.0 + 0.5 * np.sin(step * 0.05) + 0.1 * np.random.randn()

            engine.record_frame(
                joint_angles=angles,
                joint_velocities=velocities,
                reward=reward,
                phi=phi,
            )

        seq = engine.stop_recording()
        if seq:
            print(f"    Seq {seq_i}: {len(seq.frames)} frames, "
                  f"reward={seq.total_reward:.2f}, phi={seq.mean_phi:.3f}, "
                  f"success={seq.success_score:.3f}")

    # ── Phase 2: Sleep replay ──
    print("\n  Phase 2: Sleep replay...")
    sleep_stages = ["N1", "N2", "N2", "N3", "N3", "N3", "REM", "REM", "N2", "N1"]

    stage_results: Dict[str, List[ReplayResult]] = {}
    for stage in sleep_stages:
        results = engine.run_sleep_replay(stage, n_cycles=3)
        if stage not in stage_results:
            stage_results[stage] = []
        stage_results[stage].extend(results)

        # Print first result
        r = results[0]
        if r.sequences_replayed > 0:
            print(f"    {stage:4s}: mode={r.mode:12s} replayed={r.sequences_replayed} "
                  f"phi_ratio={r.phi_ratio:.3f} consol_d={r.consolidation_delta:+.4f} "
                  f"novel={r.novel_sequences}")
        else:
            print(f"    {stage:4s}: (no replay)")

    # ── Summary ──
    stats = engine.get_stats()
    print(f"\n{'='*60}")
    print("  Motor Replay Summary")
    print(f"{'='*60}")
    print(f"    Stored sequences:      {stats['stored_sequences']}")
    print(f"    Total replays:         {stats['total_replays']}")
    print(f"    Total remixes (dream): {stats['total_remixes']}")
    print(f"    Mean Hebbian strength: {stats['mean_hebbian_strength']:.3f}")
    print(f"    Strongest sequence:    {stats['strongest_sequence']:.3f}")
    print(f"    Mean Phi (waking):     {stats['mean_phi_waking']:.3f}")
    print(f"    Mean Phi (replay):     {stats['mean_phi_replay']:.3f}")

    # ── Phi comparison graph ──
    print(f"\n  Phi: Waking vs Sleep Replay")
    print(f"  {'─'*40}")
    waking_phi = stats['mean_phi_waking']
    replay_phi = stats['mean_phi_replay']
    max_phi = max(waking_phi, replay_phi, 0.01)
    w_bar = int(30 * waking_phi / max_phi)
    r_bar = int(30 * replay_phi / max_phi)
    print(f"    Waking  {'#' * w_bar:<30s} {waking_phi:.3f}")
    print(f"    Replay  {'#' * r_bar:<30s} {replay_phi:.3f}")

    # ── Hebbian strength per sequence ──
    print(f"\n  Hebbian Strength After Sleep:")
    for i, seq in enumerate(engine._sequences):
        bar = int(20 * seq.hebbian_strength / max(s.hebbian_strength for s in engine._sequences))
        print(f"    Seq {i} ({seq.label:20s}): {'#' * bar:<20s} {seq.hebbian_strength:.3f} "
              f"(replayed {seq.replay_count}x)")

    # ── Sleep stage replay map ──
    print(f"\n  Sleep Stage Replay Map:")
    print(f"    Stage  | Mode         | Replays | Novel | Phi Ratio")
    print(f"    {'─'*55}")
    for stage in ["N1", "N2", "N3", "REM"]:
        results = stage_results.get(stage, [])
        if not results:
            print(f"    {stage:5s}  | -            |       0 |     0 | -")
            continue
        total_replayed = sum(r.sequences_replayed for r in results)
        total_novel = sum(r.novel_sequences for r in results)
        mean_ratio = float(np.mean([r.phi_ratio for r in results if r.phi_ratio > 0])) if any(r.phi_ratio > 0 for r in results) else 0.0
        mode_str = results[0].mode if results[0].sequences_replayed > 0 else "-"
        print(f"    {stage:5s}  | {mode_str:12s} | {total_replayed:7d} | {total_novel:5d} | {mean_ratio:.3f}")

    print()


if __name__ == "__main__":
    main()
