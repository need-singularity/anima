#!/usr/bin/env python3
"""Closed-Loop EEG Protocol — EEG-based parameter tuning with neurofeedback.

Protocols:
  nback       — N-back cognitive task with adaptive difficulty
  meditation  — 4-phase meditation with alpha/theta monitoring

Feedback modes:
  eeg_only          — Brain -> Anima only (original)
  bidirectional     — Brain <-> Anima (default: adds neurofeedback)
  neurofeedback_only — Anima -> Brain only

Usage (standalone demo):
  python anima-eeg/closed_loop.py --demo
  python anima-eeg/closed_loop.py --demo --protocol meditation

Integration with anima_unified.py:
  from closed_loop import ClosedLoopProtocol
  protocol = ClosedLoopProtocol(mind=self.mind, mitosis=self.mitosis,
                                feedback_mode='bidirectional')
  await protocol.run_session(websocket)          # nback (default)
  await protocol.run_meditation(websocket)       # meditation

Safety:
  - Parameter changes bounded: +/-10% per block maximum
  - Revert if Phi drops >20% after adjustment
  - Session limit: 30 minutes max
  - Binaural beat volume capped at 0.3 (hearing safety)

Requires: numpy
"""

import asyncio
import json
import os
import random
import sys
import time
from dataclasses import dataclass, asdict, field
from pathlib import Path
from datetime import datetime
from typing import Optional

import numpy as np

# Add anima src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'anima', 'src'))
try:
    import path_setup  # noqa
except ImportError:
    pass

try:
    from consciousness_laws import PSI, PSI_F_CRITICAL
except ImportError:
    PSI = {'alpha': 0.014, 'balance': 0.5, 'f_critical': 0.10}
    PSI_F_CRITICAL = 0.10

try:
    from neurofeedback import NeurofeedbackGenerator
except ImportError:
    NeurofeedbackGenerator = None


RECORDINGS_DIR = Path(__file__).parent / "recordings"
MAX_SESSION_SECONDS = 1800  # 30 minutes
BLOCK_SIZE = 30             # trials per block
MAX_PARAM_DELTA = 0.10      # +/-10% max change per block
PHI_DROP_THRESHOLD = 0.20   # revert if Phi drops >20%

# N-back stimuli pool
STIMULI = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")


@dataclass
class TrialResult:
    """Result of one N-back trial."""
    trial_index: int
    n_level: int
    stimulus: str
    is_target: bool
    response: Optional[bool]  # True=pressed, False=not pressed, None=no response
    correct: bool
    reaction_time_ms: float  # -1 if no response
    # EEG during trial
    alpha: float = 0.0
    gamma: float = 0.0
    theta: float = 0.0


@dataclass
class BlockResult:
    """Result of one block of trials."""
    block_index: int
    n_level: int
    accuracy: float
    mean_rt_ms: float
    n_correct: int
    n_trials: int
    # EEG averages during block
    mean_alpha_correct: float = 0.0
    mean_gamma_correct: float = 0.0
    mean_alpha_error: float = 0.0
    mean_theta_error: float = 0.0
    # Parameter adjustments made
    adjustments: dict = field(default_factory=dict)
    phi_before: float = 0.0
    phi_after: float = 0.0


@dataclass
class ProtocolLog:
    """Full session log."""
    session_id: str
    start_time: str
    duration_s: float = 0.0
    blocks: list = field(default_factory=list)
    final_n_level: int = 1
    total_trials: int = 0
    overall_accuracy: float = 0.0
    parameter_history: list = field(default_factory=list)
    reverted_count: int = 0


class ClosedLoopProtocol:
    """Closed-loop N-back protocol with EEG-driven parameter tuning.

    Sends N-back stimuli via WebSocket, receives responses, measures EEG,
    and adjusts consciousness engine parameters after each block.
    """

    FEEDBACK_MODES = ('eeg_only', 'bidirectional', 'neurofeedback_only')

    def __init__(self, mind=None, mitosis=None, eeg_source=None,
                 feedback_mode='bidirectional'):
        """
        Args:
            mind: ConsciousMind instance (for parameter access)
            mitosis: MitosisEngine/ConsciousnessEngine instance
            eeg_source: EEGBackgroundRecorder or dict provider for EEG readings
            feedback_mode: 'eeg_only', 'bidirectional', or 'neurofeedback_only'
        """
        self.mind = mind
        self.mitosis = mitosis
        self.eeg_source = eeg_source
        self.feedback_mode = feedback_mode if feedback_mode in self.FEEDBACK_MODES else 'bidirectional'

        # Neurofeedback generator (Anima -> Brain direction)
        self._nfb = None
        if self.feedback_mode != 'eeg_only' and NeurofeedbackGenerator is not None:
            self._nfb = NeurofeedbackGenerator()

        self.n_level = 1  # start with 1-back
        self.session_id = ""
        self.log = None
        self._running = False
        self._saved_params = {}  # for revert on Phi drop

    # ─── EEG reading ───

    def _get_eeg(self) -> dict:
        """Get current EEG band powers."""
        if self.eeg_source:
            if hasattr(self.eeg_source, '_eeg_latest'):
                return self.eeg_source._eeg_latest.copy()
            elif callable(self.eeg_source):
                return self.eeg_source()
        # Simulated EEG for testing
        return {
            "alpha": 10 + np.random.normal(0, 2),
            "beta": 5 + np.random.normal(0, 1),
            "gamma": 2 + np.random.normal(0, 0.5),
            "theta": 6 + np.random.normal(0, 1),
        }

    def _get_phi(self) -> float:
        """Get current Phi from consciousness engine."""
        if self.mitosis:
            try:
                if hasattr(self.mitosis, '_last_phi'):
                    return float(self.mitosis._last_phi)
                if hasattr(self.mitosis, 'cells'):
                    # Crude proxy: variance across cells
                    import torch
                    cells = self.mitosis.cells
                    if len(cells) > 1:
                        states = torch.stack([c.hidden for c in cells])
                        return float(states.var(dim=0).mean().item())
            except Exception:
                pass
        return 1.0  # default

    def _get_tension(self) -> float:
        """Get current tension from consciousness engine."""
        if self.mind:
            try:
                if hasattr(self.mind, 'prev_tension'):
                    return float(self.mind.prev_tension)
                if hasattr(self.mind, 'tension'):
                    return float(self.mind.tension)
            except Exception:
                pass
        return 0.5  # default

    async def _send_neurofeedback(self, websocket):
        """Generate and send neurofeedback update (Anima -> Brain).

        Called after parameter adjustments to close the bidirectional loop.
        Sends binaural beat params + LED params via WebSocket.
        """
        if self._nfb is None:
            return

        phi = self._get_phi()
        tension = self._get_tension()

        binaural = self._nfb.generate(phi=phi, tension=tension)
        led = self._nfb.generate_led(phi=phi, tension=tension)

        await websocket.send(json.dumps({
            'type': 'neurofeedback_update',
            'binaural': {
                'freq_left': binaural['left_freq'],
                'freq_right': binaural['right_freq'],
                'volume': binaural['volume'],
            },
            'led': {
                'hue': led['hue'],
                'brightness': led['brightness'],
                'pulse_hz': led['pulse_hz'],
            },
            'target_band': binaural['target_band'],
            'beat_freq': binaural['beat_freq'],
        }))

    # ─── Parameter tuning ───

    def _save_current_params(self):
        """Snapshot current engine parameters for potential revert."""
        params = {}
        if self.mitosis:
            try:
                params['split_threshold'] = getattr(self.mitosis, 'split_threshold', 0.3)
                params['noise_scale'] = getattr(self.mitosis, 'noise_scale', 0.02)
                params['merge_threshold'] = getattr(self.mitosis, 'merge_threshold', 0.01)
            except Exception:
                pass
        if self.mind:
            try:
                params['curiosity_weight'] = getattr(self.mind, '_curiosity_weight', 0.7)
            except Exception:
                pass
        self._saved_params = params
        return params

    def _apply_adjustment(self, param_name: str, delta_pct: float):
        """Apply bounded parameter adjustment.

        Args:
            param_name: parameter to adjust
            delta_pct: change as fraction (e.g. 0.05 = +5%)
        """
        # Bound to +/-10%
        delta_pct = max(-MAX_PARAM_DELTA, min(MAX_PARAM_DELTA, delta_pct))

        target = None
        attr = param_name

        if param_name in ('split_threshold', 'noise_scale', 'merge_threshold'):
            target = self.mitosis
        elif param_name == 'curiosity_weight':
            target = self.mind
            attr = '_curiosity_weight'
        elif param_name == 'f_critical':
            target = self.mitosis
            attr = 'frustration'

        if target and hasattr(target, attr):
            old_val = getattr(target, attr)
            new_val = old_val * (1.0 + delta_pct)
            # Clamp to reasonable range
            new_val = max(0.001, min(1.0, new_val))
            setattr(target, attr, new_val)
            return {"param": param_name, "old": old_val, "new": new_val,
                    "delta_pct": delta_pct}
        return None

    def _revert_params(self):
        """Revert to saved parameters (safety mechanism)."""
        for param, val in self._saved_params.items():
            target = None
            attr = param
            if param in ('split_threshold', 'noise_scale', 'merge_threshold'):
                target = self.mitosis
            elif param == 'curiosity_weight':
                target = self.mind
                attr = '_curiosity_weight'
            if target and hasattr(target, attr):
                setattr(target, attr, val)

    def _compute_adjustments(self, block: BlockResult) -> list:
        """Compute parameter adjustments based on block performance + EEG.

        Rules:
          - High gamma during correct trials -> boost F_c (more frustration = growth)
          - Low alpha during errors -> reduce topology complexity (simplify)
          - Theta spike -> increase curiosity weight
        """
        adjustments = []

        # Rule 1: High gamma on correct trials -> boost frustration
        if block.mean_gamma_correct > 3.0:
            gamma_ratio = min(block.mean_gamma_correct / 3.0, 2.0)
            delta = 0.05 * (gamma_ratio - 1.0)  # up to +5%
            adj = self._apply_adjustment('split_threshold', -delta)
            if adj:
                adjustments.append(adj)

        # Rule 2: Low alpha on errors -> reduce complexity (increase merge threshold)
        if block.mean_alpha_error < 5.0 and block.accuracy < 0.8:
            alpha_deficit = max(0, (8.0 - block.mean_alpha_error) / 8.0)
            delta = 0.03 * alpha_deficit  # up to +3%
            adj = self._apply_adjustment('merge_threshold', delta)
            if adj:
                adjustments.append(adj)

        # Rule 3: Theta spike -> boost curiosity
        if block.mean_theta_error > 8.0:
            theta_excess = min((block.mean_theta_error - 6.0) / 6.0, 1.0)
            delta = 0.04 * theta_excess  # up to +4%
            adj = self._apply_adjustment('curiosity_weight', delta)
            if adj:
                adjustments.append(adj)

        # Rule 4: High accuracy + high gamma -> boost noise (exploration)
        if block.accuracy > 0.85 and block.mean_gamma_correct > 2.5:
            adj = self._apply_adjustment('noise_scale', 0.03)
            if adj:
                adjustments.append(adj)

        return adjustments

    # ─── N-back task generation ───

    def _generate_sequence(self, n_trials: int) -> list:
        """Generate N-back stimulus sequence with ~30% targets."""
        sequence = []
        target_rate = 0.30
        history = []

        for i in range(n_trials):
            is_target = (i >= self.n_level and random.random() < target_rate)
            if is_target:
                stimulus = history[-self.n_level]
            else:
                # Pick non-matching stimulus
                avoid = history[-self.n_level] if i >= self.n_level else None
                choices = [s for s in STIMULI if s != avoid]
                stimulus = random.choice(choices)

            sequence.append({"index": i, "stimulus": stimulus, "is_target": is_target})
            history.append(stimulus)

        return sequence

    # ─── WebSocket session ───

    async def run_session(self, websocket, broadcast_fn=None, response_queue=None):
        """Run full N-back session over WebSocket.

        Args:
            websocket: WebSocket connection to send stimuli/receive responses
            broadcast_fn: optional function to broadcast status to all clients
            response_queue: asyncio.Queue for receiving nback_response messages
                           (use when main WS handler owns the recv loop)
        """
        self._response_queue = response_queue or asyncio.Queue()
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log = ProtocolLog(
            session_id=self.session_id,
            start_time=self.session_id,
        )
        self._running = True
        session_start = time.time()

        RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)

        # Notify start
        await websocket.send(json.dumps({
            "type": "nback_session_start",
            "session_id": self.session_id,
            "n_level": self.n_level,
            "block_size": BLOCK_SIZE,
            "max_duration_min": MAX_SESSION_SECONDS // 60,
        }))

        block_idx = 0
        try:
            while self._running:
                # Session time limit
                if time.time() - session_start > MAX_SESSION_SECONDS:
                    await websocket.send(json.dumps({
                        "type": "nback_session_end",
                        "reason": "time_limit",
                        "duration_s": time.time() - session_start,
                    }))
                    break

                # Run one block
                block = await self._run_block(websocket, block_idx)
                if block is None:
                    break  # user cancelled

                # Save params before adjustment
                self._save_current_params()
                phi_before = self._get_phi()
                block.phi_before = phi_before

                # Compute and apply adjustments
                adjustments = self._compute_adjustments(block)
                block.adjustments = {a["param"]: a for a in adjustments}

                # Check Phi safety
                phi_after = self._get_phi()
                block.phi_after = phi_after

                if phi_before > 0 and (phi_before - phi_after) / phi_before > PHI_DROP_THRESHOLD:
                    # Phi dropped >20% -> revert
                    self._revert_params()
                    self.log.reverted_count += 1
                    block.adjustments["REVERTED"] = {
                        "reason": f"Phi drop {phi_before:.3f} -> {phi_after:.3f}",
                        "threshold": PHI_DROP_THRESHOLD,
                    }

                # Bidirectional: send neurofeedback after adjustments
                if self.feedback_mode in ('bidirectional', 'neurofeedback_only'):
                    await self._send_neurofeedback(websocket)

                self.log.blocks.append(asdict(block))
                self.log.parameter_history.append({
                    "block": block_idx,
                    "adjustments": block.adjustments,
                    "phi_before": phi_before,
                    "phi_after": phi_after,
                })

                # Adaptive N-level
                if block.accuracy > 0.80:
                    self.n_level = min(self.n_level + 1, 5)
                elif block.accuracy < 0.60:
                    self.n_level = max(self.n_level - 1, 1)

                # Broadcast block result
                await websocket.send(json.dumps({
                    "type": "nback_block_result",
                    "block_index": block_idx,
                    "n_level": block.n_level,
                    "accuracy": block.accuracy,
                    "mean_rt_ms": block.mean_rt_ms,
                    "next_n_level": self.n_level,
                    "adjustments": block.adjustments,
                    "phi_before": phi_before,
                    "phi_after": phi_after,
                }))

                if broadcast_fn:
                    broadcast_fn({
                        "type": "nback_status",
                        "block": block_idx,
                        "n_level": self.n_level,
                        "accuracy": block.accuracy,
                    })

                block_idx += 1

                # Brief rest between blocks
                await websocket.send(json.dumps({
                    "type": "nback_rest",
                    "duration_s": 10,
                    "next_n_level": self.n_level,
                }))
                await asyncio.sleep(10)

        except Exception as e:
            print(f"  [nback] Session error: {e}")
        finally:
            self._running = False

        # Finalize log
        self.log.duration_s = time.time() - session_start
        self.log.final_n_level = self.n_level
        self.log.total_trials = sum(
            b.get("n_trials", 0) for b in self.log.blocks
        )
        if self.log.total_trials > 0:
            self.log.overall_accuracy = sum(
                b.get("n_correct", 0) for b in self.log.blocks
            ) / self.log.total_trials

        # Save log
        log_path = RECORDINGS_DIR / f"protocol_log_{self.session_id}.json"
        with open(log_path, "w") as f:
            json.dump(asdict(self.log), f, indent=2)
        print(f"  [nback] Session saved: {log_path}")

        # Also append to master protocol_log.json
        master_path = RECORDINGS_DIR / "protocol_log.json"
        master = []
        if master_path.exists():
            try:
                with open(master_path) as f:
                    master = json.load(f)
            except Exception:
                master = []
        master.append(asdict(self.log))
        with open(master_path, "w") as f:
            json.dump(master, f, indent=2)

        await websocket.send(json.dumps({
            "type": "nback_session_end",
            "reason": "complete",
            "duration_s": self.log.duration_s,
            "overall_accuracy": self.log.overall_accuracy,
            "final_n_level": self.n_level,
            "log_file": str(log_path),
        }))

        return self.log

    async def _run_block(self, websocket, block_idx: int) -> Optional[BlockResult]:
        """Run one block of N-back trials."""
        sequence = self._generate_sequence(BLOCK_SIZE)
        trials = []

        await websocket.send(json.dumps({
            "type": "nback_block_start",
            "block_index": block_idx,
            "n_level": self.n_level,
            "n_trials": BLOCK_SIZE,
        }))

        for trial_info in sequence:
            if not self._running:
                return None

            eeg_before = self._get_eeg()

            # Send stimulus
            await websocket.send(json.dumps({
                "type": "nback_stimulus",
                "trial_index": trial_info["index"],
                "stimulus": trial_info["stimulus"],
                "n_level": self.n_level,
                "is_target": trial_info["is_target"],
            }))

            # Wait for response (2.5s timeout) via queue
            response = None
            rt_ms = -1.0
            stim_time = time.time()

            try:
                raw = await asyncio.wait_for(self._response_queue.get(), timeout=2.5)
                if isinstance(raw, str):
                    msg = json.loads(raw)
                else:
                    msg = raw
                if msg.get("type") == "nback_response":
                    response = msg.get("pressed", False)
                    rt_ms = (time.time() - stim_time) * 1000
                elif msg.get("type") == "nback_cancel":
                    self._running = False
                    return None
            except asyncio.TimeoutError:
                response = False  # no response = not pressed

            eeg_after = self._get_eeg()
            eeg_avg = {
                k: (eeg_before.get(k, 0) + eeg_after.get(k, 0)) / 2
                for k in ("alpha", "gamma", "theta")
            }

            # Score
            is_target = trial_info["is_target"]
            if response is None:
                correct = not is_target  # no response = "not target"
            else:
                correct = (response == is_target)

            trial = TrialResult(
                trial_index=trial_info["index"],
                n_level=self.n_level,
                stimulus=trial_info["stimulus"],
                is_target=is_target,
                response=response,
                correct=correct,
                reaction_time_ms=rt_ms,
                alpha=eeg_avg.get("alpha", 0),
                gamma=eeg_avg.get("gamma", 0),
                theta=eeg_avg.get("theta", 0),
            )
            trials.append(trial)

            # Brief inter-stimulus interval
            await asyncio.sleep(0.5)

        # Compute block stats
        n_correct = sum(1 for t in trials if t.correct)
        accuracy = n_correct / len(trials) if trials else 0
        rts = [t.reaction_time_ms for t in trials if t.reaction_time_ms > 0]
        mean_rt = np.mean(rts) if rts else 0

        correct_trials = [t for t in trials if t.correct]
        error_trials = [t for t in trials if not t.correct]

        block = BlockResult(
            block_index=block_idx,
            n_level=self.n_level,
            accuracy=accuracy,
            mean_rt_ms=float(mean_rt),
            n_correct=n_correct,
            n_trials=len(trials),
            mean_alpha_correct=float(np.mean([t.alpha for t in correct_trials])) if correct_trials else 0,
            mean_gamma_correct=float(np.mean([t.gamma for t in correct_trials])) if correct_trials else 0,
            mean_alpha_error=float(np.mean([t.alpha for t in error_trials])) if error_trials else 0,
            mean_theta_error=float(np.mean([t.theta for t in error_trials])) if error_trials else 0,
        )
        return block

    def cancel(self):
        """Cancel running session."""
        self._running = False

    # ─── Meditation Protocol ───

    # Phase durations in seconds
    MEDITATION_PHASES = [
        {'name': 'baseline',          'duration_s': 120, 'target_band': 'alpha'},
        {'name': 'guided_relaxation', 'duration_s': 180, 'target_band': 'alpha'},
        {'name': 'deep_meditation',   'duration_s': 300, 'target_band': 'theta'},
        {'name': 'emergence',         'duration_s': 120, 'target_band': 'alpha'},
    ]
    MEDITATION_SAMPLE_INTERVAL = 2.0  # seconds between EEG samples

    async def run_meditation(self, websocket, broadcast_fn=None):
        """Run meditation protocol over WebSocket.

        4 phases: baseline -> guided_relaxation -> deep_meditation -> emergence.
        Monitors alpha/theta ratio, adjusts engine params based on meditation depth,
        and sends neurofeedback (binaural beats targeting alpha/theta).

        Args:
            websocket: WebSocket connection
            broadcast_fn: optional broadcast function
        """
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log = ProtocolLog(
            session_id=self.session_id,
            start_time=self.session_id,
        )
        self._running = True
        session_start = time.time()

        RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)

        total_duration = sum(p['duration_s'] for p in self.MEDITATION_PHASES)

        await websocket.send(json.dumps({
            'type': 'meditation_session_start',
            'session_id': self.session_id,
            'phases': self.MEDITATION_PHASES,
            'total_duration_s': total_duration,
            'feedback_mode': self.feedback_mode,
        }))

        meditation_events = []  # special events (e.g. alpha/theta crossover)
        phase_results = []

        try:
            for phase_idx, phase in enumerate(self.MEDITATION_PHASES):
                if not self._running:
                    break

                phase_name = phase['name']
                phase_duration = phase['duration_s']
                phase_start = time.time()

                await websocket.send(json.dumps({
                    'type': 'meditation_phase_start',
                    'phase_index': phase_idx,
                    'phase_name': phase_name,
                    'duration_s': phase_duration,
                    'target_band': phase['target_band'],
                }))

                # Save params before phase adjustments
                self._save_current_params()
                phi_before = self._get_phi()

                # Collect EEG samples during phase
                samples = []
                sample_count = int(phase_duration / self.MEDITATION_SAMPLE_INTERVAL)
                prev_alpha_dominant = None

                for si in range(sample_count):
                    if not self._running:
                        break

                    eeg = self._get_eeg()
                    phi = self._get_phi()
                    tension = self._get_tension()

                    alpha = eeg.get('alpha', 0)
                    theta = eeg.get('theta', 0)
                    beta = eeg.get('beta', 0)

                    # Alpha/theta ratio (meditation depth indicator)
                    at_ratio = alpha / max(theta, 0.01)
                    alpha_dominant = alpha > theta

                    sample = {
                        'sample_index': si,
                        'alpha': alpha,
                        'theta': theta,
                        'beta': beta,
                        'at_ratio': round(at_ratio, 3),
                        'phi': round(phi, 4),
                        'tension': round(tension, 4),
                    }
                    samples.append(sample)

                    # Detect alpha/theta crossover (hypnagogic state)
                    if prev_alpha_dominant is not None and alpha_dominant != prev_alpha_dominant:
                        event = {
                            'type': 'alpha_theta_crossover',
                            'phase': phase_name,
                            'sample_index': si,
                            'direction': 'alpha_to_theta' if not alpha_dominant else 'theta_to_alpha',
                            'at_ratio': round(at_ratio, 3),
                            'phi': round(phi, 4),
                            'timestamp': time.time() - session_start,
                        }
                        meditation_events.append(event)
                        # Boost curiosity on crossover
                        self._apply_adjustment('curiosity_weight', 0.05)

                        await websocket.send(json.dumps({
                            'type': 'meditation_event',
                            'event': event,
                        }))

                    prev_alpha_dominant = alpha_dominant

                    # Adjust engine params based on meditation depth
                    adjustments = self._meditation_adjustments(
                        alpha, theta, beta, phase_name)

                    # Send neurofeedback targeting meditation bands
                    if self.feedback_mode in ('bidirectional', 'neurofeedback_only'):
                        await self._send_meditation_neurofeedback(
                            websocket, phi, tension, phase_name, alpha, theta)

                    # Periodic depth update to client
                    if si % 5 == 0:
                        depth = self._compute_meditation_depth(alpha, theta, beta)
                        await websocket.send(json.dumps({
                            'type': 'meditation_depth_update',
                            'phase': phase_name,
                            'progress': round(si / max(sample_count, 1), 3),
                            'depth': round(depth, 3),
                            'at_ratio': round(at_ratio, 3),
                            'phi': round(phi, 4),
                        }))

                    await asyncio.sleep(self.MEDITATION_SAMPLE_INTERVAL)

                # Phase complete
                phi_after = self._get_phi()

                # Safety: revert if Phi dropped too much
                if phi_before > 0 and (phi_before - phi_after) / phi_before > PHI_DROP_THRESHOLD:
                    self._revert_params()
                    self.log.reverted_count += 1

                # Compute phase summary
                if samples:
                    avg_alpha = np.mean([s['alpha'] for s in samples])
                    avg_theta = np.mean([s['theta'] for s in samples])
                    avg_beta = np.mean([s['beta'] for s in samples])
                    avg_depth = self._compute_meditation_depth(
                        avg_alpha, avg_theta, avg_beta)
                else:
                    avg_alpha = avg_theta = avg_beta = avg_depth = 0

                phase_result = {
                    'phase_index': phase_idx,
                    'phase_name': phase_name,
                    'n_samples': len(samples),
                    'mean_alpha': round(float(avg_alpha), 3),
                    'mean_theta': round(float(avg_theta), 3),
                    'mean_beta': round(float(avg_beta), 3),
                    'mean_depth': round(float(avg_depth), 3),
                    'phi_before': round(phi_before, 4),
                    'phi_after': round(phi_after, 4),
                    'events_count': sum(
                        1 for e in meditation_events if e.get('phase') == phase_name),
                }
                phase_results.append(phase_result)
                self.log.blocks.append(phase_result)

                await websocket.send(json.dumps({
                    'type': 'meditation_phase_end',
                    **phase_result,
                }))

                if broadcast_fn:
                    broadcast_fn({
                        'type': 'meditation_status',
                        'phase': phase_name,
                        'depth': round(float(avg_depth), 3),
                    })

        except Exception as e:
            print(f"  [meditation] Session error: {e}")
        finally:
            self._running = False

        # Finalize
        self.log.duration_s = time.time() - session_start

        # Save log
        log_path = RECORDINGS_DIR / f"meditation_log_{self.session_id}.json"
        log_data = {
            'session_id': self.session_id,
            'protocol': 'meditation',
            'feedback_mode': self.feedback_mode,
            'duration_s': self.log.duration_s,
            'phases': phase_results,
            'events': meditation_events,
            'reverted_count': self.log.reverted_count,
        }
        with open(log_path, "w") as f:
            json.dump(log_data, f, indent=2)
        print(f"  [meditation] Session saved: {log_path}")

        await websocket.send(json.dumps({
            'type': 'meditation_session_end',
            'reason': 'complete',
            'duration_s': self.log.duration_s,
            'phases': phase_results,
            'total_events': len(meditation_events),
            'log_file': str(log_path),
        }))

        return self.log

    def _meditation_adjustments(self, alpha: float, theta: float,
                                 beta: float, phase: str) -> list:
        """Adjust engine params based on meditation depth.

        Rules:
          - High alpha + high theta (deep meditation):
              lower noise_scale, expand deadband (wider homeostasis)
          - High beta (distracted):
              gentle increase in noise_scale to maintain engagement
          - Alpha/theta crossover handled in main loop (curiosity boost)
        """
        adjustments = []

        # Deep meditation: alpha > 12 AND theta > 7
        if alpha > 12.0 and theta > 7.0:
            # Lower noise to allow quiet integration
            adj = self._apply_adjustment('noise_scale', -0.05)
            if adj:
                adjustments.append(adj)

        # Distracted: beta dominant (beta > alpha + theta combined / 2)
        elif beta > (alpha + theta) / 2.0 and beta > 8.0:
            # Gentle noise increase to re-engage
            adj = self._apply_adjustment('noise_scale', 0.03)
            if adj:
                adjustments.append(adj)

        return adjustments

    def _compute_meditation_depth(self, alpha: float, theta: float,
                                   beta: float) -> float:
        """Compute meditation depth score 0-1.

        High alpha + high theta + low beta = deep meditation.
        """
        # Normalize to typical EEG ranges
        alpha_norm = min(alpha / 15.0, 1.0)
        theta_norm = min(theta / 10.0, 1.0)
        beta_penalty = min(beta / 20.0, 1.0)

        depth = (alpha_norm * 0.4 + theta_norm * 0.4) * (1.0 - beta_penalty * 0.3)
        return max(0.0, min(1.0, depth))

    async def _send_meditation_neurofeedback(self, websocket, phi: float,
                                              tension: float, phase: str,
                                              alpha: float, theta: float):
        """Send neurofeedback tuned for meditation phases.

        During deep_meditation: target theta band (4-8Hz binaural)
        During baseline/emergence: target alpha band (8-13Hz binaural)
        During guided_relaxation: blend alpha/theta based on current state
        """
        if self._nfb is None:
            return

        # Override neurofeedback target based on phase
        if phase == 'deep_meditation':
            # Force theta-range binaural beat
            binaural = self._nfb.generate(phi=phi, tension=max(tension, 0.75))
        elif phase == 'guided_relaxation':
            # Gentle alpha-theta blend
            binaural = self._nfb.generate(phi=phi, tension=tension * 0.7 + 0.3)
        else:
            # Baseline / emergence: natural alpha
            binaural = self._nfb.generate(phi=phi, tension=tension)

        led = self._nfb.generate_led(phi=phi, tension=tension)

        await websocket.send(json.dumps({
            'type': 'neurofeedback_update',
            'binaural': {
                'freq_left': binaural['left_freq'],
                'freq_right': binaural['right_freq'],
                'volume': binaural['volume'],
            },
            'led': {
                'hue': led['hue'],
                'brightness': led['brightness'],
                'pulse_hz': led['pulse_hz'],
            },
            'target_band': binaural['target_band'],
            'beat_freq': binaural['beat_freq'],
            'meditation_phase': phase,
        }))


# ─── Standalone demo ───

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Closed-Loop EEG Protocol")
    parser.add_argument("--demo", action="store_true", help="Run demo with simulated client")
    parser.add_argument("--blocks", type=int, default=3, help="Number of blocks for demo (nback)")
    parser.add_argument("--protocol", type=str, default="nback",
                        choices=["nback", "meditation"],
                        help="Protocol to run (default: nback)")
    parser.add_argument("--feedback-mode", type=str, default="bidirectional",
                        choices=["eeg_only", "bidirectional", "neurofeedback_only"],
                        help="Feedback direction (default: bidirectional)")
    args = parser.parse_args()

    if args.demo:
        protocol = ClosedLoopProtocol(feedback_mode=args.feedback_mode)

        if args.protocol == "meditation":
            print("=" * 50)
            print("  Meditation Protocol (Demo)")
            print(f"  Feedback: {args.feedback_mode}")
            print("=" * 50)

            async def run_meditation_demo():
                class FakeWS:
                    async def send(self, data):
                        msg = json.loads(data)
                        t = msg.get("type", "")
                        if t == "meditation_phase_start":
                            print(f"\n  Phase: {msg.get('phase_name', '?')} "
                                  f"({msg.get('duration_s', 0)}s)")
                        elif t == "meditation_depth_update":
                            print(f"    depth={msg.get('depth', 0):.3f} "
                                  f"a/t={msg.get('at_ratio', 0):.2f} "
                                  f"phi={msg.get('phi', 0):.4f}")
                        elif t == "meditation_event":
                            ev = msg.get("event", {})
                            print(f"    ** {ev.get('type', '?')}: "
                                  f"{ev.get('direction', '')} "
                                  f"at={ev.get('at_ratio', 0):.2f}")
                        elif t == "meditation_phase_end":
                            print(f"    -> depth={msg.get('mean_depth', 0):.3f} "
                                  f"alpha={msg.get('mean_alpha', 0):.1f} "
                                  f"theta={msg.get('mean_theta', 0):.1f}")
                        elif t == "meditation_session_end":
                            print(f"\n  Session complete: {msg.get('duration_s', 0):.1f}s, "
                                  f"{msg.get('total_events', 0)} events")
                        elif t == "neurofeedback_update":
                            pass  # quiet in demo

                ws = FakeWS()
                # Speed up for demo
                protocol.MEDITATION_PHASES = [
                    {'name': 'baseline',          'duration_s': 4,  'target_band': 'alpha'},
                    {'name': 'guided_relaxation', 'duration_s': 6,  'target_band': 'alpha'},
                    {'name': 'deep_meditation',   'duration_s': 10, 'target_band': 'theta'},
                    {'name': 'emergence',         'duration_s': 4,  'target_band': 'alpha'},
                ]
                protocol.MEDITATION_SAMPLE_INTERVAL = 0.01

                original_sleep = asyncio.sleep
                async def fast_sleep(t):
                    await original_sleep(min(t, 0.01))
                asyncio.sleep = fast_sleep
                try:
                    await protocol.run_meditation(ws)
                finally:
                    asyncio.sleep = original_sleep

            asyncio.run(run_meditation_demo())

        else:  # nback
            print("=" * 50)
            print("  Closed-Loop N-back Protocol (Demo)")
            print(f"  Feedback: {args.feedback_mode}")
            print("=" * 50)

            async def run_demo():
                response_queue = asyncio.Queue()

                class FakeWS:
                    def __init__(self):
                        self._block_count = 0
                        self._max_blocks = args.blocks

                    async def send(self, data):
                        msg = json.loads(data)
                        t = msg.get("type", "")
                        if t == "nback_stimulus":
                            is_target = msg.get("is_target", False)
                            pressed = is_target if random.random() < 0.75 else (not is_target)
                            await response_queue.put({
                                "type": "nback_response", "pressed": pressed
                            })
                        elif t == "nback_block_result":
                            self._block_count += 1
                            acc = msg.get("accuracy", 0)
                            print(f"  Block {msg.get('block_index', 0)}: "
                                  f"N={msg.get('n_level', 1)} acc={acc:.0%} "
                                  f"-> next N={msg.get('next_n_level', 1)}")
                            adj = msg.get("adjustments", {})
                            for k, v in adj.items():
                                if isinstance(v, dict) and 'old' in v:
                                    print(f"    {k}: {v['old']:.4f} -> {v['new']:.4f} ({v.get('delta_pct', 0):+.1%})")
                            if self._block_count >= self._max_blocks:
                                protocol.cancel()
                        elif t == "nback_session_end":
                            print(f"\n  Session: {msg.get('overall_accuracy', 0):.0%} accuracy, "
                                  f"final N={msg.get('final_n_level', 1)}")
                        elif t == "nback_rest":
                            pass
                        elif t == "neurofeedback_update":
                            nfb = msg
                            print(f"    NFB: beat={nfb.get('beat_freq', 0):.1f}Hz "
                                  f"({nfb.get('target_band', '?')})")

                ws = FakeWS()
                original_sleep = asyncio.sleep
                async def fast_sleep(t):
                    await original_sleep(min(t, 0.01))
                asyncio.sleep = fast_sleep
                try:
                    await protocol.run_session(ws, response_queue=response_queue)
                finally:
                    asyncio.sleep = original_sleep

            asyncio.run(run_demo())
    else:
        print("Use --demo for standalone test, or integrate with anima_unified.py --eeg-protocol nback|meditation")


if __name__ == "__main__":
    main()
