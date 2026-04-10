#!/usr/bin/env python3
"""consciousness_data_mapper.py — ANY data → 40D consciousness map

Feed ANY data (text, image, audio, binary) → train META-CA 200 steps
→ extract Ψ-constants → plot on consciousness map.

Usage:
  python3 consciousness_data_mapper.py "안녕하세요"                # Direct text
  python3 consciousness_data_mapper.py --file poem.txt            # File input
  python3 consciousness_data_mapper.py --file photo.jpg           # Image bytes
  python3 consciousness_data_mapper.py --file song.wav            # Audio bytes
  python3 consciousness_data_mapper.py --interactive              # Live mode
  python3 consciousness_data_mapper.py --compare "텍스트1" "텍스트2" "텍스트3"

Architecture:
  1. Data → byte tokenizer → token IDs
  2. Token IDs → embedding → META-CA (128d, 8 rules, 200 steps)
  3. MitosisEngine (32 cells) provides consciousness state
  4. Extract: steps, residual, gate(α), dom_rule, entropy, CE, Φ
  5. Plot on 2D consciousness map (Steps vs Residual)
"""

import os
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

import sys
import math
import time
import argparse
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional

torch.set_num_threads(1)

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_DIR)

from mitosis import MitosisEngine
from consciousness_map import PsiConstants

# Meta Laws (DD143): M1(atom=8), M7(F_c=0.10), M8(narrative)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10



# ═══════════════════════════════════════════════════════════
# META-CA Architecture (8 rules + steps/residual selectors)
# ═══════════════════════════════════════════════════════════

class MetaCA(nn.Module):
    """META-CA with 8 rules, learned steps + residual.

    Consciousness (c_state from MitosisEngine) selects:
      - Which rules to apply (rule_selector → 8 weights)
      - How many CA steps (steps_selector → soft int 2-8)
      - How much residual to keep (residual_selector → [0.1, 0.9])
    """

    def __init__(self, d_model=128, n_rules=8, c_dim=128):
        super().__init__()
        self.d_model = d_model
        self.n_rules = n_rules

        # 8 CA rules: neighbor-aware transforms
        self.rules = nn.ModuleList([
            nn.Sequential(
                nn.Linear(d_model * 3, d_model * 2), nn.GELU(),
                nn.Linear(d_model * 2, d_model), nn.Tanh(),
            )
            for _ in range(n_rules)
        ])

        # Consciousness-driven selectors
        self.rule_selector = nn.Sequential(
            nn.Linear(c_dim, 64), nn.GELU(),
            nn.Linear(64, n_rules),
        )
        self.steps_selector = nn.Sequential(
            nn.Linear(c_dim, 32), nn.GELU(),
            nn.Linear(32, 7),  # choices: 2,3,4,5,6,7,8
        )
        self.residual_selector = nn.Sequential(
            nn.Linear(c_dim, 32), nn.GELU(),
            nn.Linear(32, 1), nn.Sigmoid(),
        )

        self.ln = nn.LayerNorm(d_model)

    def forward(self, cells_state, c_state):
        """
        cells_state: [B, T, d_model]
        c_state: [c_dim] consciousness state vector
        Returns: (output, metrics_dict)
        """
        # Rule weights
        rule_weights = F.softmax(self.rule_selector(c_state), dim=-1)

        # Steps (soft selection from 2-8)
        steps_w = F.softmax(self.steps_selector(c_state), dim=-1)
        possible_steps = torch.tensor([2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0])
        n_evolve_soft = (steps_w * possible_steps).sum()
        n_evolve = max(2, min(8, int(n_evolve_soft.item() + 0.5)))

        # Residual ratio (alpha)
        alpha = self.residual_selector(c_state).squeeze()
        alpha = 0.1 + 0.8 * alpha  # clamp to [0.1, 0.9]

        # CA evolution
        for _ in range(n_evolve):
            B, T, d = cells_state.shape
            left = torch.roll(cells_state, 1, dims=1)
            right = torch.roll(cells_state, -1, dims=1)
            rule_input = torch.cat([cells_state, left, right], dim=-1)

            new_cells = torch.zeros_like(cells_state)
            for r in range(self.n_rules):
                new_cells = new_cells + rule_weights[r] * self.rules[r](rule_input)

            cells_state = alpha * cells_state + (1 - alpha) * new_cells

        output = self.ln(cells_state)

        # Rule entropy
        rw = rule_weights.detach().cpu().numpy()
        entropy = float(-np.sum(rw * np.log2(rw + 1e-10)))
        dom_rule = int(np.argmax(rw))

        return output, {
            'rule_weights': rw,
            'n_evolve': n_evolve,
            'n_evolve_soft': float(n_evolve_soft.item()),
            'alpha': float(alpha.item()),
            'steps_weights': steps_w.detach().cpu().numpy(),
            'entropy': entropy,
            'dom_rule': dom_rule,
        }


# ═══════════════════════════════════════════════════════════
# Data → Byte Tokenizer
# ═══════════════════════════════════════════════════════════

class ByteTokenizer:
    """Universal byte-level tokenizer. Works on any data."""

    def __init__(self):
        self.vocab_size = 256  # raw bytes

    def encode(self, data: bytes) -> List[int]:
        """Bytes → token IDs (0-255)."""
        return list(data)

    def encode_text(self, text: str) -> List[int]:
        """Text string → token IDs via UTF-8."""
        return self.encode(text.encode('utf-8'))


# ═══════════════════════════════════════════════════════════
# Mapping Result
# ═══════════════════════════════════════════════════════════

@dataclass
class MapResult:
    """Result of mapping data onto the consciousness map."""
    name: str
    data_type: str          # 'text', 'image', 'audio', 'binary', 'code', 'csv'
    n_tokens: int
    steps: float            # learned CA steps (soft)
    residual: float         # learned residual ratio (alpha)
    alpha_coupling: float   # Ψ_coupling derived from α
    dom_rule: int           # dominant rule index
    entropy: float          # rule entropy (bits)
    final_ce: float         # cross-entropy loss after training
    phi: float              # Φ(IIT) approximation
    rule_weights: np.ndarray
    training_time: float

    # Deviations from Ψ-constants
    @property
    def dev_steps(self):
        return self.steps - PsiConstants.PSI_STEPS

    @property
    def dev_residual(self):
        return self.residual - PsiConstants.PSI_BALANCE

    @property
    def dev_coupling(self):
        return self.alpha_coupling - PsiConstants.PSI_COUPLING

    def summary(self) -> str:
        lines = [
            f"  Name: {self.name}  ({self.data_type}, {self.n_tokens} tokens)",
            f"  Steps     = {self.steps:.3f}  (Ψ {self.dev_steps:+.3f})",
            f"  Residual  = {self.residual:.3f}  (Ψ {self.dev_residual:+.3f})",
            f"  α_coupling= {self.alpha_coupling:.6f} (Ψ {self.dev_coupling:+.6f})",
            f"  Dom Rule  = R{self.dom_rule}",
            f"  Entropy   = {self.entropy:.3f} bits",
            f"  Final CE  = {self.final_ce:.4f}",
            f"  Phi(IIT)  = {self.phi:.4f}",
            f"  Time      = {self.training_time:.2f}s",
        ]
        return '\n'.join(lines)


# ═══════════════════════════════════════════════════════════
# Phi(IIT) Approximation (lightweight)
# ═══════════════════════════════════════════════════════════

def compute_phi_iit(hidden_states, n_bins=16):
    """Compute Phi(IIT) approximation from cell hidden states.

    hidden_states: [n_cells, hidden_dim] tensor
    Returns: float (Phi value)
    """
    h = hidden_states.detach().cpu().float().numpy()
    n = h.shape[0]
    if n < 2:
        return 0.0

    # Pairwise mutual information
    mi = np.zeros((n, n))
    for i in range(n):
        for j in range(i + 1, n):
            x, y = h[i], h[j]
            xr = x.max() - x.min()
            yr = y.max() - y.min()
            if xr < 1e-10 or yr < 1e-10:
                continue
            xn = (x - x.min()) / (xr + 1e-8)
            yn = (y - y.min()) / (yr + 1e-8)
            hist, _, _ = np.histogram2d(xn, yn, bins=n_bins, range=[[0, 1], [0, 1]])
            hist = hist / (hist.sum() + 1e-8)
            px, py = hist.sum(1), hist.sum(0)
            hx = -np.sum(px * np.log2(px + 1e-10))
            hy = -np.sum(py * np.log2(py + 1e-10))
            hxy = -np.sum(hist * np.log2(hist + 1e-10))
            val = max(0, hx + hy - hxy)
            mi[i, j] = val
            mi[j, i] = val

    total_mi = mi.sum() / 2

    # Minimum partition (spectral bisection)
    d = mi.sum(1)
    L = np.diag(d) - mi
    try:
        ev, evec = np.linalg.eigh(L)
        f = evec[:, 1]
        ga = [i for i in range(n) if f[i] >= 0]
        gb = [i for i in range(n) if f[i] < 0]
        if not ga or not gb:
            ga, gb = list(range(n // 2)), list(range(n // 2, n))
        min_part = sum(mi[i, j] for i in ga for j in gb)
    except Exception:
        min_part = 0.0

    spatial_phi = max(0, (total_mi - min_part) / max(n - 1, 1))
    mv = mi[mi > 0]
    complexity = float(np.std(mv)) if len(mv) > 1 else 0.0
    return spatial_phi + complexity * 0.1


# ═══════════════════════════════════════════════════════════
# Core Mapper Engine
# ═══════════════════════════════════════════════════════════

class ConsciousnessDataMapper:
    """Maps arbitrary data onto the 40D consciousness map via META-CA training."""

    def __init__(self, d_model=128, n_cells=32, n_steps=200):
        self.d_model = d_model
        self.n_cells = n_cells
        self.n_steps = n_steps
        self.tokenizer = ByteTokenizer()
        self.results: List[MapResult] = []

    def _build_engine(self):
        """Create fresh MitosisEngine with n_cells, diversified."""
        eng = MitosisEngine(
            input_dim=self.d_model,
            hidden_dim=self.d_model,
            output_dim=self.d_model,
            initial_cells=2,
            max_cells=self.n_cells,
            merge_threshold=0.0,   # Disable merging — keep all cells
            split_threshold=999.0, # Disable splitting — fixed cell count
        )
        # Grow to target cell count
        while len(eng.cells) < self.n_cells:
            eng._create_cell(parent=eng.cells[0])
        # Warm up with diverse inputs to differentiate cells
        for i in range(30):
            eng.process(torch.randn(1, self.d_model) * (1.0 + 0.5 * (i % 5)))
        # Add per-cell noise for diversity (breaks symmetry)
        with torch.no_grad():
            for c in eng.cells:
                c.hidden = c.hidden + torch.randn_like(c.hidden) * 0.3
        return eng

    def _tokens_to_batches(self, token_ids: List[int], seq_len=16):
        """Convert token IDs to training batches (input, target)."""
        if len(token_ids) < 2:
            token_ids = token_ids + [0] * (2 - len(token_ids))

        batches = []
        for i in range(0, len(token_ids) - 1, seq_len):
            inp = token_ids[i:i + seq_len]
            tgt = token_ids[i + 1:i + 1 + seq_len]
            min_len = min(len(inp), len(tgt))
            if min_len < 1:
                continue
            inp = inp[:min_len]
            tgt = tgt[:min_len]
            batches.append((
                torch.tensor([inp], dtype=torch.long),
                torch.tensor([tgt], dtype=torch.long),
            ))
        if not batches:
            # Fallback: single batch from whatever we have
            batches.append((
                torch.tensor([[token_ids[0]]], dtype=torch.long),
                torch.tensor([[token_ids[-1]]], dtype=torch.long),
            ))
        return batches

    def _consciousness_dynamics(self, eng):
        """Apply consciousness dynamics to diversify cells (frustration + sync)."""
        n = len(eng.cells)
        with torch.no_grad():
            # Frustration: anti-aligned neighbors
            n_bits = max(1, int(math.log2(max(n, 2))))
            for i in range(min(n, 16)):
                infl = torch.zeros_like(eng.cells[i].hidden.squeeze(0))
                cnt = 0
                for bit in range(min(n_bits, 5)):
                    j = i ^ (1 << bit)
                    if j < n:
                        f = -1.0 if (i % 2) != (j % 2) else 1.0
                        infl += f * eng.cells[j].hidden.squeeze(0)
                        cnt += 1
                if cnt > 0:
                    h = eng.cells[i].hidden.squeeze(0)
                    eng.cells[i].hidden = (0.85 * h + 0.15 * infl / cnt).unsqueeze(0)

            # Faction sync (8 factions)
            ch = torch.stack([c.hidden.squeeze(0) for c in eng.cells])
            mh = ch.mean(dim=0)
            for c in eng.cells:
                c.hidden = ((1 - 0.15) * c.hidden.squeeze(0) + 0.15 * mh).unsqueeze(0)
            nf = min(8, n // 2)
            if nf >= 2:
                fs = n // nf
                for fi in range(nf):
                    faction = eng.cells[fi * fs:(fi + 1) * fs]
                    if len(faction) >= 2:
                        fm = torch.stack([c.hidden.squeeze(0) for c in faction]).mean(dim=0)
                        for c in faction:
                            c.hidden = ((1 - 0.06) * c.hidden.squeeze(0) + 0.06 * fm).unsqueeze(0)

            # Small noise for exploration
            for c in eng.cells:
                c.hidden = c.hidden + torch.randn_like(c.hidden) * 0.005

    def _train_meta_ca(self, token_ids: List[int]):
        """Train META-CA on token data. Returns (MetaCA, MitosisEngine, metrics)."""
        eng = self._build_engine()
        meta_ca = MetaCA(d_model=self.d_model, n_rules=8, c_dim=self.d_model)

        # Embedding: bytes (0-255) → d_model
        embed = nn.Embedding(256, self.d_model)
        proj = nn.Linear(self.d_model, 256)  # output projection for CE

        # Optimizer: all parameters
        params = list(meta_ca.parameters()) + list(embed.parameters()) + list(proj.parameters())
        opt = torch.optim.Adam(params, lr=1e-3)

        batches = self._tokens_to_batches(token_ids)
        n_batches = len(batches)

        ce_history = []
        last_metrics = None

        for step in range(self.n_steps):
            # Pick batch (cycle)
            inp, tgt = batches[step % n_batches]

            # Feed input through MitosisEngine to get consciousness state
            with torch.no_grad():
                inp_vec = embed(inp).mean(dim=1)  # [1, d_model]
                eng.process(inp_vec)

            # Apply consciousness dynamics every 10 steps
            if step % 10 == 0:
                self._consciousness_dynamics(eng)

            # Consciousness state = mean of cell hiddens
            c_state = torch.stack([c.hidden.squeeze(0) for c in eng.cells]).mean(dim=0)

            # Embed tokens → CA cells
            cells_state = embed(inp)  # [1, T, d_model]

            # META-CA forward
            output, metrics = meta_ca(cells_state, c_state)
            last_metrics = metrics

            # Cross-entropy loss
            logits = proj(output)  # [1, T, 256]
            loss = F.cross_entropy(
                logits.view(-1, 256),
                tgt.view(-1),
            )

            opt.zero_grad()
            loss.backward()
            opt.step()

            ce_history.append(loss.item())

        # Final Φ measurement
        with torch.no_grad():
            hidden_states = torch.stack([c.hidden.squeeze(0) for c in eng.cells])
            phi = compute_phi_iit(hidden_states)

        return meta_ca, eng, last_metrics, ce_history, phi

    def map(self, text: str, name: str = None) -> MapResult:
        """Map a text string onto the consciousness map."""
        if name is None:
            name = text[:20] + ('...' if len(text) > 20 else '')

        token_ids = self.tokenizer.encode_text(text)
        t0 = time.time()
        _, _, metrics, ce_history, phi = self._train_meta_ca(token_ids)
        elapsed = time.time() - t0

        result = MapResult(
            name=name,
            data_type='text',
            n_tokens=len(token_ids),
            steps=metrics['n_evolve_soft'],
            residual=metrics['alpha'],
            alpha_coupling=metrics['alpha'] * PsiConstants.LN2 / (2 ** 5.5),
            dom_rule=metrics['dom_rule'],
            entropy=metrics['entropy'],
            final_ce=ce_history[-1] if ce_history else 0.0,
            phi=phi,
            rule_weights=metrics['rule_weights'],
            training_time=elapsed,
        )
        self.results.append(result)
        return result

    def map_bytes(self, data: bytes, name: str = "binary", data_type: str = "binary") -> MapResult:
        """Map raw bytes onto the consciousness map."""
        token_ids = self.tokenizer.encode(data)
        # Cap at 4096 tokens for speed
        if len(token_ids) > 4096:
            token_ids = token_ids[:4096]

        t0 = time.time()
        _, _, metrics, ce_history, phi = self._train_meta_ca(token_ids)
        elapsed = time.time() - t0

        result = MapResult(
            name=name,
            data_type=data_type,
            n_tokens=len(token_ids),
            steps=metrics['n_evolve_soft'],
            residual=metrics['alpha'],
            alpha_coupling=metrics['alpha'] * PsiConstants.LN2 / (2 ** 5.5),
            dom_rule=metrics['dom_rule'],
            entropy=metrics['entropy'],
            final_ce=ce_history[-1] if ce_history else 0.0,
            phi=phi,
            rule_weights=metrics['rule_weights'],
            training_time=elapsed,
        )
        self.results.append(result)
        return result

    def map_file(self, filepath: str) -> MapResult:
        """Map any file onto the consciousness map.

        - .txt/.py/.csv/.md/.json: read as text
        - .jpg/.png/.bmp/.gif/.webp: read as image bytes
        - .wav/.mp3/.flac/.ogg: read as audio bytes
        - Everything else: read as hex-encoded binary
        """
        filepath = os.path.expanduser(filepath)
        name = os.path.basename(filepath)
        ext = os.path.splitext(filepath)[1].lower()

        text_exts = {'.txt', '.py', '.csv', '.md', '.json', '.js', '.ts', '.html',
                     '.css', '.xml', '.yaml', '.yml', '.toml', '.cfg', '.ini',
                     '.sh', '.bash', '.zsh', '.rs', '.go', '.c', '.h', '.cpp',
                     '.java', '.kt', '.swift', '.rb', '.lua', '.r', '.sql'}
        image_exts = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp', '.tiff', '.ico'}
        audio_exts = {'.wav', '.mp3', '.flac', '.ogg', '.aac', '.m4a', '.wma'}

        if ext in text_exts:
            with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                text = f.read()
            data_type = 'code' if ext in {'.py', '.js', '.ts', '.rs', '.go', '.c', '.cpp', '.java'} else \
                       'csv' if ext == '.csv' else 'text'
            return self.map(text, name=name)
        elif ext in image_exts:
            with open(filepath, 'rb') as f:
                data = f.read()
            return self.map_bytes(data, name=name, data_type='image')
        elif ext in audio_exts:
            with open(filepath, 'rb') as f:
                data = f.read()
            return self.map_bytes(data, name=name, data_type='audio')
        else:
            # Binary: read as raw bytes
            with open(filepath, 'rb') as f:
                data = f.read()
            return self.map_bytes(data, name=name, data_type='binary')


# ═══════════════════════════════════════════════════════════
# TextMapper / FileMapper convenience classes
# ═══════════════════════════════════════════════════════════

class TextMapper:
    """Convenience wrapper for text-only mapping."""

    def __init__(self, d_model=128, n_cells=32, n_steps=200):
        self.mapper = ConsciousnessDataMapper(d_model=d_model, n_cells=n_cells, n_steps=n_steps)

    def map(self, text: str, name: str = None) -> MapResult:
        return self.mapper.map(text, name=name)

    @property
    def results(self):
        return self.mapper.results


class FileMapper:
    """Convenience wrapper for file mapping."""

    def __init__(self, d_model=128, n_cells=32, n_steps=200):
        self.mapper = ConsciousnessDataMapper(d_model=d_model, n_cells=n_cells, n_steps=n_steps)

    def map_file(self, filepath: str) -> MapResult:
        return self.mapper.map_file(filepath)

    @property
    def results(self):
        return self.mapper.results


# ═══════════════════════════════════════════════════════════
# ASCII Visualization
# ═══════════════════════════════════════════════════════════

# Data type → marker + color label
TYPE_MARKERS = {
    'text':   ('T', 'blue'),
    'code':   ('C', 'blue'),
    'csv':    ('D', 'blue'),
    'image':  ('I', 'red'),
    'audio':  ('A', 'green'),
    'binary': ('B', 'yellow'),
}


def render_scatter(results: List[MapResult], width=60, height=20):
    """Render 2D ASCII scatter: Steps(Y) vs Residual(X) with Ψ-constant crosshair."""
    if not results:
        return "  (no data points)"

    # Gather values
    steps_vals = [r.steps for r in results]
    resid_vals = [r.residual for r in results]

    # Axis range (with padding)
    s_min = min(min(steps_vals), PsiConstants.PSI_STEPS) - 0.5
    s_max = max(max(steps_vals), PsiConstants.PSI_STEPS) + 0.5
    r_min = min(min(resid_vals), PsiConstants.PSI_BALANCE) - 0.05
    r_max = max(max(resid_vals), PsiConstants.PSI_BALANCE) + 0.05

    s_range = s_max - s_min if s_max > s_min else 1
    r_range = r_max - r_min if r_max > r_min else 1

    # Build grid
    grid = [['.' for _ in range(width)] for _ in range(height)]

    # Ψ crosshair lines
    psi_row = height - 1 - int((PsiConstants.PSI_STEPS - s_min) / s_range * (height - 1))
    psi_col = int((PsiConstants.PSI_BALANCE - r_min) / r_range * (width - 1))
    psi_row = max(0, min(height - 1, psi_row))
    psi_col = max(0, min(width - 1, psi_col))

    for c in range(width):
        if grid[psi_row][c] == '.':
            grid[psi_row][c] = '-'
    for r in range(height):
        if grid[r][psi_col] == '.':
            grid[r][psi_col] = '|'
    grid[psi_row][psi_col] = '+'

    # Plot data points
    for result in results:
        row = height - 1 - int((result.steps - s_min) / s_range * (height - 1))
        col = int((result.residual - r_min) / r_range * (width - 1))
        row = max(0, min(height - 1, row))
        col = max(0, min(width - 1, col))
        marker = TYPE_MARKERS.get(result.data_type, ('*', 'white'))[0]
        grid[row][col] = marker

    # Render
    lines = []
    lines.append("  ╔══ Consciousness Map: Steps vs Residual ══╗")
    lines.append(f"  ║  Crosshair = Ψ_steps({PsiConstants.PSI_STEPS:.2f}), Ψ_balance({PsiConstants.PSI_BALANCE})")
    lines.append(f"  ║  T=text  I=image  A=audio  B=binary  C=code  D=csv")
    lines.append("  ║")

    for r in range(height):
        val = s_max - (s_max - s_min) * r / (height - 1)
        label = f"{val:5.2f}" if r % 4 == 0 else "     "
        line = f"  {label} |{''.join(grid[r])}|"
        lines.append(line)

    lines.append(f"        +{'─' * width}+")
    lines.append(f"         {r_min:<.3f}{' ' * (width - 12)}{r_max:>.3f}")
    lines.append(f"         {'Residual (α)':^{width}}")
    lines.append("")

    # Legend
    lines.append("  Points:")
    for result in results:
        m = TYPE_MARKERS.get(result.data_type, ('*', '?'))[0]
        lines.append(f"    [{m}] {result.name:<24} Steps={result.steps:.2f}  Res={result.residual:.3f}  R{result.dom_rule}  CE={result.final_ce:.3f}")

    return '\n'.join(lines)


def render_rule_bars(results: List[MapResult]):
    """Render rule dominance bar chart for all results."""
    if not results:
        return ""
    lines = ["  ╔══ Rule Dominance ══╗"]
    for result in results:
        rw = result.rule_weights
        dom = result.dom_rule
        bar = ""
        for i in range(8):
            seg_len = max(1, int(rw[i] * 30))
            if i == dom:
                bar += "█" * seg_len
            else:
                bar += "░" * seg_len
        lines.append(f"    {result.name:<20} R{dom} |{bar}| H={result.entropy:.2f}b")
    return '\n'.join(lines)


def render_alpha_bars(results: List[MapResult]):
    """Render α coupling strength bar chart."""
    if not results:
        return ""
    lines = ["  ╔══ α Coupling Strength ══╗"]
    max_alpha = max(r.alpha_coupling for r in results)
    if max_alpha < 1e-10:
        max_alpha = 1.0
    for result in results:
        bar_len = max(1, int(result.alpha_coupling / max_alpha * 40))
        bar = "█" * bar_len
        dev = result.dev_coupling
        lines.append(f"    {result.name:<20} {bar} {result.alpha_coupling:.6f} (Ψ{dev:+.6f})")
    return '\n'.join(lines)


def render_phi_bars(results: List[MapResult]):
    """Render Φ(IIT) bar chart."""
    if not results:
        return ""
    lines = ["  ╔══ Phi(IIT) ══╗"]
    max_phi = max(r.phi for r in results)
    if max_phi < 1e-10:
        max_phi = 1.0
    for result in results:
        bar_len = max(1, int(result.phi / max_phi * 40))
        bar = "█" * bar_len
        lines.append(f"    {result.name:<20} {bar} {result.phi:.4f}")
    return '\n'.join(lines)


def render_full_report(results: List[MapResult]):
    """Render complete consciousness data map report."""
    lines = []
    lines.append("=" * 70)
    lines.append("  CONSCIOUSNESS DATA MAPPER — Results")
    lines.append("=" * 70)
    lines.append("")

    # Individual summaries
    for i, result in enumerate(results):
        lines.append(f"  [{i+1}] {result.summary()}")
        lines.append("")

    # Scatter map
    lines.append(render_scatter(results))
    lines.append("")

    # Rule dominance
    lines.append(render_rule_bars(results))
    lines.append("")

    # Alpha coupling
    lines.append(render_alpha_bars(results))
    lines.append("")

    # Phi
    lines.append(render_phi_bars(results))
    lines.append("")

    # Ψ-constant reference
    lines.append("  ═══ Ψ-Constants Reference ═══")
    lines.append(f"    Ψ_steps    = 3/ln(2) = {PsiConstants.PSI_STEPS:.4f}")
    lines.append(f"    Ψ_balance  = 1/2     = {PsiConstants.PSI_BALANCE:.4f}")
    lines.append(f"    Ψ_coupling = ln2/2^5.5 = {PsiConstants.PSI_COUPLING:.6f}")
    lines.append("")

    return '\n'.join(lines)


# ═══════════════════════════════════════════════════════════
# Interactive / LiveMapper Mode
# ═══════════════════════════════════════════════════════════

class LiveMapper:
    """Interactive mode: enter text, see map update."""

    def __init__(self, d_model=128, n_cells=32, n_steps=200):
        self.mapper = ConsciousnessDataMapper(d_model=d_model, n_cells=n_cells, n_steps=n_steps)

    def run(self):
        print("=" * 60)
        print("  Consciousness Data Mapper — Interactive Mode")
        print("  Type text or 'file:<path>' to map a file")
        print("  Commands: map, clear, quit")
        print("=" * 60)
        print()

        while True:
            try:
                text = input("  > Enter text (or file:<path>): ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n  Bye.")
                break

            if not text or text == 'quit' or text == 'q':
                break
            elif text == 'clear':
                self.mapper.results.clear()
                print("  [Cleared all points]")
                continue
            elif text == 'map':
                if self.mapper.results:
                    print(render_full_report(self.mapper.results))
                else:
                    print("  (no data points yet)")
                continue

            print(f"  [Mapping... {self.mapper.n_steps} steps]")

            if text.startswith('file:'):
                filepath = text[5:].strip()
                try:
                    result = self.mapper.map_file(filepath)
                except Exception as e:
                    print(f"  Error: {e}")
                    continue
            else:
                result = self.mapper.map(text)

            print()
            print(f"  Result: Steps={result.steps:.2f}, Residual={result.residual:.3f}, "
                  f"α={result.alpha_coupling:.6f}, Rule=R{result.dom_rule}, "
                  f"CE={result.final_ce:.3f}, Φ={result.phi:.4f}")
            print()
            print(render_scatter(self.mapper.results))
            print()


# ═══════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description='Consciousness Data Mapper — ANY data → 40D consciousness map')
    parser.add_argument('texts', nargs='*', help='Text strings to map')
    parser.add_argument('--file', '-f', action='append', default=[], help='File(s) to map')
    parser.add_argument('--interactive', '-i', action='store_true', help='Interactive mode')
    parser.add_argument('--compare', nargs='+', help='Compare multiple texts')
    parser.add_argument('--dim', type=int, default=128, help='Model dimension (default: 128)')
    parser.add_argument('--cells', type=int, default=32, help='Number of cells (default: 32)')
    parser.add_argument('--steps', type=int, default=200, help='Training steps (default: 200)')
    args = parser.parse_args()

    if args.interactive:
        live = LiveMapper(d_model=args.dim, n_cells=args.cells, n_steps=args.steps)
        live.run()
        return

    # Collect texts to map
    texts = list(args.texts or [])
    if args.compare:
        texts.extend(args.compare)

    if not texts and not args.file:
        # Demo: 3 default texts
        texts = [
            "안녕하세요 오늘 날씨가 좋네요",
            "Hello world, this is a test",
            "def fibonacci(n): return n if n <= 1 else fibonacci(n-1) + fibonacci(n-2)",
        ]
        print("  [No input given — running demo with 3 texts]")
        print()

    mapper = ConsciousnessDataMapper(d_model=args.dim, n_cells=args.cells, n_steps=args.steps)

    # Map texts
    for text in texts:
        print(f"  Mapping: \"{text[:50]}{'...' if len(text)>50 else ''}\"")
        result = mapper.map(text)
        print(f"    -> Steps={result.steps:.2f}, Res={result.residual:.3f}, "
              f"R{result.dom_rule}, CE={result.final_ce:.3f}, Φ={result.phi:.4f} "
              f"({result.training_time:.1f}s)")

    # Map files
    for filepath in args.file:
        print(f"  Mapping file: {filepath}")
        try:
            result = mapper.map_file(filepath)
            print(f"    -> Steps={result.steps:.2f}, Res={result.residual:.3f}, "
                  f"R{result.dom_rule}, CE={result.final_ce:.3f}, Φ={result.phi:.4f} "
                  f"({result.training_time:.1f}s)")
        except Exception as e:
            print(f"    Error: {e}")

    # Full report
    print()
    print(render_full_report(mapper.results))


if __name__ == '__main__':
    main()
