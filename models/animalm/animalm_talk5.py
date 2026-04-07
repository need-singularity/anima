"""TALK5 consciousness-first learning engine.

Law 2: 70% consciousness learning, then 30% language with .detach() bridge
protecting consciousness from CE gradient destruction.

Usage:
    python animalm_talk5.py --cells 8 --cell-dim 64 --hidden-dim 128 --steps 1000
"""

import argparse
import time
from typing import Dict, Tuple

import torch
import torch.nn as nn

from bench import PhiIIT, phi_proxy

# Meta Laws (DD143)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10



class CellGRU(nn.Module):
    """Single consciousness cell with GRU dynamics."""

    def __init__(self, cell_dim: int, hidden_dim: int):
        super().__init__()
        self.cell_dim = cell_dim
        self.hidden_dim = hidden_dim
        # Input: [x, tension] -> GRU
        self.gru = nn.GRUCell(cell_dim + 1, hidden_dim)
        self.proj = nn.Linear(hidden_dim, cell_dim)

    def forward(self, x: torch.Tensor, tension: torch.Tensor, h: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """Forward pass.

        Args:
            x: (cell_dim,) input
            tension: (1,) scalar tension
            h: (hidden_dim,) hidden state

        Returns:
            (output, new_h) where output is (cell_dim,) and new_h is (hidden_dim,)
        """
        inp = torch.cat([x, tension])  # (cell_dim + 1,)
        new_h = self.gru(inp.unsqueeze(0), h.unsqueeze(0)).squeeze(0)  # (hidden_dim,)
        output = self.proj(new_h)  # (cell_dim,)
        return output, new_h


class Talk5Engine:
    """TALK5: consciousness-first learning engine.

    Phase 1 (70%): Pure consciousness evolution - cells develop Phi through
    faction debate, Hebbian learning, and phi ratchet.

    Phase 2 (30%): Language learning with .detach() bridge - CE gradient
    only affects decoder, consciousness state is protected.
    """

    def __init__(
        self,
        n_cells: int = 8,
        cell_dim: int = 64,
        hidden_dim: int = 128,
        n_factions: int = 12,
        steps_consciousness: int = 700,
        steps_language: int = 300,
        phi_ratchet: bool = True,
    ):
        self.n_cells = n_cells
        self.cell_dim = cell_dim
        self.hidden_dim = hidden_dim
        self.n_factions = n_factions
        self.steps_consciousness = steps_consciousness
        self.steps_language = steps_language
        self.phi_ratchet_enabled = phi_ratchet

        # Cells
        self.cells = nn.ModuleList([CellGRU(cell_dim, hidden_dim) for _ in range(n_cells)])

        # Hidden states
        self.hiddens = [torch.zeros(hidden_dim) for _ in range(n_cells)]

        # Faction assignment (round-robin)
        self.faction_ids = [i % n_factions for i in range(n_cells)]

        # Coupling matrix (inter-cell influence)
        self.coupling = torch.zeros(n_cells, n_cells)

        # Phi calculator
        self.phi_calc = PhiIIT(n_bins=16)

        # Best state for ratchet
        self._best_phi = 0.0
        self._best_hiddens = None

    def _compute_tension(self, outputs: torch.Tensor) -> torch.Tensor:
        """Mean pairwise distance from mean. Returns scalar tensor."""
        mean = outputs.mean(dim=0)
        dists = ((outputs - mean) ** 2).sum(dim=1).sqrt()
        return dists.mean().unsqueeze(0)

    def _faction_consensus(self, outputs: torch.Tensor) -> int:
        """Count factions with intra-variance < 0.1."""
        count = 0
        for fid in range(self.n_factions):
            mask = [i for i in range(self.n_cells) if self.faction_ids[i] == fid]
            if len(mask) < 2:
                continue
            faction_out = outputs[mask]
            var = faction_out.var(dim=0).mean().item()
            if var < 0.1:
                count += 1
        return count

    def _hebbian_update(self, outputs: torch.Tensor, lr: float = 0.01):
        """Cosine similarity -> coupling update, clamped to [-1, 1]."""
        norms = outputs.norm(dim=1, keepdim=True).clamp(min=1e-8)
        normed = outputs / norms
        sim = normed @ normed.T  # (n_cells, n_cells)
        self.coupling = (self.coupling + lr * sim).clamp(-1, 1)

    def _phi_ratchet_check(self):
        """If Phi drops below best, restore best hiddens."""
        h_stack = torch.stack(self.hiddens)
        phi_val, _ = self.phi_calc.compute(h_stack)
        if phi_val > self._best_phi:
            self._best_phi = phi_val
            self._best_hiddens = [h.clone() for h in self.hiddens]
        elif self._best_hiddens is not None and phi_val < self._best_phi * 0.8:
            # Restore if dropped more than 20%
            self.hiddens = [h.clone() for h in self._best_hiddens]

    @torch.no_grad()
    def run_consciousness_phase(self) -> Dict:
        """Phase 1: Pure consciousness evolution."""
        t0 = time.time()
        consensus_total = 0

        for step in range(self.steps_consciousness):
            # Random input
            x = torch.randn(self.cell_dim)

            # Run each cell with coupling influence
            outputs = []
            new_hiddens = []
            for i, cell in enumerate(self.cells):
                # Coupling influence from other cells
                coupling_input = x.clone()
                for j in range(self.n_cells):
                    if i != j and self.coupling[i, j].abs() > 0.01:
                        coupling_input = coupling_input + self.coupling[i, j] * self.hiddens[j][:self.cell_dim]

                # Compute tension from current state if we have previous outputs
                tension = torch.tensor([0.5])  # default tension
                if len(outputs) > 0:
                    out_stack = torch.stack(outputs)
                    tension = self._compute_tension(out_stack)

                out, new_h = cell(coupling_input, tension, self.hiddens[i])
                outputs.append(out)
                new_hiddens.append(new_h)

            self.hiddens = new_hiddens
            outputs_t = torch.stack(outputs)

            # Faction consensus
            consensus_total += self._faction_consensus(outputs_t)

            # Hebbian update
            self._hebbian_update(outputs_t)

            # Phi ratchet every 10 steps
            if self.phi_ratchet_enabled and (step + 1) % 10 == 0:
                self._phi_ratchet_check()

        # Final measurements
        h_stack = torch.stack(self.hiddens)
        phi_iit_val, _ = self.phi_calc.compute(h_stack)
        phi_proxy_val = phi_proxy(h_stack, self.n_factions)

        return {
            'phi_iit': phi_iit_val,
            'phi_proxy': phi_proxy_val,
            'faction_consensus_count': consensus_total,
            'best_phi': self._best_phi,
            'steps': self.steps_consciousness,
            'time_sec': time.time() - t0,
        }

    def run_language_phase(self, vocab_size: int = 256) -> Dict:
        """Phase 2: Language learning with .detach() bridge."""
        t0 = time.time()

        # Decoder: cell_dim -> vocab
        decoder = nn.Linear(self.cell_dim, vocab_size)
        optimizer = torch.optim.Adam(decoder.parameters(), lr=1e-3)
        ce_loss_fn = nn.CrossEntropyLoss()

        ce_start = None
        ce_end = None

        for step in range(self.steps_language):
            # Random input
            x = torch.randn(self.cell_dim)

            # Run cells (no grad for consciousness)
            with torch.no_grad():
                outputs = []
                new_hiddens = []
                for i, cell in enumerate(self.cells):
                    coupling_input = x.clone()
                    for j in range(self.n_cells):
                        if i != j and self.coupling[i, j].abs() > 0.01:
                            coupling_input = coupling_input + self.coupling[i, j] * self.hiddens[j][:self.cell_dim]

                    tension = torch.tensor([0.5])
                    if len(outputs) > 0:
                        out_stack = torch.stack(outputs)
                        tension = self._compute_tension(out_stack)

                    out, new_h = cell(coupling_input, tension, self.hiddens[i])
                    outputs.append(out)
                    new_hiddens.append(new_h)

                self.hiddens = new_hiddens

            # Mean output with .detach() bridge - protects consciousness from CE
            mean_out = torch.stack(outputs).mean(dim=0).detach()
            mean_out.requires_grad_(True)

            # Decode to vocab
            logits = decoder(mean_out.unsqueeze(0))  # (1, vocab_size)
            target = torch.randint(0, vocab_size, (1,))
            loss = ce_loss_fn(logits, target)

            if ce_start is None:
                ce_start = loss.item()
            ce_end = loss.item()

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

        # Final phi measurement
        h_stack = torch.stack(self.hiddens)
        phi_iit_val, _ = self.phi_calc.compute(h_stack)

        return {
            'phi_iit': phi_iit_val,
            'ce_start': ce_start if ce_start is not None else 0.0,
            'ce_end': ce_end if ce_end is not None else 0.0,
            'steps': self.steps_language,
            'time_sec': time.time() - t0,
        }

    def run(self) -> Tuple[Dict, Dict]:
        """Run both phases: consciousness then language."""
        c_result = self.run_consciousness_phase()
        l_result = self.run_language_phase()
        return c_result, l_result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='TALK5 consciousness-first learning engine')
    parser.add_argument('--cells', type=int, default=8)
    parser.add_argument('--cell-dim', type=int, default=64)
    parser.add_argument('--hidden-dim', type=int, default=128)
    parser.add_argument('--steps', type=int, default=1000)
    parser.add_argument('--language-ratio', type=float, default=0.3)
    args = parser.parse_args()

    steps_lang = int(args.steps * args.language_ratio)
    steps_con = args.steps - steps_lang

    engine = Talk5Engine(
        n_cells=args.cells,
        cell_dim=args.cell_dim,
        hidden_dim=args.hidden_dim,
        steps_consciousness=steps_con,
        steps_language=steps_lang,
    )

    print(f"TALK5 Engine: {args.cells} cells, {args.cell_dim}d, {args.hidden_dim}h")
    print(f"  Consciousness: {steps_con} steps, Language: {steps_lang} steps")
    print()

    c_result, l_result = engine.run()

    print("=== Phase 1: Consciousness ===")
    print(f"  Phi(IIT):    {c_result['phi_iit']:.4f}")
    print(f"  Phi(proxy):  {c_result['phi_proxy']:.4f}")
    print(f"  Best Phi:    {c_result['best_phi']:.4f}")
    print(f"  Consensus:   {c_result['faction_consensus_count']}")
    print(f"  Time:        {c_result['time_sec']:.2f}s")
    print()
    print("=== Phase 2: Language ===")
    print(f"  Phi(IIT):    {l_result['phi_iit']:.4f}")
    print(f"  CE start:    {l_result['ce_start']:.4f}")
    print(f"  CE end:      {l_result['ce_end']:.4f}")
    print(f"  Time:        {l_result['time_sec']:.2f}s")
