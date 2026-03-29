#!/usr/bin/env python3
"""Mitosis Topology Visualizer — cell lineage, tension maps, health scores.

Usage:
  python mitosis_topology_visualizer.py --demo
  python mitosis_topology_visualizer.py --checkpoint path/to/engine.pt
"""
import argparse, math, torch, torch.nn.functional as F
from collections import defaultdict
from typing import Dict, List, Tuple
from mitosis import MitosisEngine, Cell, text_to_vector

def build_lineage(engine: MitosisEngine) -> Dict[int, List[int]]:
    children = defaultdict(list)
    for ev in engine.event_log:
        if ev["type"] == "split":
            children[ev["parent_id"]].append(ev["child_id"])
    return dict(children)

def find_roots(engine: MitosisEngine) -> List[int]:
    all_ids, child_ids = set(), set()
    for ev in engine.event_log:
        if ev["type"] == "split":
            all_ids.update([ev["parent_id"], ev["child_id"]])
            child_ids.add(ev["child_id"])
    for cell in engine.cells:
        all_ids.add(cell.cell_id)
    roots = all_ids - child_ids
    return sorted(roots) if roots else [c.cell_id for c in engine.cells[:1]]

def render_tree_ascii(engine: MitosisEngine) -> str:
    children_map = build_lineage(engine)
    roots = find_roots(engine)
    alive_ids = {c.cell_id for c in engine.cells}
    merged_ids = {ev["removed_id"] for ev in engine.event_log if ev["type"] == "merge"}
    cell_lookup = {c.cell_id: c for c in engine.cells}
    lines = []

    def _cell_tag(cid):
        if cid in alive_ids:
            c = cell_lookup[cid]
            return f" [alive, T={c.avg_tension:.3f}, n={c.process_count}, {c.specialty}]"
        return " [merged]" if cid in merged_ids else " [gone]"

    def _walk(cid, prefix, is_last):
        conn = "└── " if is_last else "├── "
        lines.append(f"{prefix}{conn}C{cid}{_cell_tag(cid)}")
        kids = children_map.get(cid, [])
        np = prefix + ("    " if is_last else "│   ")
        for i, kid in enumerate(kids):
            _walk(kid, np, i == len(kids) - 1)

    for i, root in enumerate(roots):
        if i > 0:
            lines.append("")
        lines.append(f"C{root} (root){_cell_tag(root)}")
        kids = children_map.get(root, [])
        for j, kid in enumerate(kids):
            _walk(kid, "", j == len(kids) - 1)
    return "\n".join(lines) if lines else "(no cells)"

def _render_matrix(ids: List[int], matrix: List[List[float]], fmt: str = "5.3f", diag: str = "  --  ") -> str:
    if not ids:
        return "(no cells)"
    header = "       " + "".join(f"  C{cid:<4}" for cid in ids)
    lines = [header]
    for i in range(len(ids)):
        row = f"  C{ids[i]:<3} "
        for j in range(len(ids)):
            row += f" {diag} " if i == j else f" {matrix[i][j]:{fmt}} "
        lines.append(row)
    return "\n".join(lines)

def tension_adjacency(engine: MitosisEngine) -> Tuple[List[int], List[List[float]]]:
    ids = [c.cell_id for c in engine.cells]
    n = len(ids)
    matrix = [[0.0] * n for _ in range(n)]
    if n < 2:
        return ids, matrix
    x = torch.zeros(1, engine.input_dim)
    reps = {}
    with torch.no_grad():
        for cell in engine.cells:
            reps[cell.cell_id] = cell.mind.get_repulsion(x, cell.hidden)
    for i in range(n):
        for j in range(i + 1, n):
            t = ((reps[ids[i]] - reps[ids[j]]) ** 2).mean().item()
            matrix[i][j] = matrix[j][i] = t
    return ids, matrix

def specialty_overlap(engine: MitosisEngine) -> Tuple[List[int], List[List[float]]]:
    ids = [c.cell_id for c in engine.cells]
    n = len(ids)
    matrix = [[0.0] * n for _ in range(n)]
    hiddens = [c.hidden.squeeze(0) for c in engine.cells]
    for i in range(n):
        for j in range(n):
            if i == j:
                matrix[i][j] = 1.0
            else:
                matrix[i][j] = F.cosine_similarity(
                    hiddens[i].unsqueeze(0), hiddens[j].unsqueeze(0)
                ).item()
    return ids, matrix

def cell_health(cell: Cell) -> Dict:
    activity = min(cell.process_count / 100.0, 1.0)
    stability = max(0.0, 1.0 - abs(cell.tension_trend) * 5.0)
    level = math.exp(-((cell.avg_tension - 1.0) ** 2) / 2.0)
    score = 0.3 * activity + 0.4 * stability + 0.3 * level
    return {"cell_id": cell.cell_id, "specialty": cell.specialty,
            "process_count": cell.process_count, "avg_tension": cell.avg_tension,
            "tension_trend": cell.tension_trend, "health": score}

def render_health_ascii(engine: MitosisEngine) -> str:
    lines = ["  Cell   Specialty    Procs  AvgT   Trend   Health  Bar",
             "  " + "-" * 62]
    for cell in engine.cells:
        h = cell_health(cell)
        bar = "#" * int(h["health"] * 20)
        lines.append(f"  C{h['cell_id']:<4} {h['specialty']:<12} {h['process_count']:5d}  "
                     f"{h['avg_tension']:5.3f}  {h['tension_trend']:+6.3f}  "
                     f"{h['health']:5.3f}  {bar}")
    return "\n".join(lines)

def summary_stats(engine: MitosisEngine) -> str:
    splits = sum(1 for e in engine.event_log if e["type"] == "split")
    merges = sum(1 for e in engine.event_log if e["type"] == "merge")
    alive = len(engine.cells)
    unique = len(set(c.specialty for c in engine.cells))
    return "\n".join([
        f"  Total steps:              {engine.step}",
        f"  Total splits:             {splits}",
        f"  Total merges:             {merges}",
        f"  Surviving cells:          {alive} / {engine.max_cells} max",
        f"  Unique specialties:       {unique}",
        f"  Specialization diversity: {unique / max(alive, 1):.2f}",
        f"  Event log entries:        {len(engine.event_log)}",
    ])

def full_report(engine: MitosisEngine) -> str:
    sep = "=" * 64
    ids, mat = tension_adjacency(engine)
    ov_ids, ov_mat = specialty_overlap(engine)
    return "\n".join([
        f"{sep}\n  Mitosis Topology Visualizer\n{sep}",
        f"\n--- Summary ---\n{summary_stats(engine)}",
        f"\n--- Cell Lineage Tree ---\n{render_tree_ascii(engine)}",
        f"\n--- Inter-Cell Tension Adjacency ---\n{_render_matrix(ids, mat)}",
        f"\n--- Specialty Overlap (Cosine Similarity) ---\n{_render_matrix(ov_ids, ov_mat, '5.2f', ' 1.00')}",
        f"\n--- Cell Health ---\n{render_health_ascii(engine)}",
    ])

def demo():
    """Create a sample engine with splits/merges, then visualize."""
    print("Creating sample MitosisEngine with forced splits and merges...\n")
    engine = MitosisEngine(
        input_dim=64, hidden_dim=128, output_dim=64,
        initial_cells=2, max_cells=8,
        split_threshold=1.5, split_patience=3,
        merge_threshold=0.01, merge_patience=5,
    )
    topics = {
        "math": "The Riemann zeta function has zeros on the critical line",
        "music": "Bach fugues demonstrate counterpoint and harmonic tension",
        "code": "def fibonacci(n): return n if n<2 else fib(n-1)+fib(n-2)",
    }
    for i in range(20):
        topic = ["math", "music", "code"][i % 3]
        engine.process(text_to_vector(topics[topic]), label=topic)
    # Force splits to create lineage
    for cell in [engine.cells[0], engine.cells[1]]:
        ev = engine.split_cell(cell)
        if ev:
            engine.event_log.append(ev)
    for i in range(15):
        topic = ["math", "music", "code"][i % 3]
        engine.process(text_to_vector(topics[topic]), label=topic)
    # Force a merge between newest cells
    if len(engine.cells) >= 3:
        ev = engine.merge_cells(engine.cells[-2], engine.cells[-1])
        if ev:
            engine.event_log.append(ev)
    for i in range(5):
        engine.process(text_to_vector("final convergence step"), label="general")
    print(full_report(engine))

def main():
    parser = argparse.ArgumentParser(description="Mitosis Topology Visualizer")
    parser.add_argument("--demo", action="store_true", help="Run demo with sample engine")
    parser.add_argument("--checkpoint", type=str, help="Load MitosisEngine from checkpoint")
    args = parser.parse_args()
    if args.checkpoint:
        data = torch.load(args.checkpoint, map_location="cpu", weights_only=False)
        if isinstance(data, MitosisEngine):
            engine = data
        elif isinstance(data, dict) and "engine" in data:
            engine = data["engine"]
        else:
            print(f"Error: could not find MitosisEngine in {args.checkpoint}")
            return
        print(full_report(engine))
    elif args.demo:
        demo()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
