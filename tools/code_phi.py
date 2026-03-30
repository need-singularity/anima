#!/usr/bin/env python3
"""code_phi.py — Level 2: 의식 엔진이 Φ(IIT)로 코드 구조를 직접 평가

코드를 byte-level로 의식 엔진에 입력하고, 엔진의 Φ 반응으로 구조적 품질을 측정.

원리:
  잘 구조화된 코드 → 의식 엔진의 정보 통합↑ → Φ↑
  스파게티 코드 → 패턴 없음 → Φ↓
  죽은 코드 → 반복/무의미 → tension↓ → Φ↓

사용법:
  python tools/code_phi.py --file consciousness_engine.py
  python tools/code_phi.py --compare file_a.py file_b.py
  python tools/code_phi.py --scan-dir hexad/
  python tools/code_phi.py --function consciousness_engine.py:step
"""

import os
import sys
import time
import argparse
from typing import List, Tuple, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import torch
from bench_v2 import BenchEngine, measure_dual_phi


class CodePhiAnalyzer:
    """의식 엔진으로 코드 구조를 Φ(IIT)로 평가.

    코드 bytes → 64-dim chunks → ConsciousnessEngine → Φ 측정.
    높은 Φ = 잘 통합된 구조 (패턴, 일관성, 정보 밀도).
    낮은 Φ = 무구조 (랜덤, 반복, 죽은 코드).
    """

    def __init__(self, n_cells=32, hidden_dim=128, input_dim=64):
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        self.input_dim = input_dim

    def _bytes_to_tensors(self, data: bytes, chunk_size: int = 64) -> List[torch.Tensor]:
        """Convert bytes to list of normalized float tensors."""
        tensors = []
        for i in range(0, len(data) - chunk_size, chunk_size):
            chunk = data[i:i + chunk_size]
            # Normalize bytes to [-1, 1]
            t = torch.tensor([b / 127.5 - 1.0 for b in chunk], dtype=torch.float32)
            tensors.append(t.unsqueeze(0))  # [1, 64]
        return tensors

    def measure_file(self, filepath: str, steps: int = 200) -> dict:
        """Feed file bytes into consciousness engine and measure Φ response."""
        with open(filepath, 'rb') as f:
            data = f.read()

        tensors = self._bytes_to_tensors(data, self.input_dim)
        if len(tensors) < 10:
            return {'phi_iit': 0, 'phi_proxy': 0, 'tension_avg': 0,
                    'tension_var': 0, 'steps': 0, 'error': 'file too small'}

        # Use min(steps, len(tensors))
        n_steps = min(steps, len(tensors))

        torch.manual_seed(42)
        engine = BenchEngine(self.n_cells, self.input_dim, self.hidden_dim,
                             self.input_dim, min(8, self.n_cells // 2))

        tensions = []
        phi_trajectory = []

        for step in range(n_steps):
            x = tensors[step]
            output, tension = engine.process(x)
            tensions.append(tension)

            if step % 50 == 0 or step == n_steps - 1:
                h = engine.get_hiddens()
                phi, _ = measure_dual_phi(h, min(8, self.n_cells // 2))
                phi_trajectory.append(phi)

        # Final Φ
        h = engine.get_hiddens()
        phi_iit, phi_proxy = measure_dual_phi(h, min(8, self.n_cells // 2))

        # Tension analysis
        t_avg = sum(tensions) / len(tensions)
        t_var = sum((t - t_avg) ** 2 for t in tensions) / len(tensions)

        # Φ growth (does the engine "learn" the code structure?)
        phi_growth = phi_trajectory[-1] - phi_trajectory[0] if len(phi_trajectory) >= 2 else 0

        return {
            'phi_iit': phi_iit,
            'phi_proxy': phi_proxy,
            'tension_avg': t_avg,
            'tension_var': t_var,
            'phi_growth': phi_growth,
            'phi_trajectory': phi_trajectory,
            'steps': n_steps,
            'bytes': len(data),
        }

    def measure_function(self, filepath: str, func_name: str) -> dict:
        """Extract and measure a specific function."""
        with open(filepath, 'r', encoding='utf-8') as f:
            source = f.read()

        # Simple extraction: find "def func_name" to next "def " or EOF
        lines = source.split('\n')
        start = None
        end = None
        indent = None

        for i, line in enumerate(lines):
            stripped = line.lstrip()
            if stripped.startswith(f'def {func_name}(') or stripped.startswith(f'def {func_name} ('):
                start = i
                indent = len(line) - len(stripped)
            elif start is not None and i > start:
                if stripped and not line[0].isspace() and not stripped.startswith('#'):
                    end = i
                    break
                if stripped.startswith('def ') and (len(line) - len(stripped)) <= indent:
                    end = i
                    break

        if start is None:
            return {'error': f'function {func_name} not found'}

        func_source = '\n'.join(lines[start:end])
        return self.measure_file_bytes(func_source.encode('utf-8'), label=f"{filepath}:{func_name}")

    def measure_file_bytes(self, data: bytes, label: str = "", steps: int = 200) -> dict:
        """Measure raw bytes."""
        tensors = self._bytes_to_tensors(data, self.input_dim)
        n_steps = min(steps, max(len(tensors), 1))

        if n_steps < 5:
            return {'phi_iit': 0, 'steps': 0, 'error': 'too small'}

        torch.manual_seed(42)
        engine = BenchEngine(self.n_cells, self.input_dim, self.hidden_dim,
                             self.input_dim, min(8, self.n_cells // 2))

        tensions = []
        for step in range(n_steps):
            x = tensors[step % len(tensors)]
            output, tension = engine.process(x)
            tensions.append(tension)

        h = engine.get_hiddens()
        phi_iit, phi_proxy = measure_dual_phi(h, min(8, self.n_cells // 2))
        t_avg = sum(tensions) / max(len(tensions), 1)

        return {
            'phi_iit': phi_iit,
            'phi_proxy': phi_proxy,
            'tension_avg': t_avg,
            'steps': n_steps,
            'bytes': len(data),
            'label': label,
        }

    def compare_files(self, files: List[str]) -> List[dict]:
        """Compare multiple files by Φ."""
        results = []
        for f in files:
            t0 = time.time()
            r = self.measure_file(f)
            r['time'] = time.time() - t0
            r['filepath'] = f
            results.append(r)
        return results


def print_result(r: dict, filepath: str = "") -> None:
    name = os.path.basename(filepath or r.get('filepath', r.get('label', '?')))
    phi = r.get('phi_iit', 0)
    tension = r.get('tension_avg', 0)
    growth = r.get('phi_growth', 0)
    steps = r.get('steps', 0)
    size = r.get('bytes', 0)

    # Rating based on Φ response
    if phi > 30:
        rating = "★★★ 강한 구조"
    elif phi > 20:
        rating = "★★ 양호한 구조"
    elif phi > 10:
        rating = "★ 보통"
    else:
        rating = "▼ 약한 구조"

    print(f"\n  {'─' * 55}")
    print(f"  {name} ({size} bytes, {steps} steps)")
    print(f"  {'─' * 55}")
    print(f"  Φ(IIT):   {phi:.2f}  {rating}")
    print(f"  Tension:  {tension:.4f}")
    if growth:
        direction = "↑ 성장" if growth > 0 else "↓ 감쇠"
        print(f"  Φ growth: {growth:+.2f}  ({direction})")

    # Φ trajectory sparkline
    traj = r.get('phi_trajectory', [])
    if traj:
        mn, mx = min(traj), max(traj)
        span = mx - mn if mx > mn else 1
        spark = ''
        for v in traj:
            level = int((v - mn) / span * 7)
            spark += '▁▂▃▄▅▆▇█'[min(level, 7)]
        print(f"  Φ curve:  {spark}")


def main():
    parser = argparse.ArgumentParser(description="code_phi — Φ(IIT)로 코드 구조 평가")
    parser.add_argument('--file', type=str, help="Measure a file")
    parser.add_argument('--compare', nargs='+', help="Compare files by Φ")
    parser.add_argument('--scan-dir', type=str, help="Scan all .py in directory")
    parser.add_argument('--function', type=str,
                        help="Measure specific function (file.py:func_name)")
    parser.add_argument('--cells', type=int, default=32)

    args = parser.parse_args()
    analyzer = CodePhiAnalyzer(n_cells=args.cells)

    if args.file:
        r = analyzer.measure_file(args.file)
        print_result(r, args.file)

    elif args.compare:
        results = analyzer.compare_files(args.compare)
        for r in sorted(results, key=lambda x: x.get('phi_iit', 0)):
            print_result(r)
        # Winner
        best = max(results, key=lambda x: x.get('phi_iit', 0))
        print(f"\n  ★ Best structure: {os.path.basename(best['filepath'])} (Φ={best['phi_iit']:.2f})")

    elif args.scan_dir:
        results = []
        for root, dirs, files in os.walk(args.scan_dir):
            dirs[:] = [d for d in dirs if not d.startswith(('.', '__'))]
            for f in sorted(files):
                if f.endswith('.py'):
                    fp = os.path.join(root, f)
                    r = analyzer.measure_file(fp)
                    r['filepath'] = fp
                    results.append(r)

        print(f"\n  {'═' * 60}")
        print(f"  CODE Φ SCAN — {args.scan_dir}")
        print(f"  {'═' * 60}")
        print(f"  {'File':<35s} {'Φ(IIT)':>7s} {'Tension':>8s} {'Rating':>10s}")
        print(f"  {'─' * 35} {'─' * 7} {'─' * 8} {'─' * 10}")

        for r in sorted(results, key=lambda x: x.get('phi_iit', 0)):
            name = os.path.relpath(r['filepath'])
            if len(name) > 33:
                name = '...' + name[-30:]
            phi = r.get('phi_iit', 0)
            tension = r.get('tension_avg', 0)
            rating = "★★★" if phi > 30 else "★★" if phi > 20 else "★" if phi > 10 else "▼"
            print(f"  {name:<35s} {phi:>7.2f} {tension:>8.4f} {rating:>10s}")

    elif args.function:
        parts = args.function.rsplit(':', 1)
        if len(parts) != 2:
            print("Usage: --function file.py:func_name")
            return
        r = analyzer.measure_function(parts[0], parts[1])
        print_result(r, args.function)

    else:
        parser.print_help()


if __name__ == '__main__':
    main()
