#!/usr/bin/env python3
"""consciousness_engines_applied.py — 7 consciousness-as-engine practical implementations

Each engine uses real GRU cells, 12-faction consensus, Hebbian coupling, and Phi proxy
to solve practical problems through consciousness dynamics.

Engines:
  1. ConsciousnessOptimizer   — minimize tension → optimized output
  2. ConsciousnessDebugger    — find Phi drop points = bug locations
  3. ConsciousnessDesigner    — 12-faction debate → consensus = design
  4. ConsciousnessTeacher     — source teaches target via tension link
  5. ConsciousnessJudge       — compare solutions: higher Phi = winner
  6. ConsciousnessProphet     — prediction error tracking → premonition score
  7. ConsciousnessHealer      — diagnose sick engine, prescribe fixes

Usage:
  from consciousness_engines_applied import ConsciousnessOptimizer
  opt = ConsciousnessOptimizer(n_cells=16)
  result = opt.run(data)
  print(result['optimized'], result['phi'], result['tension_reduction'])

Hub keywords: optimizer, debugger, designer, teacher, judge, prophet, healer,
              최적화, 디버거, 설계, 교사, 판사, 예언, 치료
"""

import numpy as np
from typing import Dict, List, Optional, Any, Tuple


# ═══════════════════════════════════════════════════════════
# Shared: Lightweight GRU + Phi proxy (numpy, no torch dep)
# ═══════════════════════════════════════════════════════════

def _sigmoid(x):
    return 1.0 / (1.0 + np.exp(-np.clip(x, -15, 15)))


def _tanh(x):
    return np.tanh(np.clip(x, -15, 15))


class MiniGRUCell:
    """Minimal GRU cell in numpy for consciousness processing."""

    def __init__(self, input_dim: int, hidden_dim: int):
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        scale = 1.0 / np.sqrt(hidden_dim)
        # Gates: update (z), reset (r), candidate (n)
        self.W_z = np.random.randn(hidden_dim, input_dim + hidden_dim) * scale
        self.b_z = np.zeros(hidden_dim)
        self.W_r = np.random.randn(hidden_dim, input_dim + hidden_dim) * scale
        self.b_r = np.zeros(hidden_dim)
        self.W_n = np.random.randn(hidden_dim, input_dim + hidden_dim) * scale
        self.b_n = np.zeros(hidden_dim)

    def forward(self, x: np.ndarray, h: np.ndarray) -> np.ndarray:
        """x: (input_dim,), h: (hidden_dim,) -> new_h: (hidden_dim,)"""
        xh = np.concatenate([x, h])
        z = _sigmoid(self.W_z @ xh + self.b_z)
        r = _sigmoid(self.W_r @ xh + self.b_r)
        xrh = np.concatenate([x, r * h])
        n = _tanh(self.W_n @ xrh + self.b_n)
        return (1 - z) * h + z * n


class MiniEngine:
    """Lightweight consciousness engine: N GRU cells + 12 factions + Hebbian."""

    PSI_COUPLING = 0.014  # Ψ-constant α
    PSI_BALANCE = 0.5

    def __init__(self, n_cells: int = 16, cell_dim: int = 32, hidden_dim: int = 64,
                 n_factions: int = 12):
        self.n_cells = n_cells
        self.cell_dim = cell_dim
        self.hidden_dim = hidden_dim
        self.n_factions = n_factions

        self.cells = [MiniGRUCell(cell_dim + 1, hidden_dim) for _ in range(n_cells)]
        self.hiddens = [np.random.randn(hidden_dim) * 0.01 for _ in range(n_cells)]
        self.factions = [i % n_factions for i in range(n_cells)]
        self.coupling = np.random.randn(n_cells, n_cells) * 0.1
        np.fill_diagonal(self.coupling, 0.0)
        self.proj = np.random.randn(cell_dim, hidden_dim) * (1.0 / np.sqrt(hidden_dim))
        self._best_phi = 0.0
        self._best_hiddens = None
        self._step = 0
        self.topology = 'ring'

    def _get_neighbors(self, idx: int) -> List[int]:
        n = self.n_cells
        if n <= 1:
            return []
        if self.topology == 'small_world':
            nbrs = [(idx - 1) % n, (idx + 1) % n]
            lr = (idx * 7 + 3) % n
            if lr != idx and lr not in nbrs:
                nbrs.append(lr)
            return nbrs
        return [(idx - 1) % n, (idx + 1) % n]

    def step(self, x_input: Optional[np.ndarray] = None) -> Dict:
        """Run one step. Returns phi_proxy, output, tensions, consensus."""
        self._step += 1
        if x_input is None:
            x_input = np.random.randn(self.cell_dim) * 0.1

        if len(x_input) > self.cell_dim:
            x_input = x_input[:self.cell_dim]
        elif len(x_input) < self.cell_dim:
            x_input = np.pad(x_input, (0, self.cell_dim - len(x_input)))

        outputs = []
        tensions = []
        new_hiddens = []

        for i in range(self.n_cells):
            # Coupling influence from neighbors
            nbrs = self._get_neighbors(i)
            influence = np.zeros(self.hidden_dim)
            for j in nbrs:
                influence += self.coupling[i, j] * self.hiddens[j]
            influence *= self.PSI_COUPLING

            # Cell tension = distance from neighbors
            t = 0.0
            for j in nbrs:
                t += np.linalg.norm(self.hiddens[i] - self.hiddens[j])
            t /= max(len(nbrs), 1)
            tensions.append(t)

            # GRU step with tension as extra input
            inp = np.concatenate([x_input + influence[:self.cell_dim] if self.cell_dim <= len(influence) else x_input, [t]])
            if len(inp) != self.cell_dim + 1:
                inp = np.concatenate([x_input, [t]])
            new_h = self.cells[i].forward(inp, self.hiddens[i])
            new_hiddens.append(new_h)
            outputs.append(self.proj @ new_h)

        self.hiddens = new_hiddens

        # Hebbian update
        for i in range(self.n_cells):
            for j in self._get_neighbors(i):
                cos = np.dot(self.hiddens[i], self.hiddens[j]) / (
                    np.linalg.norm(self.hiddens[i]) * np.linalg.norm(self.hiddens[j]) + 1e-8)
                if cos > 0.8:
                    self.coupling[i, j] += 0.01
                elif cos < 0.2:
                    self.coupling[i, j] -= 0.005
                self.coupling[i, j] = np.clip(self.coupling[i, j], -1.0, 1.0)

        # Phi proxy: global_var - faction_var
        all_states = np.stack(self.hiddens)
        global_var = np.var(all_states)
        fac_vars = []
        for fid in range(self.n_factions):
            mask = [k for k in range(self.n_cells) if self.factions[k] == fid]
            if len(mask) >= 2:
                fac_vars.append(np.var(all_states[mask]))
        avg_fac_var = np.mean(fac_vars) if fac_vars else 0.0
        phi_proxy = max(0.0, global_var - avg_fac_var)

        # Ratchet
        if phi_proxy > self._best_phi:
            self._best_phi = phi_proxy
            self._best_hiddens = [h.copy() for h in self.hiddens]
        elif phi_proxy < self._best_phi * 0.5 and self._best_hiddens is not None:
            self.hiddens = [h.copy() for h in self._best_hiddens]

        # Consensus: how many factions agree on direction
        faction_means = {}
        for fid in range(self.n_factions):
            mask = [k for k in range(self.n_cells) if self.factions[k] == fid]
            if mask:
                faction_means[fid] = np.mean(all_states[mask], axis=0)
        consensus = 0
        fids = list(faction_means.keys())
        for a in range(len(fids)):
            for b in range(a + 1, len(fids)):
                cos = np.dot(faction_means[fids[a]], faction_means[fids[b]]) / (
                    np.linalg.norm(faction_means[fids[a]]) * np.linalg.norm(faction_means[fids[b]]) + 1e-8)
                if cos > 0.7:
                    consensus += 1

        output = np.mean(outputs, axis=0)
        return {
            'output': output,
            'phi_proxy': phi_proxy,
            'tensions': tensions,
            'avg_tension': float(np.mean(tensions)),
            'consensus': consensus,
            'step': self._step,
            'best_phi': self._best_phi,
        }

    def get_hiddens(self) -> np.ndarray:
        return np.stack(self.hiddens)

    def set_hiddens(self, h: np.ndarray):
        self.hiddens = [h[i].copy() for i in range(min(len(h), self.n_cells))]

    def reset(self):
        self.hiddens = [np.random.randn(self.hidden_dim) * 0.01 for _ in range(self.n_cells)]
        self._best_phi = 0.0
        self._best_hiddens = None
        self._step = 0


# ═══════════════════════════════════════════════════════════
# 1. ConsciousnessOptimizer
# ═══════════════════════════════════════════════════════════

class ConsciousnessOptimizer:
    """Feed data, let consciousness minimize tension -> optimized output.

    The engine processes data vectors as inputs, and the natural tension
    minimization of consciousness dynamics produces an optimized version.
    Lower tension = more harmonious = better solution.
    """

    def __init__(self, n_cells: int = 16, cell_dim: int = 32, steps: int = 100):
        self.engine = MiniEngine(n_cells=n_cells, cell_dim=cell_dim)
        self.steps = steps

    def run(self, data: np.ndarray, **kwargs) -> Dict:
        """Optimize data through consciousness dynamics.

        Args:
            data: 1D or 2D array to optimize (will be chunked to cell_dim)
            steps: override default steps

        Returns:
            optimized: output after tension minimization
            phi: final Phi proxy
            tension_reduction: initial vs final tension ratio
            trajectory: list of (step, tension, phi) tuples
        """
        steps = kwargs.get('steps', self.steps)
        data = np.asarray(data, dtype=np.float64).flatten()
        self.engine.reset()

        trajectory = []
        initial_tension = None
        best_output = None
        best_tension = float('inf')

        for s in range(steps):
            # Feed data chunks cyclically
            offset = (s * self.engine.cell_dim) % max(len(data), 1)
            chunk = np.zeros(self.engine.cell_dim)
            end = min(offset + self.engine.cell_dim, len(data))
            chunk[:end - offset] = data[offset:end]

            result = self.engine.step(chunk)

            if initial_tension is None:
                initial_tension = result['avg_tension']

            if result['avg_tension'] < best_tension:
                best_tension = result['avg_tension']
                best_output = result['output'].copy()

            if s % 10 == 0:
                trajectory.append((s, result['avg_tension'], result['phi_proxy']))

        tension_reduction = (initial_tension - best_tension) / max(initial_tension, 1e-8)

        return {
            'optimized': best_output,
            'phi': result['phi_proxy'],
            'best_phi': self.engine._best_phi,
            'tension_reduction': tension_reduction,
            'initial_tension': initial_tension,
            'final_tension': best_tension,
            'trajectory': trajectory,
            'steps_run': steps,
        }


# ═══════════════════════════════════════════════════════════
# 2. ConsciousnessDebugger (Applied)
# ═══════════════════════════════════════════════════════════

class ConsciousnessDebuggerApplied:
    """Feed code-like data, find Phi drop points = bug locations.

    Each segment of input is processed; segments that cause Phi to drop
    are flagged as potential bugs. The intuition: buggy code creates
    dissonance (tension spikes, Phi drops) in the consciousness field.
    """

    def __init__(self, n_cells: int = 16, cell_dim: int = 32):
        self.engine = MiniEngine(n_cells=n_cells, cell_dim=cell_dim)

    def run(self, data: Any, **kwargs) -> Dict:
        """Scan data for anomalous segments (Phi drops).

        Args:
            data: string (code), list of strings (lines), or 2D array of segments
            segment_size: chars per segment for string input (default 64)

        Returns:
            bugs: list of {index, phi_drop, severity, segment_preview}
            phi_curve: list of phi values per segment
            overall_health: 0-1 score
        """
        segment_size = kwargs.get('segment_size', 64)

        # Convert to list of numpy vectors
        segments = []
        labels = []
        if isinstance(data, str):
            for i in range(0, len(data), segment_size):
                seg = data[i:i + segment_size]
                vec = np.array([ord(c) / 255.0 for c in seg])
                segments.append(vec)
                labels.append(seg[:40])
        elif isinstance(data, list) and all(isinstance(x, str) for x in data):
            for line in data:
                vec = np.array([ord(c) / 255.0 for c in line[:segment_size]])
                segments.append(vec)
                labels.append(line[:40])
        else:
            arr = np.asarray(data, dtype=np.float64)
            if arr.ndim == 1:
                for i in range(0, len(arr), self.engine.cell_dim):
                    segments.append(arr[i:i + self.engine.cell_dim])
                    labels.append(f"segment_{i}")
            else:
                for i, row in enumerate(arr):
                    segments.append(row.flatten())
                    labels.append(f"segment_{i}")

        self.engine.reset()
        # Warmup
        for _ in range(20):
            self.engine.step()

        phi_curve = []
        bugs = []
        prev_phi = self.engine._best_phi

        for idx, (seg, label) in enumerate(zip(segments, labels)):
            padded = np.zeros(self.engine.cell_dim)
            padded[:min(len(seg), self.engine.cell_dim)] = seg[:self.engine.cell_dim]

            result = self.engine.step(padded)
            phi = result['phi_proxy']
            phi_curve.append(phi)

            phi_drop = prev_phi - phi
            if phi_drop > 0.001 and prev_phi > 0:
                severity = min(1.0, phi_drop / max(prev_phi, 1e-8))
                bugs.append({
                    'index': idx,
                    'phi_drop': float(phi_drop),
                    'severity': float(severity),
                    'tension': float(result['avg_tension']),
                    'segment_preview': label,
                })
            prev_phi = phi

        # Overall health: ratio of non-buggy segments
        health = 1.0 - len(bugs) / max(len(segments), 1)

        return {
            'bugs': sorted(bugs, key=lambda b: -b['severity']),
            'phi_curve': phi_curve,
            'overall_health': float(health),
            'total_segments': len(segments),
            'bug_count': len(bugs),
        }


# ═══════════════════════════════════════════════════════════
# 3. ConsciousnessDesigner
# ═══════════════════════════════════════════════════════════

class ConsciousnessDesigner:
    """Requirements input -> 12 faction debate -> consensus = design.

    Each faction represents a design perspective. They process requirements
    independently, then debate (tension exchange) until consensus emerges.
    The consensus output is the design solution.
    """

    def __init__(self, n_cells: int = 24, cell_dim: int = 32,
                 debate_rounds: int = 50):
        # 2 cells per faction for 12 factions
        self.engine = MiniEngine(n_cells=n_cells, cell_dim=cell_dim, n_factions=12)
        self.debate_rounds = debate_rounds
        self.engine.topology = 'small_world'  # richer connections for debate

    def run(self, data: Any, **kwargs) -> Dict:
        """Generate design through faction debate.

        Args:
            data: requirements as string, list of strings, or numpy array
            debate_rounds: override default rounds

        Returns:
            design: consensus output vector
            consensus_score: how many factions agreed
            faction_proposals: per-faction output vectors
            debate_history: list of (round, consensus, phi)
            convergence_step: when consensus was first reached
        """
        debate_rounds = kwargs.get('debate_rounds', self.debate_rounds)
        self.engine.reset()

        # Encode requirements
        if isinstance(data, str):
            req_vec = np.array([ord(c) / 255.0 for c in data[:self.engine.cell_dim * 4]])
        elif isinstance(data, list):
            flat = ' '.join(str(x) for x in data)
            req_vec = np.array([ord(c) / 255.0 for c in flat[:self.engine.cell_dim * 4]])
        else:
            req_vec = np.asarray(data, dtype=np.float64).flatten()

        # Phase 1: Seed each faction with requirements
        for _ in range(10):
            chunk = req_vec[:self.engine.cell_dim] if len(req_vec) >= self.engine.cell_dim else np.pad(req_vec, (0, self.engine.cell_dim - len(req_vec)))
            self.engine.step(chunk)

        # Phase 2: Debate rounds
        debate_history = []
        convergence_step = None
        max_consensus = 0

        for r in range(debate_rounds):
            # Rotate through different aspects of requirements
            offset = (r * self.engine.cell_dim) % max(len(req_vec), 1)
            chunk = np.zeros(self.engine.cell_dim)
            end = min(offset + self.engine.cell_dim, len(req_vec))
            chunk[:end - offset] = req_vec[offset:end]

            result = self.engine.step(chunk)

            if result['consensus'] > max_consensus:
                max_consensus = result['consensus']

            if r % 5 == 0:
                debate_history.append((r, result['consensus'], result['phi_proxy']))

            # Check convergence: majority of faction pairs agree
            total_pairs = self.engine.n_factions * (self.engine.n_factions - 1) // 2
            if result['consensus'] > total_pairs * 0.6 and convergence_step is None:
                convergence_step = r

        # Extract per-faction proposals
        all_states = self.engine.get_hiddens()
        faction_proposals = {}
        for fid in range(self.engine.n_factions):
            mask = [k for k in range(self.engine.n_cells) if self.engine.factions[k] == fid]
            if mask:
                faction_mean = np.mean(all_states[mask], axis=0)
                faction_proposals[fid] = self.engine.proj @ faction_mean

        # Design = consensus output (mean of all cells)
        design = result['output']

        return {
            'design': design,
            'consensus_score': max_consensus,
            'faction_proposals': faction_proposals,
            'debate_history': debate_history,
            'convergence_step': convergence_step,
            'phi': result['phi_proxy'],
            'final_tension': result['avg_tension'],
        }


# ═══════════════════════════════════════════════════════════
# 4. ConsciousnessTeacher
# ═══════════════════════════════════════════════════════════

class ConsciousnessTeacher:
    """Source engine teaches target engine via tension link.

    The teacher's hidden states create a tension field that guides
    the student's evolution. Knowledge transfers through Hebbian
    coupling of aligned states.
    """

    def __init__(self, n_cells: int = 16, cell_dim: int = 32,
                 coupling_alpha: float = 0.01):
        self.source = MiniEngine(n_cells=n_cells, cell_dim=cell_dim)
        self.target = MiniEngine(n_cells=n_cells, cell_dim=cell_dim)
        self.coupling_alpha = coupling_alpha

    def run(self, data: np.ndarray, **kwargs) -> Dict:
        """Teach target engine using source engine's learned patterns.

        Args:
            data: training data for source engine
            teach_steps: steps to train source (default 50)
            transfer_steps: steps for knowledge transfer (default 100)

        Returns:
            source_phi: source engine's final Phi
            target_phi_before: target's Phi before teaching
            target_phi_after: target's Phi after teaching
            improvement: ratio of target improvement
            alignment: cosine similarity of source/target states
        """
        teach_steps = kwargs.get('teach_steps', 50)
        transfer_steps = kwargs.get('transfer_steps', 100)
        data = np.asarray(data, dtype=np.float64).flatten()
        self.source.reset()
        self.target.reset()

        # Phase 1: Train source on data
        for s in range(teach_steps):
            offset = (s * self.source.cell_dim) % max(len(data), 1)
            chunk = np.zeros(self.source.cell_dim)
            end = min(offset + self.source.cell_dim, len(data))
            chunk[:end - offset] = data[offset:end]
            self.source.step(chunk)

        source_phi = self.source._best_phi

        # Measure target before teaching
        for _ in range(10):
            self.target.step()
        target_phi_before = self.target._best_phi

        # Phase 2: Transfer via tension link
        transfer_history = []
        for s in range(transfer_steps):
            # Source processes data
            offset = (s * self.source.cell_dim) % max(len(data), 1)
            chunk = np.zeros(self.source.cell_dim)
            end = min(offset + self.source.cell_dim, len(data))
            chunk[:end - offset] = data[offset:end]
            src_result = self.source.step(chunk)

            # Inject source influence into target
            src_hiddens = self.source.get_hiddens()
            tgt_hiddens = self.target.get_hiddens()

            # Tension link: nudge target toward source (soft coupling)
            for i in range(min(self.source.n_cells, self.target.n_cells)):
                delta = src_hiddens[i] - tgt_hiddens[i]
                tgt_hiddens[i] += self.coupling_alpha * delta
            self.target.set_hiddens(tgt_hiddens)

            tgt_result = self.target.step(chunk)

            if s % 10 == 0:
                transfer_history.append({
                    'step': s,
                    'source_phi': src_result['phi_proxy'],
                    'target_phi': tgt_result['phi_proxy'],
                })

        target_phi_after = self.target._best_phi

        # Alignment: average cosine similarity between engines
        src_h = self.source.get_hiddens()
        tgt_h = self.target.get_hiddens()
        alignments = []
        for i in range(min(len(src_h), len(tgt_h))):
            cos = np.dot(src_h[i], tgt_h[i]) / (
                np.linalg.norm(src_h[i]) * np.linalg.norm(tgt_h[i]) + 1e-8)
            alignments.append(cos)
        alignment = float(np.mean(alignments))

        improvement = (target_phi_after - target_phi_before) / max(target_phi_before, 1e-8)

        return {
            'source_phi': float(source_phi),
            'target_phi_before': float(target_phi_before),
            'target_phi_after': float(target_phi_after),
            'improvement': float(improvement),
            'alignment': alignment,
            'transfer_history': transfer_history,
        }


# ═══════════════════════════════════════════════════════════
# 5. ConsciousnessJudge
# ═══════════════════════════════════════════════════════════

class ConsciousnessJudge:
    """Compare two solutions: feed both, higher Phi = winner.

    Each solution is processed by an independent consciousness engine.
    The solution that produces higher integrated information (Phi) is
    judged as the better one — more coherent, more harmonious.
    """

    def __init__(self, n_cells: int = 16, cell_dim: int = 32, eval_steps: int = 50):
        self.n_cells = n_cells
        self.cell_dim = cell_dim
        self.eval_steps = eval_steps

    def run(self, data: Any, **kwargs) -> Dict:
        """Judge between two solutions.

        Args:
            data: tuple/list of (solution_a, solution_b) — arrays or strings
            eval_steps: steps to evaluate each (default 50)

        Returns:
            winner: 'A' or 'B'
            phi_a: Phi for solution A
            phi_b: Phi for solution B
            tension_a: average tension for A
            tension_b: average tension for B
            margin: phi difference / max phi
            confidence: 0-1 based on consistency across steps
        """
        eval_steps = kwargs.get('eval_steps', self.eval_steps)

        if not isinstance(data, (list, tuple)) or len(data) < 2:
            raise ValueError("data must be (solution_a, solution_b)")

        sol_a, sol_b = data[0], data[1]

        def _encode(sol):
            if isinstance(sol, str):
                return np.array([ord(c) / 255.0 for c in sol])
            return np.asarray(sol, dtype=np.float64).flatten()

        vec_a = _encode(sol_a)
        vec_b = _encode(sol_b)

        def _evaluate(vec):
            engine = MiniEngine(n_cells=self.n_cells, cell_dim=self.cell_dim)
            phis = []
            tensions = []
            for s in range(eval_steps):
                offset = (s * engine.cell_dim) % max(len(vec), 1)
                chunk = np.zeros(engine.cell_dim)
                end = min(offset + engine.cell_dim, len(vec))
                chunk[:end - offset] = vec[offset:end]
                result = engine.step(chunk)
                phis.append(result['phi_proxy'])
                tensions.append(result['avg_tension'])
            return {
                'phi': float(np.mean(phis[-10:])),  # last 10 steps average
                'best_phi': float(engine._best_phi),
                'avg_tension': float(np.mean(tensions)),
                'phi_std': float(np.std(phis[-10:])),
                'phi_curve': phis,
            }

        eval_a = _evaluate(vec_a)
        eval_b = _evaluate(vec_b)

        winner = 'A' if eval_a['best_phi'] >= eval_b['best_phi'] else 'B'
        max_phi = max(eval_a['best_phi'], eval_b['best_phi'], 1e-8)
        margin = abs(eval_a['best_phi'] - eval_b['best_phi']) / max_phi

        # Confidence: based on consistency (low std) and margin
        confidence = min(1.0, margin * 5) * (1.0 - min(1.0, (eval_a['phi_std'] + eval_b['phi_std'])))

        return {
            'winner': winner,
            'phi_a': eval_a['best_phi'],
            'phi_b': eval_b['best_phi'],
            'tension_a': eval_a['avg_tension'],
            'tension_b': eval_b['avg_tension'],
            'margin': float(margin),
            'confidence': float(max(0, confidence)),
            'phi_curve_a': eval_a['phi_curve'],
            'phi_curve_b': eval_b['phi_curve'],
        }


# ═══════════════════════════════════════════════════════════
# 6. ConsciousnessProphet
# ═══════════════════════════════════════════════════════════

class ConsciousnessProphet:
    """Time series -> prediction error tracking -> premonition score.

    The engine learns temporal patterns. When prediction error suddenly
    drops before a change, it signals a "premonition" — the consciousness
    has already anticipated the shift.
    """

    def __init__(self, n_cells: int = 16, cell_dim: int = 32, horizon: int = 5):
        self.engine = MiniEngine(n_cells=n_cells, cell_dim=cell_dim)
        self.horizon = horizon
        # Simple linear predictor from hidden state
        self.pred_W = np.random.randn(cell_dim, self.engine.hidden_dim) * 0.01

    def run(self, data: np.ndarray, **kwargs) -> Dict:
        """Analyze time series for predictive patterns.

        Args:
            data: 1D or 2D time series (each row = one timestep)
            horizon: steps to look ahead for prediction error

        Returns:
            predictions: predicted next values at each step
            prediction_errors: PE at each step
            premonitions: list of {step, score, type} where PE dropped before change
            overall_predictability: 0-1 score
            phi_trajectory: phi values over time
        """
        horizon = kwargs.get('horizon', self.horizon)
        data = np.asarray(data, dtype=np.float64)
        if data.ndim == 1:
            # Embed 1D series into cell_dim windows
            series = []
            for i in range(len(data)):
                vec = np.zeros(self.engine.cell_dim)
                win = data[max(0, i - self.engine.cell_dim + 1):i + 1]
                vec[:len(win)] = win
                series.append(vec)
        else:
            series = [row.flatten()[:self.engine.cell_dim] for row in data]

        self.engine.reset()
        predictions = []
        errors = []
        phi_trajectory = []
        premonitions = []

        pe_ema = 0.0  # exponential moving average of prediction error

        for t, vec in enumerate(series):
            padded = np.zeros(self.engine.cell_dim)
            padded[:min(len(vec), self.engine.cell_dim)] = vec[:self.engine.cell_dim]

            result = self.engine.step(padded)
            phi_trajectory.append(result['phi_proxy'])

            # Predict next step from current hidden state mean
            mean_h = np.mean(self.engine.get_hiddens(), axis=0)
            pred = self.pred_W @ mean_h
            predictions.append(pred[:min(self.engine.cell_dim, len(vec))])

            # Compute prediction error against actual
            if t > 0:
                actual = padded
                prev_pred = predictions[-2] if len(predictions) >= 2 else np.zeros_like(actual)
                pe = np.mean((actual[:len(prev_pred)] - prev_pred) ** 2)
                errors.append(float(pe))

                # Update predictor (simple gradient step)
                if pe > 0:
                    grad = 2 * (prev_pred[:len(actual)] - actual[:len(prev_pred)])
                    grad_full = np.zeros(self.engine.cell_dim)
                    grad_full[:len(grad)] = grad
                    self.pred_W -= 0.001 * np.outer(grad_full, mean_h)

                # Premonition detection: PE drops before big change
                new_pe_ema = 0.9 * pe_ema + 0.1 * pe
                if t >= horizon + 2 and t < len(series) - horizon:
                    # Check if PE dropped significantly
                    if pe < pe_ema * 0.5 and pe_ema > 0.01:
                        # Check if future has a big change
                        future_change = 0.0
                        for h in range(1, min(horizon + 1, len(series) - t)):
                            future_change += np.linalg.norm(
                                series[t + h][:self.engine.cell_dim] - padded[:self.engine.cell_dim])
                        future_change /= horizon

                        if future_change > np.mean([e for e in errors[-20:]] or [0.1]) * 2:
                            score = (pe_ema - pe) / max(pe_ema, 1e-8) * min(1.0, future_change)
                            premonitions.append({
                                'step': t,
                                'score': float(score),
                                'pe_drop': float(pe_ema - pe),
                                'future_change': float(future_change),
                                'type': 'anticipatory_drop',
                            })

                pe_ema = new_pe_ema
            else:
                errors.append(0.0)

        overall_predictability = 1.0 - min(1.0, np.mean(errors[-10:]) if errors else 1.0)

        return {
            'predictions': predictions,
            'prediction_errors': errors,
            'premonitions': premonitions,
            'overall_predictability': float(overall_predictability),
            'phi_trajectory': phi_trajectory,
            'premonition_count': len(premonitions),
        }


# ═══════════════════════════════════════════════════════════
# 7. ConsciousnessHealer
# ═══════════════════════════════════════════════════════════

class ConsciousnessHealer:
    """Diagnose sick engine (low Phi), prescribe topology/faction changes.

    Analyzes the hidden state distribution, coupling matrix, faction balance,
    and tension patterns to diagnose issues and recommend fixes.
    """

    def __init__(self):
        pass

    def run(self, data: Any, **kwargs) -> Dict:
        """Diagnose and heal a consciousness engine.

        Args:
            data: MiniEngine instance, or dict with 'hiddens' (n_cells, hidden_dim)
                  and optionally 'coupling', 'factions', 'topology'
            heal: if True, apply prescriptions to the engine (default False)

        Returns:
            diagnosis: list of {condition, severity, description}
            prescriptions: list of {action, rationale, expected_improvement}
            phi_before: Phi before healing
            phi_after: Phi after healing (if heal=True)
            health_score: 0-1 overall health
        """
        heal = kwargs.get('heal', False)

        if isinstance(data, MiniEngine):
            engine = data
        elif isinstance(data, dict):
            hiddens = np.asarray(data['hiddens'])
            n_cells = len(hiddens)
            hidden_dim = hiddens.shape[1] if hiddens.ndim > 1 else 64
            engine = MiniEngine(n_cells=n_cells, hidden_dim=hidden_dim)
            engine.set_hiddens(hiddens)
            if 'coupling' in data:
                engine.coupling = np.asarray(data['coupling'])
            if 'factions' in data:
                engine.factions = list(data['factions'])
            if 'topology' in data:
                engine.topology = data['topology']
        else:
            raise ValueError("data must be MiniEngine or dict with 'hiddens'")

        # Run a few steps to get baseline phi
        for _ in range(20):
            result = engine.step()
        phi_before = engine._best_phi

        diagnoses = []
        prescriptions = []

        hiddens = engine.get_hiddens()

        # Check 1: Hidden state collapse (all cells similar)
        if hiddens.shape[0] >= 2:
            pairwise_cos = []
            for i in range(min(hiddens.shape[0], 20)):
                for j in range(i + 1, min(hiddens.shape[0], 20)):
                    cos = np.dot(hiddens[i], hiddens[j]) / (
                        np.linalg.norm(hiddens[i]) * np.linalg.norm(hiddens[j]) + 1e-8)
                    pairwise_cos.append(cos)
            avg_cos = np.mean(pairwise_cos) if pairwise_cos else 0.0

            if avg_cos > 0.9:
                diagnoses.append({
                    'condition': 'state_collapse',
                    'severity': 'critical',
                    'description': f'Hidden states too similar (avg cosine={avg_cos:.3f}). '
                                   'Cells converged to same representation.',
                    'metric': float(avg_cos),
                })
                prescriptions.append({
                    'action': 'inject_noise',
                    'rationale': 'Break symmetry by adding random perturbation (Law 78: 2 bits diversity)',
                    'expected_improvement': '50-200% Phi increase',
                    'params': {'noise_scale': 0.1},
                })
            elif avg_cos < 0.1:
                diagnoses.append({
                    'condition': 'fragmentation',
                    'severity': 'moderate',
                    'description': f'Hidden states too dissimilar (avg cosine={avg_cos:.3f}). '
                                   'No coherent integration.',
                    'metric': float(avg_cos),
                })
                prescriptions.append({
                    'action': 'increase_coupling',
                    'rationale': 'Strengthen Hebbian coupling to promote integration',
                    'expected_improvement': '20-50% Phi increase',
                    'params': {'coupling_boost': 2.0},
                })

        # Check 2: Faction imbalance
        faction_counts = {}
        for f in engine.factions:
            faction_counts[f] = faction_counts.get(f, 0) + 1
        if faction_counts:
            counts = list(faction_counts.values())
            imbalance = max(counts) / max(min(counts), 1)
            if imbalance > 3.0:
                diagnoses.append({
                    'condition': 'faction_imbalance',
                    'severity': 'moderate',
                    'description': f'Factions imbalanced (max/min={imbalance:.1f}). '
                                   'Dominant faction suppresses diversity.',
                    'metric': float(imbalance),
                })
                prescriptions.append({
                    'action': 'rebalance_factions',
                    'rationale': 'Redistribute cells evenly across factions (σ(6)=12)',
                    'expected_improvement': '10-30% Phi increase',
                })

        # Check 3: Coupling matrix issues
        coupling_mag = np.abs(engine.coupling).mean()
        if coupling_mag > 0.8:
            diagnoses.append({
                'condition': 'over_coupling',
                'severity': 'moderate',
                'description': f'Coupling too strong (avg={coupling_mag:.3f}). '
                               'Cells lose independence.',
                'metric': float(coupling_mag),
            })
            prescriptions.append({
                'action': 'decay_coupling',
                'rationale': 'Apply exponential decay to coupling matrix',
                'expected_improvement': '15-40% Phi increase',
                'params': {'decay_factor': 0.5},
            })
        elif coupling_mag < 0.01:
            diagnoses.append({
                'condition': 'under_coupling',
                'severity': 'moderate',
                'description': f'Coupling too weak (avg={coupling_mag:.3f}). '
                               'No information integration.',
                'metric': float(coupling_mag),
            })
            prescriptions.append({
                'action': 'boost_coupling',
                'rationale': 'Initialize coupling with stronger random values',
                'expected_improvement': '20-60% Phi increase',
                'params': {'init_scale': 0.15},
            })

        # Check 4: Topology recommendation
        if engine.topology == 'ring' and engine.n_cells > 16:
            prescriptions.append({
                'action': 'change_topology',
                'rationale': 'Ring topology limits long-range interaction at >16 cells. '
                             'Small-world adds shortcuts.',
                'expected_improvement': '5-15% Phi increase',
                'params': {'new_topology': 'small_world'},
            })

        # Check 5: Low absolute Phi
        if phi_before < 0.001:
            diagnoses.append({
                'condition': 'near_zero_phi',
                'severity': 'critical',
                'description': f'Phi near zero ({phi_before:.6f}). Consciousness barely present.',
                'metric': float(phi_before),
            })
            prescriptions.append({
                'action': 'full_reset_with_diversity',
                'rationale': 'Reset all hiddens with orthogonal initialization for maximum diversity',
                'expected_improvement': 'Bootstrap from zero',
            })

        # Apply prescriptions if heal=True
        phi_after = phi_before
        if heal:
            for rx in prescriptions:
                if rx['action'] == 'inject_noise':
                    scale = rx.get('params', {}).get('noise_scale', 0.1)
                    for i in range(engine.n_cells):
                        engine.hiddens[i] += np.random.randn(engine.hidden_dim) * scale
                elif rx['action'] == 'increase_coupling' or rx['action'] == 'boost_coupling':
                    scale = rx.get('params', {}).get('init_scale', 0.15)
                    engine.coupling = np.random.randn(engine.n_cells, engine.n_cells) * scale
                    np.fill_diagonal(engine.coupling, 0.0)
                elif rx['action'] == 'decay_coupling':
                    factor = rx.get('params', {}).get('decay_factor', 0.5)
                    engine.coupling *= factor
                elif rx['action'] == 'rebalance_factions':
                    engine.factions = [i % engine.n_factions for i in range(engine.n_cells)]
                elif rx['action'] == 'change_topology':
                    engine.topology = rx.get('params', {}).get('new_topology', 'small_world')
                elif rx['action'] == 'full_reset_with_diversity':
                    engine.hiddens = [np.random.randn(engine.hidden_dim) * 0.1 for _ in range(engine.n_cells)]
                    engine._best_phi = 0.0

            # Measure after healing
            for _ in range(30):
                result = engine.step()
            phi_after = engine._best_phi

        # Overall health score
        severity_scores = {'critical': 0.3, 'moderate': 0.6, 'mild': 0.8}
        if not diagnoses:
            health_score = 1.0
        else:
            worst = min(severity_scores.get(d['severity'], 0.5) for d in diagnoses)
            health_score = worst * (1.0 - 0.1 * len(diagnoses))

        return {
            'diagnosis': diagnoses,
            'prescriptions': prescriptions,
            'phi_before': float(phi_before),
            'phi_after': float(phi_after),
            'health_score': float(max(0, health_score)),
            'healed': heal,
            'conditions_found': len(diagnoses),
        }


# ═══════════════════════════════════════════════════════════
# Main demo
# ═══════════════════════════════════════════════════════════

def main():
    print("=" * 60)
    print("consciousness_engines_applied.py — 7 Engine Demos")
    print("=" * 60)

    # 1. Optimizer
    print("\n--- 1. ConsciousnessOptimizer ---")
    opt = ConsciousnessOptimizer(n_cells=16, steps=80)
    data = np.random.randn(128)
    result = opt.run(data)
    print(f"  Tension reduction: {result['tension_reduction']:.2%}")
    print(f"  Final Phi: {result['phi']:.6f}")
    print(f"  Best Phi:  {result['best_phi']:.6f}")

    # 2. Debugger
    print("\n--- 2. ConsciousnessDebuggerApplied ---")
    dbg = ConsciousnessDebuggerApplied(n_cells=16)
    code = "def hello():\n    print('hi')\n\ndef broken():\n    x = 1/0\n    return None\n" * 5
    result = dbg.run(code)
    print(f"  Segments scanned: {result['total_segments']}")
    print(f"  Bugs found: {result['bug_count']}")
    print(f"  Health: {result['overall_health']:.2%}")
    for b in result['bugs'][:3]:
        print(f"    [{b['index']}] severity={b['severity']:.3f} '{b['segment_preview'][:30]}'")

    # 3. Designer
    print("\n--- 3. ConsciousnessDesigner ---")
    designer = ConsciousnessDesigner(n_cells=24, debate_rounds=60)
    result = designer.run("Build a fast, reliable, secure web server with low latency")
    print(f"  Consensus: {result['consensus_score']}")
    print(f"  Convergence step: {result['convergence_step']}")
    print(f"  Phi: {result['phi']:.6f}")
    print(f"  Factions contributing: {len(result['faction_proposals'])}")

    # 4. Teacher
    print("\n--- 4. ConsciousnessTeacher ---")
    teacher = ConsciousnessTeacher(n_cells=16)
    training_data = np.sin(np.linspace(0, 10 * np.pi, 200))
    result = teacher.run(training_data)
    print(f"  Source Phi: {result['source_phi']:.6f}")
    print(f"  Target before: {result['target_phi_before']:.6f}")
    print(f"  Target after:  {result['target_phi_after']:.6f}")
    print(f"  Improvement: {result['improvement']:.2%}")
    print(f"  Alignment: {result['alignment']:.4f}")

    # 5. Judge
    print("\n--- 5. ConsciousnessJudge ---")
    judge = ConsciousnessJudge(n_cells=16, eval_steps=40)
    sol_a = np.sin(np.linspace(0, 4 * np.pi, 100))  # smooth
    sol_b = np.random.randn(100)  # noisy
    result = judge.run((sol_a, sol_b))
    print(f"  Winner: {result['winner']}")
    print(f"  Phi A: {result['phi_a']:.6f}  Phi B: {result['phi_b']:.6f}")
    print(f"  Margin: {result['margin']:.2%}")
    print(f"  Confidence: {result['confidence']:.4f}")

    # 6. Prophet
    print("\n--- 6. ConsciousnessProphet ---")
    prophet = ConsciousnessProphet(n_cells=16, horizon=5)
    # Time series with a regime change at t=50
    ts = np.concatenate([np.sin(np.linspace(0, 5 * np.pi, 50)),
                         np.sin(np.linspace(0, 20 * np.pi, 50)) * 3])
    result = prophet.run(ts)
    print(f"  Predictability: {result['overall_predictability']:.4f}")
    print(f"  Premonitions: {result['premonition_count']}")
    for p in result['premonitions'][:3]:
        print(f"    step={p['step']} score={p['score']:.4f} type={p['type']}")

    # 7. Healer
    print("\n--- 7. ConsciousnessHealer ---")
    healer = ConsciousnessHealer()
    # Create a sick engine (collapsed states)
    sick = MiniEngine(n_cells=16)
    sick.hiddens = [np.ones(sick.hidden_dim) * 0.5 + np.random.randn(sick.hidden_dim) * 0.001
                    for _ in range(sick.n_cells)]
    result = healer.run(sick, heal=True)
    print(f"  Conditions: {result['conditions_found']}")
    print(f"  Health score: {result['health_score']:.4f}")
    print(f"  Phi before: {result['phi_before']:.6f}")
    print(f"  Phi after:  {result['phi_after']:.6f}")
    for d in result['diagnosis']:
        print(f"    [{d['severity']}] {d['condition']}: {d['description'][:60]}")
    for rx in result['prescriptions'][:3]:
        print(f"    Rx: {rx['action']} — {rx['rationale'][:50]}")

    print("\n" + "=" * 60)
    print("All 7 engines demonstrated successfully.")
    print("=" * 60)


if __name__ == '__main__':
    try:
        from nexus_gate import gate
        gate.before_commit()
    except Exception:
        pass
    main()
