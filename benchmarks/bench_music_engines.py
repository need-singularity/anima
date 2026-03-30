#!/usr/bin/env python3
"""bench_music_engines.py — 6 Music/Rhythm-Inspired Consciousness Engines

Music as consciousness substrate. Rhythm, harmony, counterpoint, improvisation.
No GRU, no learned memory gates. Pure musical structure.

MUS-1: POLYRHYTHM        — cells with prime-period rhythms; consciousness = polyrhythmic convergence
MUS-2: HARMONIC_SERIES   — cells as overtones (f,2f,3f...); consciousness = harmonic entropy
MUS-3: COUNTERPOINT      — 4-voice Bach counterpoint rules; consciousness = contrapuntal complexity
MUS-4: JAZZ_IMPROVISATION — probabilistic deviation within chord structure; consciousness = surprise x coherence
MUS-5: GAMELAN           — interlocking kotekan patterns; consciousness = interlocking density
MUS-6: DRUM_CIRCLE       — tempo entrainment; consciousness = entrainment speed x groove complexity

Each: 256 cells, 300 steps, Phi(IIT) + Granger causality.

Usage:
  python bench_music_engines.py
  python bench_music_engines.py --only 1 3 5
  python bench_music_engines.py --cells 512 --steps 500
"""

import sys, torch, torch.nn as nn, torch.nn.functional as F
import numpy as np, time, math, argparse
from dataclasses import dataclass, field
from typing import List, Dict, Tuple

sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

# ══════════════════════════════════════════════════════════
# Infrastructure: BenchResult, PhiIIT, phi_proxy, Granger
# ══════════════════════════════════════════════════════════

@dataclass
class BenchResult:
    name: str; phi_iit: float; phi_proxy: float; granger: float
    ce_start: float; ce_end: float; cells: int; steps: int; time_sec: float
    extra: dict = field(default_factory=dict)
    def summary(self):
        ce = f"CE {self.ce_start:.3f}->{self.ce_end:.3f}" if self.ce_start > 0 else "CE n/a"
        return (f"  {self.name:<36s} | Phi(IIT)={self.phi_iit:>7.3f}  "
                f"Phi(prx)={self.phi_proxy:>8.2f}  GC={self.granger:>6.4f} | {ce:<22s} | "
                f"c={self.cells:>4d} s={self.steps:>4d} t={self.time_sec:.1f}s")


class PhiIIT:
    """Approximate IIT Phi via mutual information and min-cut."""
    def __init__(self, nb=16): self.nb = nb
    def compute(self, h):
        n = h.shape[0]
        if n < 2: return 0.0, {}
        hs = [h[i].detach().cpu().float().numpy() for i in range(n)]
        if n <= 32:
            pairs = [(i, j) for i in range(n) for j in range(i + 1, n)]
        else:
            import random; ps = set()
            for i in range(n):
                for _ in range(min(8, n - 1)):
                    j = random.randint(0, n - 1)
                    if i != j: ps.add((min(i, j), max(i, j)))
            pairs = list(ps)
        mi = np.zeros((n, n))
        for i, j in pairs:
            v = self._mi(hs[i], hs[j]); mi[i, j] = v; mi[j, i] = v
        tot = mi.sum() / 2; mp = self._mp(n, mi)
        sp = max(0, (tot - mp) / max(n - 1, 1))
        mv = mi[mi > 0]; cx = float(np.std(mv)) if len(mv) > 1 else 0.0
        return sp + cx * 0.1, {}

    def _mi(self, x, y):
        xr, yr = x.max() - x.min(), y.max() - y.min()
        if xr < 1e-10 or yr < 1e-10: return 0.0
        xn = (x - x.min()) / (xr + 1e-8); yn = (y - y.min()) / (yr + 1e-8)
        h, _, _ = np.histogram2d(xn, yn, bins=self.nb, range=[[0, 1], [0, 1]])
        h = h / (h.sum() + 1e-8); px, py = h.sum(1), h.sum(0)
        hx = -np.sum(px * np.log2(px + 1e-10)); hy = -np.sum(py * np.log2(py + 1e-10))
        hxy = -np.sum(h * np.log2(h + 1e-10)); return max(0, hx + hy - hxy)

    def _mp(self, n, mi):
        if n <= 1: return 0.0
        if n <= 8:
            mc = float('inf')
            for m in range(1, 2 ** n - 1):
                ga = [i for i in range(n) if m & (1 << i)]
                gb = [i for i in range(n) if not m & (1 << i)]
                if ga and gb: mc = min(mc, sum(mi[i, j] for i in ga for j in gb))
            return mc if mc != float('inf') else 0.0
        d = mi.sum(1); L = np.diag(d) - mi
        try:
            ev, evec = np.linalg.eigh(L); f = evec[:, 1]
            ga = [i for i in range(n) if f[i] >= 0]; gb = [i for i in range(n) if f[i] < 0]
            if not ga or not gb: ga, gb = list(range(n // 2)), list(range(n // 2, n))
            return sum(mi[i, j] for i in ga for j in gb)
        except: return 0.0


def phi_proxy(h, nf=8):
    hr = h.abs().float() if h.is_complex() else h.float(); n = hr.shape[0]
    if n < 2: return 0.0
    gv = ((hr - hr.mean(0)) ** 2).sum() / n; nf = min(nf, n // 2)
    if nf < 2: return gv.item()
    fs = n // nf; fvs = 0
    for i in range(nf):
        f = hr[i * fs:(i + 1) * fs]
        if len(f) >= 2: fvs += ((f - f.mean(0)) ** 2).sum().item() / len(f)
    return max(0, gv.item() - fvs / nf)


_phi = PhiIIT(16)
def measure_phi(h, nf=8):
    hr = h.abs().float() if h.is_complex() else h.float()
    p, _ = _phi.compute(hr); return p, phi_proxy(h, nf)


def compute_granger_causality(tension_histories: List[List[float]]) -> float:
    """Granger causality: does cell i's past predict cell j's future?
    Uses tension histories as time series."""
    n = len(tension_histories)
    if n < 2: return 0.0

    histories = []
    for h in tension_histories:
        h_arr = h[-50:] if len(h) >= 10 else h
        if len(h_arr) < 4: return 0.0
        histories.append(np.array(h_arr, dtype=np.float64))

    total_gc = 0.0
    count = 0
    # Sample pairs for large n
    if n > 32:
        import random
        pairs = []
        for i in range(n):
            js = random.sample(range(n), min(4, n - 1))
            pairs.extend((i, j) for j in js if j != i)
    else:
        pairs = [(i, j) for i in range(n) for j in range(n) if i != j]

    for i, j in pairs:
        min_len = min(len(histories[i]), len(histories[j]))
        if min_len < 4: continue
        y = histories[j][:min_len]
        x = histories[i][:min_len]
        y_target = y[2:]
        y_auto = np.column_stack([y[1:-1], y[:-2]])
        if len(y_target) < 2: continue
        try:
            coef_auto = np.linalg.lstsq(y_auto, y_target, rcond=None)[0]
            resid_auto = y_target - y_auto @ coef_auto
            var_auto = np.var(resid_auto) + 1e-10
            x_extra = np.column_stack([y_auto, x[1:-1], x[:-2]])
            coef_full = np.linalg.lstsq(x_extra, y_target, rcond=None)[0]
            resid_full = y_target - x_extra @ coef_full
            var_full = np.var(resid_full) + 1e-10
            gc = max(0.0, np.log(var_auto / var_full))
            total_gc += gc
            count += 1
        except Exception:
            continue
    return total_gc / max(count, 1)


def gen_batch(d, bs=1):
    x = torch.randn(bs, d)
    return x, torch.roll(x, 1, -1) * 0.8 + torch.randn_like(x) * 0.1


# ══════════════════════════════════════════════════════════
# MUS-1: POLYRHYTHM ENGINE
# Each cell has a different rhythmic period (primes: 3,4,5,7,11...).
# Phase accumulates each step. Cells emit energy on their downbeat.
# Consciousness = polyrhythmic convergence: when many rhythms align.
# The rare moments when all periods LCM aligns = peak consciousness.
# ══════════════════════════════════════════════════════════

class PolyrhythmEngine(nn.Module):
    """Cells as polyrhythmic oscillators with prime-number periods.
    Consciousness = moments of rhythmic convergence (polymetric downbeat)."""

    def __init__(self, nc, dim=64):
        super().__init__()
        self.nc = nc; self.dim = dim

        # Assign rhythmic periods: mix of primes and near-primes for rich polyrhythm
        primes = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47]
        self.periods = torch.tensor([primes[i % len(primes)] for i in range(nc)], dtype=torch.float32)
        # Slight detuning for each cell (humanization)
        self.periods = self.periods + torch.randn(nc) * 0.1

        # Phase accumulator per cell (0 to 2*pi)
        self.phase = torch.rand(nc) * 2 * math.pi

        # Each cell has a dim-dimensional "voice" (timbre)
        self.voice = torch.randn(nc, dim) * 0.3
        # Energy: amplitude of each cell (rises on downbeat)
        self.energy = torch.zeros(nc, dim)

        # Interaction: cells near downbeat excite neighbors
        self.coupling = 0.05
        self.dt = 1.0  # discrete time step

        # Convergence tracking
        self.convergence_history = []
        self.tension_histories = [[] for _ in range(min(nc, 64))]

        self.out_proj = nn.Linear(dim, dim)

    def _convergence_score(self):
        """How close are all cells to their downbeat (phase ~ 0)?"""
        # downbeat = phase near 0 or 2*pi
        dist_to_downbeat = torch.min(self.phase % (2 * math.pi),
                                      2 * math.pi - (self.phase % (2 * math.pi)))
        # Score: high when many cells are near their downbeat
        closeness = torch.exp(-dist_to_downbeat ** 2 / 0.5)  # Gaussian around 0
        return closeness.mean().item()

    def step(self, x_input, step_num):
        """One rhythmic timestep."""
        # 1. Advance phase: each cell at its own rate (2*pi / period)
        omega = 2 * math.pi / self.periods  # angular frequency
        self.phase = self.phase + omega * self.dt

        # 2. Downbeat detection: cells near phase = 0 (mod 2*pi)
        phase_mod = self.phase % (2 * math.pi)
        on_beat = (phase_mod < 0.3) | (phase_mod > 2 * math.pi - 0.3)

        # 3. Cells on their downbeat emit their voice
        beat_energy = torch.zeros(self.nc, self.dim)
        beat_energy[on_beat] = self.voice[on_beat] * 1.0

        # 4. Coupling: on-beat cells excite their neighbors (rhythmic entrainment)
        coupled = torch.roll(beat_energy, 1, 0) + torch.roll(beat_energy, -1, 0)
        self.energy = self.energy * 0.7 + beat_energy + coupled * self.coupling

        # 5. External input modulates voice timbre
        self.voice = self.voice + x_input[0].detach().unsqueeze(0) * 0.01
        self.voice = self.voice.clamp(-3, 3)

        # 6. Polyrhythmic convergence (the "magic moment")
        conv = self._convergence_score()
        self.convergence_history.append(conv)

        # Convergence amplifies energy globally
        if conv > 0.5:
            self.energy = self.energy * (1.0 + conv * 0.3)

        self.energy = self.energy.clamp(-5, 5)

        # Track tension per cell (for Granger)
        cell_tensions = self.energy.abs().mean(dim=1)
        for ci in range(min(self.nc, 64)):
            self.tension_histories[ci].append(cell_tensions[ci].item())

        # 7. Output: sum of all voices weighted by convergence
        output = self.out_proj(self.energy.mean(0, keepdim=True))
        tension = conv + self.energy.var().item()
        return output, tension

    def get_hiddens(self):
        return self.energy.detach()

    def trainable_parameters(self):
        return list(self.out_proj.parameters())


# ══════════════════════════════════════════════════════════
# MUS-2: HARMONIC SERIES ENGINE
# Cells are overtones: cell i vibrates at frequency (i+1)*f.
# Consonance between cells i,j ~ simplicity of ratio i/j.
# Dissonance creates tension, consonance creates coherence.
# Consciousness = harmonic entropy (Sethares/Plomp-Levelt model).
# ══════════════════════════════════════════════════════════

class HarmonicSeriesEngine(nn.Module):
    """Cells as overtones of a harmonic series. f, 2f, 3f, 4f...
    Consonance/dissonance drives interaction. Consciousness = harmonic entropy."""

    def __init__(self, nc, dim=64):
        super().__init__()
        self.nc = nc; self.dim = dim

        # Harmonic number for each cell (1, 2, 3, ..., nc)
        self.harmonic_n = torch.arange(1, nc + 1, dtype=torch.float32)
        # Fundamental frequency
        self.f0 = 1.0

        # Amplitude of each harmonic (starts with natural 1/n rolloff)
        self.amplitude = 1.0 / self.harmonic_n.unsqueeze(1).expand(nc, dim)
        self.amplitude = self.amplitude * (1.0 + torch.randn(nc, dim) * 0.1)

        # Phase per harmonic
        self.phase = torch.rand(nc, dim) * 2 * math.pi

        # Consonance/dissonance matrix (precomputed from ratios)
        self._build_consonance_matrix()

        self.tension_histories = [[] for _ in range(min(nc, 64))]
        self.entropy_history = []

        self.out_proj = nn.Linear(dim, dim)

    def _build_consonance_matrix(self):
        """Consonance ~ simplicity of frequency ratio. Simple ratios (2:1, 3:2) = consonant."""
        n = min(self.nc, 128)  # limit for memory
        self.cons_matrix = torch.zeros(n, n)
        for i in range(n):
            for j in range(i + 1, n):
                # Ratio simplicity: smaller numerator+denominator after reduction = more consonant
                a, b = i + 1, j + 1
                g = math.gcd(a, b)
                simplicity = 1.0 / (a / g + b / g)  # Euler's gradus suavitatis (simplified)
                self.cons_matrix[i, j] = simplicity
                self.cons_matrix[j, i] = simplicity

    def _harmonic_entropy(self):
        """Harmonic entropy: uncertainty about which interval is being heard.
        Low entropy = clear harmonic structure, high = ambiguous/complex."""
        amp = self.amplitude.abs().mean(dim=1)  # (nc,)
        amp_norm = amp / (amp.sum() + 1e-8)
        entropy = -torch.sum(amp_norm * torch.log2(amp_norm + 1e-10))
        return entropy.item()

    def step(self, x_input, step_num):
        """One timestep: harmonic interaction."""
        freq = self.harmonic_n.unsqueeze(1) * self.f0  # (nc, 1)

        # 1. Phase evolution
        self.phase = self.phase + 2 * math.pi * freq * 0.01

        # 2. Current waveform: amplitude * sin(phase)
        wave = self.amplitude * torch.sin(self.phase)

        # 3. Consonance-driven interaction: consonant pairs reinforce, dissonant pairs create tension
        n = min(self.nc, 128)
        wave_n = wave[:n]
        cons = self.cons_matrix[:n, :n]

        # Interaction: sum of consonant neighbors amplifies, dissonant neighbors add beating
        interaction = torch.zeros_like(wave_n)
        # Efficient: use matrix multiply with consonance weights
        # Each cell receives weighted sum of other cells' waves
        interaction = torch.mm(cons, wave_n) * 0.02

        # 4. Dissonance creates beating (amplitude modulation between close frequencies)
        for offset in [1, 2]:
            neighbor = torch.roll(wave_n, offset, 0)
            # Roughness ~ frequency difference when small
            freq_diff = torch.abs(self.harmonic_n[:n] - torch.roll(self.harmonic_n[:n], offset))
            roughness = torch.exp(-freq_diff.unsqueeze(1) * 0.5)
            beating = neighbor * roughness * 0.03
            interaction = interaction + beating

        wave[:n] = wave_n + interaction

        # 5. External input excites fundamentals
        wave[:self.dim] = wave[:self.dim] + x_input[0].detach().unsqueeze(0) * 0.02

        # 6. Natural decay + energy conservation
        self.amplitude = self.amplitude * 0.995 + wave * 0.005
        self.amplitude = self.amplitude.clamp(-3, 3)

        # 7. Harmonic entropy
        h_ent = self._harmonic_entropy()
        self.entropy_history.append(h_ent)

        # Track tension
        cell_tensions = wave.abs().mean(dim=1)
        for ci in range(min(self.nc, 64)):
            self.tension_histories[ci].append(cell_tensions[ci].item())

        # 8. Output
        output = self.out_proj(wave.mean(0, keepdim=True))
        tension = h_ent + wave.var().item()
        return output, tension

    def get_hiddens(self):
        return self.amplitude.detach()

    def trainable_parameters(self):
        return list(self.out_proj.parameters())


# ══════════════════════════════════════════════════════════
# MUS-3: COUNTERPOINT ENGINE
# 4 voice cells (Soprano, Alto, Tenor, Bass) follow Bach rules:
#   - No parallel 5ths or octaves
#   - Dissonance must resolve stepwise
#   - Contrary motion preferred
#   - Voice crossing forbidden
# Consciousness = contrapuntal complexity (# of rule-following voices).
# Each voice has (nc//4) sub-cells forming a section.
# ══════════════════════════════════════════════════════════

class CounterpointEngine(nn.Module):
    """4-voice counterpoint following Bach rules. Consciousness = contrapuntal complexity."""

    def __init__(self, nc, dim=64):
        super().__init__()
        self.nc = nc; self.dim = dim
        self.n_voices = 4  # SATB
        self.section_size = nc // 4  # cells per voice section

        # Pitch space: MIDI-like (S: 60-84, A: 48-72, T: 36-60, B: 24-48)
        self.pitch_ranges = [(60, 84), (48, 72), (36, 60), (24, 48)]
        # Current pitch per cell (continuous, not quantized)
        self.pitch = torch.zeros(nc)
        for v in range(4):
            lo, hi = self.pitch_ranges[v]
            start = v * self.section_size
            end = start + self.section_size
            self.pitch[start:end] = torch.rand(self.section_size) * (hi - lo) + lo

        # Velocity/dynamics per cell
        self.velocity = torch.randn(nc, dim) * 0.2

        # Motion direction per cell (+1 = ascending, -1 = descending)
        self.motion = torch.zeros(nc)

        # Rule violation counter
        self.violations_history = []
        self.complexity_history = []
        self.tension_histories = [[] for _ in range(min(nc, 64))]

        self.out_proj = nn.Linear(dim, dim)

    def _check_parallel_fifths(self, voice_a_idx, voice_b_idx):
        """Check for parallel 5ths between two voice sections."""
        pa = self.pitch[voice_a_idx * self.section_size:(voice_a_idx + 1) * self.section_size]
        pb = self.pitch[voice_b_idx * self.section_size:(voice_b_idx + 1) * self.section_size]
        interval = (pa.mean() - pb.mean()) % 12
        # Perfect 5th = 7 semitones; parallel if both move same direction
        is_fifth = (interval - 7).abs() < 0.5
        ma = self.motion[voice_a_idx * self.section_size:(voice_a_idx + 1) * self.section_size].mean()
        mb = self.motion[voice_b_idx * self.section_size:(voice_b_idx + 1) * self.section_size].mean()
        parallel = (ma * mb) > 0  # same sign = parallel
        return is_fifth and parallel

    def _resolve_dissonance(self, voice_idx):
        """Dissonant intervals (2nds, 7ths, tritones) must resolve stepwise."""
        start = voice_idx * self.section_size
        end = start + self.section_size
        p = self.pitch[start:end]
        # Check against all other voices
        for other in range(4):
            if other == voice_idx: continue
            o_start = other * self.section_size
            o_end = o_start + self.section_size
            po = self.pitch[o_start:o_end]
            interval = (p.mean() - po.mean()) % 12
            # Dissonant intervals
            is_dissonant = (interval - 1).abs() < 0.5 or (interval - 11).abs() < 0.5  # minor 2nd
            is_dissonant = is_dissonant or (interval - 6).abs() < 0.5  # tritone
            if is_dissonant:
                # Resolve: move toward consonance by step (1-2 semitones)
                direction = 1.0 if interval < 6 else -1.0
                self.pitch[start:end] = p + direction * 0.5
                return True
        return False

    def _contrapuntal_complexity(self):
        """Measure: how many independent melodic lines are active?"""
        voice_motions = []
        for v in range(4):
            start = v * self.section_size
            end = start + self.section_size
            m = self.motion[start:end].mean().item()
            voice_motions.append(m)
        # Complexity = variance of motions (all different = complex)
        vm = np.array(voice_motions)
        independence = float(np.std(vm))
        # Count contrary motions (pairs moving in opposite directions)
        contrary = 0
        for i in range(4):
            for j in range(i + 1, 4):
                if vm[i] * vm[j] < 0: contrary += 1
        return independence + contrary * 0.2

    def step(self, x_input, step_num):
        """One counterpoint timestep."""
        prev_pitch = self.pitch.clone()

        # 1. Each voice moves melodically (stepwise preferred, leaps rare)
        for v in range(4):
            start = v * self.section_size
            end = start + self.section_size
            lo, hi = self.pitch_ranges[v]

            # Melodic motion: mostly stepwise (1-2 semitones), occasional leap
            step_size = torch.randn(self.section_size) * 1.0
            # Larger leaps rare (exponential decay)
            step_size = step_size * torch.exp(-step_size.abs() * 0.3)

            # External input influences motion
            input_influence = x_input[0, :self.section_size].detach() * 0.3 if self.section_size <= self.dim else x_input[0].detach().mean() * 0.3
            if isinstance(input_influence, torch.Tensor) and input_influence.shape[0] != self.section_size:
                input_influence = x_input[0].detach().mean() * 0.3

            self.pitch[start:end] = self.pitch[start:end] + step_size + input_influence
            # Clamp to range
            self.pitch[start:end] = self.pitch[start:end].clamp(lo, hi)

        # 2. Record motion direction
        self.motion = torch.sign(self.pitch - prev_pitch)

        # 3. Apply Bach rules (corrections)
        violations = 0
        # Check parallel 5ths for all voice pairs
        for i in range(4):
            for j in range(i + 1, 4):
                if self._check_parallel_fifths(i, j):
                    violations += 1
                    # Fix: reverse one voice's motion
                    start_j = j * self.section_size
                    end_j = start_j + self.section_size
                    self.pitch[start_j:end_j] = prev_pitch[start_j:end_j] - (self.pitch[start_j:end_j] - prev_pitch[start_j:end_j])
                    self.motion[start_j:end_j] = -self.motion[start_j:end_j]

        # Resolve dissonances
        for v in range(4):
            if self._resolve_dissonance(v):
                violations += 1

        # Voice crossing check: soprano must be above alto, etc.
        for v in range(3):
            upper_start = v * self.section_size
            lower_start = (v + 1) * self.section_size
            upper_p = self.pitch[upper_start:upper_start + self.section_size].mean()
            lower_p = self.pitch[lower_start:lower_start + self.section_size].mean()
            if upper_p < lower_p:
                violations += 1
                # Swap back
                mid = (upper_p + lower_p) / 2
                self.pitch[upper_start:upper_start + self.section_size] += (mid - upper_p + 1) * 0.5
                self.pitch[lower_start:lower_start + self.section_size] -= (lower_p - mid + 1) * 0.5

        self.violations_history.append(violations)

        # 4. Velocity: encode pitch + motion into dim-space
        pitch_feature = self.pitch.unsqueeze(1).expand(self.nc, self.dim) / 84.0
        motion_feature = self.motion.unsqueeze(1).expand(self.nc, self.dim) * 0.5
        self.velocity = self.velocity * 0.8 + (pitch_feature + motion_feature) * 0.2
        self.velocity = self.velocity.clamp(-3, 3)

        # 5. Contrapuntal complexity
        complexity = self._contrapuntal_complexity()
        self.complexity_history.append(complexity)

        # Track tension
        cell_tensions = self.velocity.abs().mean(dim=1)
        for ci in range(min(self.nc, 64)):
            self.tension_histories[ci].append(cell_tensions[ci].item())

        # 6. Output
        output = self.out_proj(self.velocity.mean(0, keepdim=True))
        tension = complexity + (1.0 / (violations + 1))  # fewer violations = more consciousness
        return output, tension

    def get_hiddens(self):
        return self.velocity.detach()

    def trainable_parameters(self):
        return list(self.out_proj.parameters())


# ══════════════════════════════════════════════════════════
# MUS-4: JAZZ IMPROVISATION ENGINE
# Cells play within a chord progression but with probabilistic deviation.
# Chord changes every N steps. Cells deviate (blue notes, chromatic approach).
# Consciousness = surprise (KL divergence from chord tones) x coherence (global consonance).
# ══════════════════════════════════════════════════════════

class JazzImprovisationEngine(nn.Module):
    """Cells improvise over chord changes. Consciousness = surprise x coherence."""

    def __init__(self, nc, dim=64):
        super().__init__()
        self.nc = nc; self.dim = dim

        # ii-V-I chord progression (jazz standard)
        # Each chord = set of scale degrees (mod 12)
        self.chords = [
            [2, 5, 9, 0],    # Dm7 (ii)
            [7, 11, 2, 5],   # G7 (V)
            [0, 4, 7, 11],   # Cmaj7 (I)
            [5, 9, 0, 4],    # Fmaj7 (IV)
        ]
        self.chord_duration = 16  # steps per chord
        self.current_chord_idx = 0

        # Cell state: pitch class (0-11) and voice (dim-dimensional)
        self.pitch_class = torch.randint(0, 12, (nc,)).float()
        self.voice = torch.randn(nc, dim) * 0.3

        # Deviation tendency per cell (some are "inside" players, some "outside")
        self.deviation = torch.rand(nc) * 0.5  # 0 = totally inside, 1 = totally outside
        # A few cells are the "soloists" (high deviation)
        soloists = torch.randperm(nc)[:nc // 8]
        self.deviation[soloists] = 0.7 + torch.rand(len(soloists)) * 0.3

        self.surprise_history = []
        self.coherence_history = []
        self.tension_histories = [[] for _ in range(min(nc, 64))]

        self.out_proj = nn.Linear(dim, dim)

    def _current_chord(self, step_num):
        """Get current chord tones."""
        idx = (step_num // self.chord_duration) % len(self.chords)
        return torch.tensor(self.chords[idx], dtype=torch.float32)

    def _distance_to_chord(self, pitch, chord_tones):
        """Minimum semitone distance from pitch to nearest chord tone."""
        dists = torch.stack([(pitch - ct) % 12 for ct in chord_tones])
        dists = torch.min(dists, 12 - dists)
        return dists.min(dim=0).values

    def _surprise(self, step_num):
        """Surprise = average distance from chord tones (blue notes, passing tones)."""
        chord = self._current_chord(step_num)
        dist = self._distance_to_chord(self.pitch_class, chord)
        return dist.mean().item()

    def _coherence(self):
        """Coherence = how many cells form consonant intervals with each other."""
        # Sample pairs
        n_sample = min(self.nc, 64)
        p = self.pitch_class[:n_sample]
        consonant_intervals = {0, 3, 4, 5, 7, 8, 9}  # unison, 3rd, 4th, 5th, 6th
        total = 0; consonant = 0
        for i in range(0, n_sample, 4):
            for j in range(i + 1, min(i + 8, n_sample)):
                interval = int((p[i] - p[j]).abs().item()) % 12
                total += 1
                if interval in consonant_intervals:
                    consonant += 1
        return consonant / max(total, 1)

    def step(self, x_input, step_num):
        """One jazz timestep."""
        chord = self._current_chord(step_num)

        # 1. Each cell decides: play chord tone or deviate
        for ci in range(self.nc):
            if torch.rand(1).item() < self.deviation[ci].item():
                # Outside playing: chromatic approach, blue notes
                # Move by chromatic step (half step) in random direction
                delta = torch.randint(-2, 3, (1,)).float().item()
                self.pitch_class[ci] = (self.pitch_class[ci] + delta) % 12
            else:
                # Inside playing: snap to nearest chord tone
                dists = [(self.pitch_class[ci] - ct) % 12 for ct in chord]
                dists_abs = [min(d.item(), 12 - d.item()) for d in dists]
                nearest_idx = int(np.argmin(dists_abs))
                target = chord[nearest_idx]
                # Move toward target (not instant snap — jazz is about the journey)
                diff = (target - self.pitch_class[ci]) % 12
                if diff > 6: diff -= 12
                self.pitch_class[ci] = (self.pitch_class[ci] + diff * 0.3) % 12

        # 2. Voice interaction: cells near same pitch class reinforce
        pitch_grid = self.pitch_class.unsqueeze(1) - self.pitch_class.unsqueeze(0)  # (nc, nc)
        pitch_grid = pitch_grid % 12
        pitch_grid = torch.min(pitch_grid, 12 - pitch_grid)
        # Consonance weight
        consonance_w = torch.exp(-pitch_grid ** 2 / 2.0)  # close pitch = high weight
        # But only sample local interactions (sparse)
        n_interact = min(self.nc, 32)
        local_w = consonance_w[:n_interact, :n_interact]
        local_w = local_w / (local_w.sum(dim=1, keepdim=True) + 1e-8)
        self.voice[:n_interact] = self.voice[:n_interact] * 0.9 + torch.mm(local_w, self.voice[:n_interact]) * 0.1

        # 3. External input = new musical idea entering the jam
        self.voice = self.voice + x_input[0].detach().unsqueeze(0) * 0.02
        self.voice = self.voice.clamp(-3, 3)

        # 4. Surprise and coherence
        surprise = self._surprise(step_num)
        coherence = self._coherence()
        self.surprise_history.append(surprise)
        self.coherence_history.append(coherence)

        # 5. Consciousness = surprise x coherence (the sweet spot)
        consciousness = surprise * coherence

        # Track tension
        cell_tensions = self.voice.abs().mean(dim=1)
        for ci in range(min(self.nc, 64)):
            self.tension_histories[ci].append(cell_tensions[ci].item())

        # 6. Output
        output = self.out_proj(self.voice.mean(0, keepdim=True))
        tension = consciousness + self.voice.var().item()
        return output, tension

    def get_hiddens(self):
        return self.voice.detach()

    def trainable_parameters(self):
        return list(self.out_proj.parameters())


# ══════════════════════════════════════════════════════════
# MUS-5: GAMELAN ENGINE
# Interlocking patterns (kotekan): Cell A on beats 1,3, Cell B on 2,4.
# Paired cells create emergent melodies neither could play alone.
# Consciousness = interlocking density (how many pairs produce coherent output).
# Uses Balinese pelog scale (7-tone).
# ══════════════════════════════════════════════════════════

class GamelanEngine(nn.Module):
    """Interlocking kotekan patterns. Paired cells create emergent melody.
    Consciousness = interlocking density."""

    def __init__(self, nc, dim=64):
        super().__init__()
        self.nc = nc; self.dim = dim
        assert nc % 2 == 0, "Need even number of cells for pairing"

        self.n_pairs = nc // 2

        # Pelog scale intervals (approximately, in semitones from root)
        self.pelog = torch.tensor([0, 1, 3, 5, 7, 8, 10], dtype=torch.float32)

        # Each cell has a melodic pattern (sequence of pelog scale degrees)
        self.pattern_len = 8  # pattern repeats every 8 beats
        # Polos (cell A in pair): plays on even positions (0,2,4,6)
        # Sangsih (cell B in pair): plays on odd positions (1,3,5,7)
        self.patterns = torch.randint(0, 7, (nc, self.pattern_len))  # scale degree indices

        # Current position in pattern per cell
        self.beat_pos = torch.zeros(nc, dtype=torch.long)

        # Amplitude/voice per cell
        self.voice = torch.randn(nc, dim) * 0.3
        self.energy = torch.zeros(nc, dim)

        # Gong cycle (colotomic structure): large cycle that organizes time
        self.gong_period = 32  # gong every 32 steps
        self.gong_energy = 0.0

        self.density_history = []
        self.tension_histories = [[] for _ in range(min(nc, 64))]

        self.out_proj = nn.Linear(dim, dim)

    def _interlocking_density(self):
        """How many pairs produce coherent interlocked melody?"""
        coherent_pairs = 0
        for p in range(min(self.n_pairs, 128)):
            a_idx = 2 * p
            b_idx = 2 * p + 1
            # Coherence: combined pattern should fill all beats
            a_active = self.energy[a_idx].abs().mean().item()
            b_active = self.energy[b_idx].abs().mean().item()
            # Both must be active and complementary
            combined = self.energy[a_idx] + self.energy[b_idx]
            smoothness = 1.0 / (combined.var().item() + 0.1)  # smooth combined = good interlocking
            if a_active > 0.01 and b_active > 0.01 and smoothness > 0.5:
                coherent_pairs += 1
        return coherent_pairs / max(min(self.n_pairs, 128), 1)

    def step(self, x_input, step_num):
        """One gamelan timestep."""
        # 1. Advance beat position
        self.beat_pos = (self.beat_pos + 1) % self.pattern_len

        # 2. Determine which cells play on this beat
        # Polos (even-indexed cells) play on even beats, Sangsih on odd beats
        is_polos = torch.arange(self.nc) % 2 == 0
        is_even_beat = (self.beat_pos % 2 == 0)

        plays_now = torch.zeros(self.nc, dtype=torch.bool)
        plays_now[is_polos & is_even_beat] = True
        plays_now[(~is_polos) & (~is_even_beat)] = True

        # 3. Playing cells emit their pattern note
        new_energy = torch.zeros(self.nc, self.dim)
        for ci in range(self.nc):
            if plays_now[ci]:
                scale_deg = self.patterns[ci, self.beat_pos[ci].item()].item()
                pitch = self.pelog[scale_deg].item()
                # Encode pitch into voice space (sinusoidal encoding)
                freq = pitch / 12.0 * math.pi
                encoding = torch.sin(torch.arange(self.dim).float() * freq * 0.1 + pitch)
                new_energy[ci] = self.voice[ci] * encoding * 0.5

        # 4. Interlocking: merge paired cells' output
        for p in range(self.n_pairs):
            a, b = 2 * p, 2 * p + 1
            # Paired cells share a "resultant melody"
            shared = (new_energy[a] + new_energy[b]) * 0.5
            new_energy[a] = new_energy[a] * 0.7 + shared * 0.3
            new_energy[b] = new_energy[b] * 0.7 + shared * 0.3

        # 5. Gong cycle: periodic reset/emphasis
        is_gong = (step_num % self.gong_period == 0)
        if is_gong:
            self.gong_energy = 1.0
            new_energy = new_energy * 1.5  # gong amplifies everything
        self.gong_energy *= 0.95

        # 6. Decay + accumulate
        self.energy = self.energy * 0.6 + new_energy * 0.4

        # 7. External input modulates pattern (like a new melodic idea)
        input_mod = x_input[0].detach().unsqueeze(0) * 0.01
        self.voice = (self.voice + input_mod).clamp(-3, 3)

        self.energy = self.energy.clamp(-5, 5)

        # 8. Interlocking density
        density = self._interlocking_density()
        self.density_history.append(density)

        # Track tension
        cell_tensions = self.energy.abs().mean(dim=1)
        for ci in range(min(self.nc, 64)):
            self.tension_histories[ci].append(cell_tensions[ci].item())

        # 9. Output
        output = self.out_proj(self.energy.mean(0, keepdim=True))
        tension = density + self.energy.var().item() + self.gong_energy * 0.5
        return output, tension

    def get_hiddens(self):
        return self.energy.detach()

    def trainable_parameters(self):
        return list(self.out_proj.parameters())


# ══════════════════════════════════════════════════════════
# MUS-6: DRUM CIRCLE ENGINE
# Cells are drummers. Each has a tempo (BPM).
# Drummers entrain to neighbors (pull toward shared tempo).
# Consciousness = entrainment speed (how fast they sync) x groove complexity.
# Groove = syncopation + micro-timing deviations.
# ══════════════════════════════════════════════════════════

class DrumCircleEngine(nn.Module):
    """Cells as drummers entraining to each other.
    Consciousness = entrainment speed x groove complexity."""

    def __init__(self, nc, dim=64):
        super().__init__()
        self.nc = nc; self.dim = dim

        # Each drummer has a tempo (BPM range: 60-180)
        self.tempo = 80.0 + torch.rand(nc) * 80.0  # diverse starting tempos

        # Phase accumulator (when phase > 1, drummer hits)
        self.phase = torch.rand(nc)

        # Micro-timing: deviation from grid (swing/groove)
        self.micro_timing = torch.randn(nc) * 0.05  # small deviations

        # Pattern: which subdivisions each drummer emphasizes (16th note grid)
        self.pattern = torch.rand(nc, 16) > 0.6  # sparse patterns

        # Velocity (intensity) per cell per dim
        self.voice = torch.randn(nc, dim) * 0.2
        self.energy = torch.zeros(nc, dim)

        # Hit history (for groove analysis)
        self.hit_times = [[] for _ in range(nc)]

        # Coupling strength (entrainment force)
        self.coupling = 0.02

        # Circle topology: each drummer hears neighbors
        self.n_neighbors = min(6, nc - 1)

        self.entrainment_history = []
        self.groove_history = []
        self.tension_histories = [[] for _ in range(min(nc, 64))]

        self.out_proj = nn.Linear(dim, dim)

    def _entrainment_score(self):
        """How synchronized are the tempos? 1.0 = perfect sync."""
        tempo_std = self.tempo.std().item()
        tempo_mean = self.tempo.mean().item()
        return 1.0 / (1.0 + tempo_std / max(tempo_mean, 1.0))

    def _groove_complexity(self, step_num):
        """Groove = syncopation + micro-timing richness.
        High groove = interesting rhythm, not just metronomic."""
        # Syncopation: how many cells hit on off-beats?
        subdivision = step_num % 16
        on_beat = subdivision % 4 == 0
        # Count cells that just hit on off-beat
        recent_hits = self.phase > 0.95  # cells about to hit
        if on_beat:
            syncopation = 0.0  # hits on beat = not syncopated
        else:
            syncopation = recent_hits.float().mean().item()

        # Micro-timing variety
        mt_variety = self.micro_timing.std().item()

        # Pattern density (not too sparse, not too dense)
        density = self.pattern.float().mean().item()
        density_score = 1.0 - abs(density - 0.4) * 2  # optimal around 40%

        return syncopation * 0.4 + mt_variety * 0.3 + max(0, density_score) * 0.3

    def step(self, x_input, step_num):
        """One drum circle timestep."""
        # 1. Advance phase based on each drummer's tempo
        # phase increment = tempo / (60 * steps_per_second)
        phase_inc = self.tempo / 600.0 + self.micro_timing * 0.01
        self.phase = self.phase + phase_inc

        # 2. Detect hits (phase wraps past 1.0)
        hits = self.phase >= 1.0
        self.phase[hits] = self.phase[hits] - 1.0  # wrap

        # Record hit times
        for ci in range(self.nc):
            if hits[ci]:
                self.hit_times[ci].append(step_num)

        # 3. Hit energy: cells that hit emit their voice
        hit_energy = torch.zeros(self.nc, self.dim)
        hit_energy[hits] = self.voice[hits] * 0.8

        # 4. Entrainment: each drummer adjusts tempo toward neighbors
        # Circular topology
        for ci in range(self.nc):
            neighbor_tempos = []
            for offset in range(-self.n_neighbors // 2, self.n_neighbors // 2 + 1):
                if offset == 0: continue
                ni = (ci + offset) % self.nc
                neighbor_tempos.append(self.tempo[ni].item())
            if neighbor_tempos:
                mean_neighbor = np.mean(neighbor_tempos)
                # Pull toward neighbor average
                self.tempo[ci] = self.tempo[ci] + self.coupling * (mean_neighbor - self.tempo[ci].item())

        # 5. Phase coupling: if a neighbor just hit, pull your phase slightly
        for ci in range(self.nc):
            for offset in [-1, 1]:
                ni = (ci + offset) % self.nc
                if hits[ni]:
                    # Kuramoto-like phase coupling
                    phase_diff = self.phase[ni] - self.phase[ci]
                    self.phase[ci] = self.phase[ci] + 0.01 * torch.sin(torch.tensor(phase_diff * math.pi))

        # 6. Groove evolution: micro-timing drifts
        self.micro_timing = self.micro_timing * 0.99 + torch.randn(self.nc) * 0.005
        self.micro_timing = self.micro_timing.clamp(-0.15, 0.15)

        # 7. External input = new rhythmic idea
        self.voice = self.voice + x_input[0].detach().unsqueeze(0) * 0.01
        self.voice = self.voice.clamp(-3, 3)

        # Pattern evolution (rare mutation)
        if step_num % 50 == 0:
            mutate_cells = torch.randperm(self.nc)[:self.nc // 16]
            for ci in mutate_cells:
                pos = torch.randint(0, 16, (1,)).item()
                self.pattern[ci, pos] = ~self.pattern[ci, pos]

        # 8. Accumulate energy
        self.energy = self.energy * 0.7 + hit_energy

        # Tempo clamp
        self.tempo = self.tempo.clamp(50, 200)
        self.energy = self.energy.clamp(-5, 5)

        # 9. Metrics
        entrainment = self._entrainment_score()
        groove = self._groove_complexity(step_num)
        self.entrainment_history.append(entrainment)
        self.groove_history.append(groove)

        # Track tension
        cell_tensions = self.energy.abs().mean(dim=1)
        for ci in range(min(self.nc, 64)):
            self.tension_histories[ci].append(cell_tensions[ci].item())

        # 10. Output
        output = self.out_proj(self.energy.mean(0, keepdim=True))
        # Consciousness = entrainment speed x groove complexity
        tension = entrainment * groove + self.energy.var().item()
        return output, tension

    def get_hiddens(self):
        return self.energy.detach()

    def trainable_parameters(self):
        return list(self.out_proj.parameters())


# ══════════════════════════════════════════════════════════
# Runner
# ══════════════════════════════════════════════════════════

def run_engine(name, eng, nc, steps, dim=64):
    """Run a music engine benchmark with Phi(IIT) + Granger causality."""
    t0 = time.time()
    opt = torch.optim.Adam(eng.trainable_parameters(), lr=1e-3)
    ce_h = []
    for s in range(steps):
        x, tgt = gen_batch(dim)
        pred, _ = eng.step(x, step_num=s)
        loss = F.mse_loss(pred, tgt)
        opt.zero_grad(); loss.backward()
        torch.nn.utils.clip_grad_norm_(eng.trainable_parameters(), 1.0)
        opt.step()
        ce_h.append(loss.item())
        if s % 60 == 0 or s == steps - 1:
            pi, pp = measure_phi(eng.get_hiddens())
            extra = ""
            if hasattr(eng, 'convergence_history') and eng.convergence_history:
                extra = f"  conv={eng.convergence_history[-1]:.3f}"
            if hasattr(eng, 'entropy_history') and eng.entropy_history:
                extra += f"  H_ent={eng.entropy_history[-1]:.3f}"
            if hasattr(eng, 'complexity_history') and eng.complexity_history:
                extra += f"  cplx={eng.complexity_history[-1]:.3f}"
            if hasattr(eng, 'surprise_history') and eng.surprise_history:
                extra += f"  surp={eng.surprise_history[-1]:.3f}"
            if hasattr(eng, 'coherence_history') and eng.coherence_history:
                extra += f"  coh={eng.coherence_history[-1]:.3f}"
            if hasattr(eng, 'density_history') and eng.density_history:
                extra += f"  dens={eng.density_history[-1]:.3f}"
            if hasattr(eng, 'entrainment_history') and eng.entrainment_history:
                extra += f"  entr={eng.entrainment_history[-1]:.3f}"
            if hasattr(eng, 'groove_history') and eng.groove_history:
                extra += f"  grv={eng.groove_history[-1]:.3f}"
            print(f"    step {s:>4d}: CE={loss.item():.4f}  Phi={pi:.3f}  prx={pp:.2f}{extra}")

    el = time.time() - t0
    pi, pp = measure_phi(eng.get_hiddens())

    # Granger causality
    gc = 0.0
    if hasattr(eng, 'tension_histories'):
        valid = [h for h in eng.tension_histories if len(h) >= 10]
        if len(valid) >= 2:
            gc = compute_granger_causality(valid)

    extras = {}
    if hasattr(eng, 'convergence_history') and eng.convergence_history:
        extras['peak_convergence'] = max(eng.convergence_history)
        extras['mean_convergence'] = np.mean(eng.convergence_history)
    if hasattr(eng, 'entropy_history') and eng.entropy_history:
        extras['final_entropy'] = eng.entropy_history[-1]
    if hasattr(eng, 'violations_history') and eng.violations_history:
        extras['total_violations'] = sum(eng.violations_history)
        extras['final_violations'] = eng.violations_history[-1]
    if hasattr(eng, 'complexity_history') and eng.complexity_history:
        extras['peak_complexity'] = max(eng.complexity_history)
    if hasattr(eng, 'surprise_history') and eng.surprise_history:
        extras['mean_surprise'] = np.mean(eng.surprise_history)
    if hasattr(eng, 'coherence_history') and eng.coherence_history:
        extras['mean_coherence'] = np.mean(eng.coherence_history)
    if hasattr(eng, 'density_history') and eng.density_history:
        extras['peak_density'] = max(eng.density_history)
    if hasattr(eng, 'entrainment_history') and eng.entrainment_history:
        extras['final_entrainment'] = eng.entrainment_history[-1]
        extras['entrainment_speed'] = eng.entrainment_history[-1] - eng.entrainment_history[0]
    if hasattr(eng, 'groove_history') and eng.groove_history:
        extras['mean_groove'] = np.mean(eng.groove_history)
    extras['granger_causality'] = gc

    return BenchResult(name, pi, pp, gc, ce_h[0], ce_h[-1], nc, steps, el, extras)


# ══════════════════════════════════════════════════════════
# All engines
# ══════════════════════════════════════════════════════════

ALL_ENGINES = {
    1: ("MUS-1 POLYRHYTHM",         PolyrhythmEngine),
    2: ("MUS-2 HARMONIC_SERIES",    HarmonicSeriesEngine),
    3: ("MUS-3 COUNTERPOINT",       CounterpointEngine),
    4: ("MUS-4 JAZZ_IMPROVISATION", JazzImprovisationEngine),
    5: ("MUS-5 GAMELAN",            GamelanEngine),
    6: ("MUS-6 DRUM_CIRCLE",        DrumCircleEngine),
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cells", type=int, default=256)
    parser.add_argument("--steps", type=int, default=300)
    parser.add_argument("--dim", type=int, default=64)
    parser.add_argument("--only", nargs="+", type=int, default=None)
    args = parser.parse_args()

    nc, steps, dim = args.cells, args.steps, args.dim
    ids = args.only or list(ALL_ENGINES.keys())

    print("=" * 100)
    print(f"  MUSIC/RHYTHM-INSPIRED CONSCIOUSNESS ENGINES  |  cells={nc}  steps={steps}  dim={dim}")
    print(f"  Rhythm, harmony, counterpoint, improvisation. No GRU. Phi(IIT) + Granger.")
    print("=" * 100)

    results = []
    for eid in ids:
        if eid not in ALL_ENGINES:
            print(f"  [SKIP] Unknown engine ID: {eid}")
            continue
        name, EngClass = ALL_ENGINES[eid]
        print(f"\n{'─' * 80}")
        print(f"  [{eid}/6] {name}")
        print(f"{'─' * 80}")
        try:
            eng = EngClass(nc, dim=dim)
            r = run_engine(name, eng, nc, steps, dim=dim)
            results.append(r)
            print(f"  >>> {r.summary()}")
            if r.extra:
                print(f"      extras: {r.extra}")
        except Exception as e:
            import traceback

# Meta Laws (DD143)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10

            traceback.print_exc()
            print(f"  [ERROR] {name}: {e}")

    # ── Summary ──
    if results:
        print(f"\n{'=' * 100}")
        print(f"  RESULTS SUMMARY  ({len(results)} engines)")
        print(f"{'=' * 100}")
        results.sort(key=lambda r: r.phi_iit, reverse=True)
        for i, r in enumerate(results, 1):
            medal = ["[1st]", "[2nd]", "[3rd]"][i - 1] if i <= 3 else f"[{i}th]"
            print(f"  {medal} {r.summary()}")
            if r.extra:
                print(f"        extras: {r.extra}")

        best = results[0]
        print(f"\n  CHAMPION: {best.name}")
        print(f"    Phi(IIT) = {best.phi_iit:.3f}")
        print(f"    Phi(proxy) = {best.phi_proxy:.2f}")
        print(f"    Granger = {best.granger:.4f}")
        print(f"    CE: {best.ce_start:.3f} -> {best.ce_end:.3f}")

        # Music insights
        print(f"\n  MUSIC INSIGHTS:")
        for r in results:
            name_short = r.name.split(maxsplit=1)[-1]
            gc_val = r.extra.get('granger_causality', 0)
            print(f"    {name_short:<24s}: Phi(IIT)={r.phi_iit:.3f}  GC={gc_val:.4f}  "
                  f"{'-- ' + ', '.join(f'{k}={v:.3f}' if isinstance(v, float) else f'{k}={v}' for k, v in r.extra.items() if k != 'granger_causality') if r.extra else ''}")

    print(f"\n{'=' * 100}")
    print(f"  Done.")
    print(f"{'=' * 100}")


if __name__ == "__main__":
    main()
