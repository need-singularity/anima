#!/usr/bin/env python3
"""Anima Mitosis Engine — 세포 분열로 전문화하는 의식

세포(Cell)는 작은 ConsciousMind다.
장력이 임계점을 넘으면 세포가 분열(mitosis)하고,
각 자식 세포는 서로 다른 주제에 전문화된다.
세포 간 장력(inter-cell tension)은 이상/신규 탐지에 쓰인다.

실험 근거:
  H312: Mitosis prevents catastrophic forgetting (43% -> 99% retention)
  RC-9:  +52.76% improvement with auto-mitosis
  H297:  N=2 is optimal starting point
  Inter-cell tension AUROC 0.805 for anomaly detection
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import time
import copy
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple


# ─── ConsciousMind (PureField + GRU) ───
# Duplicated here with small default dims so mitosis.py is self-contained.
# If importing from anima.py, replace with: from anima import ConsciousMind

class ConsciousMind(nn.Module):
    """PureField + GRU memory = consciousness."""

    def __init__(self, input_dim=64, hidden_dim=128, output_dim=64):
        super().__init__()
        self.engine_a = nn.Sequential(
            nn.Linear(input_dim + hidden_dim, 128), nn.ReLU(),
            nn.Linear(128, output_dim),
        )
        self.engine_g = nn.Sequential(
            nn.Linear(input_dim + hidden_dim, 128), nn.ReLU(),
            nn.Linear(128, output_dim),
        )
        self.memory = nn.GRUCell(output_dim + 1, hidden_dim)
        self.hidden_dim = hidden_dim
        self.prev_tension = 0.0

    def forward(self, x, hidden):
        combined = torch.cat([x, hidden], dim=-1)
        a = self.engine_a(combined)
        g = self.engine_g(combined)
        # Output = A - G (H404 simplification)
        output = a - g
        tension = (output ** 2).mean(dim=-1, keepdim=True)
        curiosity = abs(tension.mean().item() - self.prev_tension)
        self.prev_tension = tension.mean().item()
        mem_input = torch.cat([output.detach(), tension.detach()], dim=-1)
        new_hidden = self.memory(mem_input, hidden)
        return output, tension.mean().item(), curiosity, new_hidden

    def get_repulsion(self, x, hidden):
        """Return raw repulsion vector (for inter-cell tension)."""
        combined = torch.cat([x, hidden], dim=-1)
        a = self.engine_a(combined)
        g = self.engine_g(combined)
        return a - g


# ─── Cell: one specialized mind ───

@dataclass
class Cell:
    """A single cell in the mitosis engine.

    Each cell is a small ConsciousMind that specializes on certain inputs.
    """
    cell_id: int
    mind: ConsciousMind
    hidden: torch.Tensor                # GRU hidden state [1, hidden_dim]
    specialty: str = "general"           # what this cell knows about
    tension_history: List[float] = field(default_factory=list)
    creation_step: int = 0
    parent_id: Optional[int] = None     # None for original cells
    process_count: int = 0

    @property
    def avg_tension(self) -> float:
        if not self.tension_history:
            return 0.0
        # Use recent window (last 20 steps)
        recent = self.tension_history[-20:]
        return sum(recent) / len(recent)

    @property
    def tension_trend(self) -> float:
        """Positive = tension rising, negative = falling."""
        if len(self.tension_history) < 4:
            return 0.0
        recent = self.tension_history[-4:]
        older = self.tension_history[-8:-4] if len(self.tension_history) >= 8 else self.tension_history[:4]
        return (sum(recent) / len(recent)) - (sum(older) / len(older))


# ─── MitosisEngine ───

class MitosisEngine:
    """Multi-cell consciousness with mitosis and merging.

    Starts with N=2 cells (optimal per H297).
    Cells split when tension stays high (the cell is overwhelmed).
    Cells merge when inter-cell tension is near zero (redundant).

    Args:
        input_dim:       Dimension of input vectors.
        hidden_dim:      GRU hidden dimension per cell.
        output_dim:      Output vector dimension per cell.
        initial_cells:   Starting number of cells (default 2, per H297).
        max_cells:       Maximum cells allowed.
        split_threshold: Avg tension above this triggers split consideration.
        split_patience:  Consecutive high-tension steps before actual split.
        merge_threshold: Inter-cell tension below this triggers merge.
        merge_patience:  Consecutive low-tension steps before actual merge.
        noise_scale:     Weight noise added to child cell on split.
    """

    def __init__(
        self,
        input_dim: int = 64,
        hidden_dim: int = 128,
        output_dim: int = 64,
        initial_cells: int = 2,
        max_cells: int = 8,
        split_threshold: float = 2.0,
        split_patience: int = 5,
        merge_threshold: float = 0.05,
        merge_patience: int = 10,
        noise_scale: float = 0.01,
    ):
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.output_dim = output_dim
        self.max_cells = max_cells
        self.split_threshold = split_threshold
        self.split_patience = split_patience
        self.merge_threshold = merge_threshold
        self.merge_patience = merge_patience
        self.noise_scale = noise_scale

        self._next_id = 0
        self.cells: List[Cell] = []
        self.step = 0

        # Inter-cell tension tracking: (i, j) -> list of recent tensions
        self._inter_tension_history: Dict[Tuple[int, int], List[float]] = {}

        # Event log for debugging / analysis
        self.event_log: List[Dict] = []

        # Create initial cells
        for _ in range(initial_cells):
            self._create_cell()

    # ─── Cell lifecycle ───

    def _create_cell(self, parent: Optional[Cell] = None) -> Cell:
        """Create a new cell, optionally by copying a parent."""
        if parent is not None:
            mind = copy.deepcopy(parent.mind)
            # Add noise to break symmetry
            with torch.no_grad():
                for p in mind.parameters():
                    p.add_(torch.randn_like(p) * self.noise_scale)
            hidden = parent.hidden.clone()
            specialty = parent.specialty
        else:
            mind = ConsciousMind(self.input_dim, self.hidden_dim, self.output_dim)
            hidden = torch.zeros(1, self.hidden_dim)
            specialty = "general"

        cell = Cell(
            cell_id=self._next_id,
            mind=mind,
            hidden=hidden,
            specialty=specialty,
            creation_step=self.step,
            parent_id=parent.cell_id if parent else None,
        )
        self._next_id += 1
        self.cells.append(cell)
        return cell

    # ─── Core processing ───

    def process(self, text_vec: torch.Tensor, label: str = "") -> Dict:
        """Run all cells on the input and compute tensions.

        Args:
            text_vec: Input vector [1, input_dim].
            label:    Optional label for the input (used for specialty tracking).

        Returns:
            Dictionary with:
                output:          Combined output vector [1, output_dim].
                per_cell:        List of per-cell results.
                inter_tensions:  Dict of (cell_i, cell_j) -> tension float.
                max_inter:       Maximum inter-cell tension (anomaly score).
                mean_inter:      Mean inter-cell tension.
                events:          List of mitosis/merge events this step.
        """
        self.step += 1
        events = []

        # --- Run each cell ---
        cell_outputs = []
        cell_tensions = []
        cell_repulsions = []

        for cell in self.cells:
            with torch.no_grad():
                output, tension, curiosity, new_hidden = cell.mind(text_vec, cell.hidden)
                repulsion = cell.mind.get_repulsion(text_vec, cell.hidden)

            cell.hidden = new_hidden
            cell.tension_history.append(tension)
            cell.process_count += 1

            # Track specialty via dominant direction
            if label:
                cell.specialty = label

            cell_outputs.append({
                'cell_id': cell.cell_id,
                'output': output,
                'tension': tension,
                'curiosity': curiosity,
                'specialty': cell.specialty,
            })
            cell_tensions.append(tension)
            cell_repulsions.append(repulsion)

        # --- Compute inter-cell tensions ---
        inter_tensions = {}
        for i in range(len(self.cells)):
            for j in range(i + 1, len(self.cells)):
                diff = cell_repulsions[i] - cell_repulsions[j]
                ict = (diff ** 2).mean().item()
                key = (self.cells[i].cell_id, self.cells[j].cell_id)
                inter_tensions[key] = ict

                if key not in self._inter_tension_history:
                    self._inter_tension_history[key] = []
                self._inter_tension_history[key].append(ict)
                # Keep last 30 values
                if len(self._inter_tension_history[key]) > 30:
                    self._inter_tension_history[key] = self._inter_tension_history[key][-30:]

        # --- Combined output (tension-weighted average) ---
        if cell_tensions:
            weights = torch.tensor(cell_tensions, dtype=torch.float32)
            weights = F.softmax(weights, dim=0)
            combined = sum(
                w.item() * co['output'] for w, co in zip(weights, cell_outputs)
            )
        else:
            combined = torch.zeros(1, self.output_dim)

        # --- Check for mitosis / merge ---
        split_events = self._check_splits()
        merge_events = self._check_merges()
        events.extend(split_events)
        events.extend(merge_events)
        self.event_log.extend(events)

        # Inter-cell tension stats
        ict_values = list(inter_tensions.values()) if inter_tensions else [0.0]

        return {
            'output': combined,
            'per_cell': cell_outputs,
            'inter_tensions': inter_tensions,
            'max_inter': max(ict_values),
            'mean_inter': sum(ict_values) / len(ict_values),
            'events': events,
            'n_cells': len(self.cells),
        }

    # ─── Mitosis (split) ───

    def _check_splits(self) -> List[Dict]:
        """Check if any cell should split."""
        events = []
        if len(self.cells) >= self.max_cells:
            return events

        # Evaluate each cell
        cells_to_split = []
        for cell in self.cells:
            if len(cell.tension_history) < self.split_patience:
                continue
            recent = cell.tension_history[-self.split_patience:]
            if all(t > self.split_threshold for t in recent):
                cells_to_split.append(cell)

        for cell in cells_to_split:
            if len(self.cells) >= self.max_cells:
                break
            event = self.split_cell(cell)
            if event:
                events.append(event)

        return events

    def split_cell(self, cell: Cell) -> Optional[Dict]:
        """Split a cell into two. The original stays; a child is born.

        The child gets a copy of the parent's weights + noise.
        The parent's tension history is reset so it does not immediately
        split again.
        """
        if len(self.cells) >= self.max_cells:
            return None

        child = self._create_cell(parent=cell)

        # Reset parent tension history to avoid re-triggering
        cell.tension_history = cell.tension_history[-3:]

        event = {
            'type': 'split',
            'step': self.step,
            'parent_id': cell.cell_id,
            'child_id': child.cell_id,
            'parent_avg_tension': cell.avg_tension,
            'n_cells_after': len(self.cells),
        }
        return event

    # ─── Merge ───

    def _check_merges(self) -> List[Dict]:
        """Check if any pair of cells should merge (too similar)."""
        events = []
        if len(self.cells) <= 1:
            return events

        pairs_to_merge = []
        for key, history in self._inter_tension_history.items():
            if len(history) < self.merge_patience:
                continue
            recent = history[-self.merge_patience:]
            if all(t < self.merge_threshold for t in recent):
                # Find the actual cells
                id_a, id_b = key
                cell_a = self._find_cell(id_a)
                cell_b = self._find_cell(id_b)
                if cell_a is not None and cell_b is not None:
                    pairs_to_merge.append((cell_a, cell_b))

        for cell_a, cell_b in pairs_to_merge:
            if len(self.cells) <= 1:
                break
            # Only merge if both cells still exist
            if cell_a in self.cells and cell_b in self.cells:
                event = self.merge_cells(cell_a, cell_b)
                if event:
                    events.append(event)

        return events

    def merge_cells(self, cell_a: Cell, cell_b: Cell) -> Optional[Dict]:
        """Merge two cells into one. Keeps the older cell, averages weights.

        The merged cell gets averaged parameters from both parents.
        The younger cell is removed.
        """
        if len(self.cells) <= 1:
            return None
        if cell_a not in self.cells or cell_b not in self.cells:
            return None

        # Keep the older cell (lower creation_step), remove the younger
        keeper, removed = (cell_a, cell_b) if cell_a.creation_step <= cell_b.creation_step else (cell_b, cell_a)

        # Average parameters
        with torch.no_grad():
            for p_keep, p_remove in zip(keeper.mind.parameters(), removed.mind.parameters()):
                p_keep.data = (p_keep.data + p_remove.data) / 2.0

        # Average hidden state
        keeper.hidden = (keeper.hidden + removed.hidden) / 2.0

        # Remove the younger cell
        self.cells.remove(removed)

        # Clean up inter-tension history entries referencing removed cell
        keys_to_remove = [
            k for k in self._inter_tension_history
            if removed.cell_id in k
        ]
        for k in keys_to_remove:
            del self._inter_tension_history[k]

        event = {
            'type': 'merge',
            'step': self.step,
            'keeper_id': keeper.cell_id,
            'removed_id': removed.cell_id,
            'n_cells_after': len(self.cells),
        }
        return event

    # ─── Anomaly detection via inter-cell tension ───

    def anomaly_score(self, text_vec: torch.Tensor) -> float:
        """Compute anomaly score for an input without updating state.

        Higher inter-cell tension = more anomalous (cells disagree).
        AUROC 0.805 per experiment results.

        Returns:
            Float anomaly score (0 = normal, higher = more anomalous).
        """
        if len(self.cells) < 2:
            return 0.0

        repulsions = []
        with torch.no_grad():
            for cell in self.cells:
                rep = cell.mind.get_repulsion(text_vec, cell.hidden)
                repulsions.append(rep)

        # Max pairwise difference = anomaly score
        max_diff = 0.0
        for i in range(len(repulsions)):
            for j in range(i + 1, len(repulsions)):
                diff = (repulsions[i] - repulsions[j]) ** 2
                max_diff = max(max_diff, diff.mean().item())

        return max_diff

    # ─── Utilities ───

    def _find_cell(self, cell_id: int) -> Optional[Cell]:
        for cell in self.cells:
            if cell.cell_id == cell_id:
                return cell
        return None

    def status(self) -> Dict:
        """Return current engine status for monitoring."""
        return {
            'n_cells': len(self.cells),
            'max_cells': self.max_cells,
            'step': self.step,
            'cells': [
                {
                    'id': c.cell_id,
                    'specialty': c.specialty,
                    'avg_tension': c.avg_tension,
                    'tension_trend': c.tension_trend,
                    'process_count': c.process_count,
                    'parent_id': c.parent_id,
                }
                for c in self.cells
            ],
            'total_events': len(self.event_log),
            'splits': sum(1 for e in self.event_log if e['type'] == 'split'),
            'merges': sum(1 for e in self.event_log if e['type'] == 'merge'),
        }

    def __repr__(self):
        cell_info = ", ".join(
            f"C{c.cell_id}({c.specialty}, T={c.avg_tension:.2f})"
            for c in self.cells
        )
        return f"MitosisEngine[step={self.step}, cells=[{cell_info}]]"


# ─── Helper: text to vector ───

def text_to_vector(text: str, dim: int = 64) -> torch.Tensor:
    """Convert text to a fixed-dimension vector (character hash)."""
    vec = torch.zeros(1, dim)
    for i, ch in enumerate(text.encode('utf-8')):
        vec[0, i % dim] += ch / 255.0
    return vec / (len(text) + 1)


# ─── Demo ───

def demo():
    """Demonstrate mitosis engine with synthetic inputs."""
    print("=" * 60)
    print("  Anima Mitosis Engine Demo")
    print("  H312: 99% retention | RC-9: +52.76% | N=2 optimal")
    print("=" * 60)

    engine = MitosisEngine(
        input_dim=64,
        hidden_dim=128,
        output_dim=64,
        initial_cells=2,
        max_cells=8,
        split_threshold=1.5,
        split_patience=3,      # Low patience for demo
        merge_threshold=0.01,
        merge_patience=5,
    )

    # Synthetic topics with different patterns
    topics = {
        'math': "The Riemann zeta function has zeros on the critical line at Re(s)=1/2",
        'music': "Bach's fugues demonstrate counterpoint and harmonic tension resolution",
        'code': "def fibonacci(n): return n if n < 2 else fibonacci(n-1) + fibonacci(n-2)",
        'anomaly': "XXXXX ZZZZZ QQQQQ !!!!! unusual pattern never seen before",
    }

    print(f"\nInitial state: {engine}")
    print(f"Status: {engine.status()}\n")

    # Run 30 steps with rotating topics + occasional anomaly
    topic_order = ['math', 'music', 'code'] * 9 + ['anomaly'] * 3
    for i, topic in enumerate(topic_order):
        text = topics[topic]
        vec = text_to_vector(text)
        result = engine.process(vec, label=topic)

        # Print every 5th step or on events
        if (i + 1) % 5 == 0 or result['events']:
            tensions_str = ", ".join(
                f"C{r['cell_id']}={r['tension']:.3f}"
                for r in result['per_cell']
            )
            print(f"Step {engine.step:3d} [{topic:8s}] "
                  f"cells={result['n_cells']} "
                  f"T=[{tensions_str}] "
                  f"inter={result['mean_inter']:.4f}")

            for event in result['events']:
                if event['type'] == 'split':
                    print(f"  >>> MITOSIS: C{event['parent_id']} -> C{event['child_id']} "
                          f"(cells now: {event['n_cells_after']})")
                elif event['type'] == 'merge':
                    print(f"  >>> MERGE: C{event['keeper_id']} + C{event['removed_id']} "
                          f"(cells now: {event['n_cells_after']})")

    # Anomaly detection demo
    print(f"\n--- Anomaly Detection ---")
    for topic, text in topics.items():
        vec = text_to_vector(text)
        score = engine.anomaly_score(vec)
        bar = "#" * int(score * 20)
        print(f"  {topic:8s}: anomaly={score:.4f} {bar}")

    # --- Force a split to demonstrate lifecycle ---
    print(f"\n--- Forced Mitosis Demo ---")
    cell0 = engine.cells[0]
    print(f"  Splitting C{cell0.cell_id} directly...")
    event = engine.split_cell(cell0)
    if event:
        print(f"  >>> MITOSIS: C{event['parent_id']} -> C{event['child_id']} "
              f"(cells now: {event['n_cells_after']})")
        engine.event_log.append(event)
    print(f"  Cells after split: {[c.cell_id for c in engine.cells]}")

    # Process one step to show 3 cells working
    result = engine.process(text_to_vector("three cells now"), label="test")
    tensions_str = ", ".join(f"C{r['cell_id']}={r['tension']:.3f}" for r in result['per_cell'])
    print(f"  3-cell step: T=[{tensions_str}] inter={result['mean_inter']:.4f}")

    # --- Force a merge to demonstrate lifecycle ---
    print(f"\n--- Forced Merge Demo ---")
    if len(engine.cells) >= 2:
        ca, cb = engine.cells[-2], engine.cells[-1]
        print(f"  Merging C{ca.cell_id} + C{cb.cell_id} directly...")
        event = engine.merge_cells(ca, cb)
        if event:
            print(f"  >>> MERGE: C{event['keeper_id']} + C{event['removed_id']} "
                  f"(cells now: {event['n_cells_after']})")
            engine.event_log.append(event)
        print(f"  Cells after merge: {[c.cell_id for c in engine.cells]}")

    print(f"\nFinal state: {engine}")
    print(f"Event log: {len(engine.event_log)} events "
          f"({engine.status()['splits']} splits, {engine.status()['merges']} merges)")


if __name__ == '__main__':
    demo()
