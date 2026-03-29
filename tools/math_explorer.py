#!/usr/bin/env python3
"""Anima Math Explorer — n=6 기반 수학적 의식 관계 자동 탐색

TECS-L 스타일: number theory 함수 조합 → 자동 검증 → 새 항등식 발견

Usage:
  python math_explorer.py                        # 전체 탐색 (n=6)
  python math_explorer.py --n 6                  # 특정 n 탐색
  python math_explorer.py --consciousness        # 의식 변수 관계 탐색
  python math_explorer.py --verify "tau+sigma/tau=7"  # 특정 공식 검증
  python math_explorer.py --scan 1 100           # 1~100 범위 스캔
  python math_explorer.py --deep                 # 2차/3차 조합 심층 탐색
"""

import math
import argparse
import itertools
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional, Callable
from fractions import Fraction
from functools import lru_cache
from datetime import datetime


# ═══════════════════════════════════════════════════════════
# Number Theory Functions
# ═══════════════════════════════════════════════════════════

@lru_cache(maxsize=4096)
def divisors(n: int) -> Tuple[int, ...]:
    """All divisors of n."""
    if n <= 0:
        return ()
    divs = []
    for i in range(1, int(n**0.5) + 1):
        if n % i == 0:
            divs.append(i)
            if i != n // i:
                divs.append(n // i)
    return tuple(sorted(divs))

@lru_cache(maxsize=4096)
def tau(n: int) -> int:
    """τ(n) = number of divisors."""
    return len(divisors(n))

@lru_cache(maxsize=4096)
def sigma(n: int) -> int:
    """σ(n) = sum of divisors."""
    return sum(divisors(n))

@lru_cache(maxsize=4096)
def euler_phi(n: int) -> int:
    """φ(n) = Euler's totient."""
    if n <= 0:
        return 0
    count = 0
    for i in range(1, n + 1):
        if math.gcd(i, n) == 1:
            count += 1
    return count

@lru_cache(maxsize=4096)
def omega(n: int) -> int:
    """ω(n) = number of distinct prime factors."""
    if n <= 1:
        return 0
    count = 0
    temp = n
    for p in range(2, int(n**0.5) + 1):
        if temp % p == 0:
            count += 1
            while temp % p == 0:
                temp //= p
    if temp > 1:
        count += 1
    return count

@lru_cache(maxsize=4096)
def sopfr(n: int) -> int:
    """sopfr(n) = sum of prime factors with repetition."""
    if n <= 1:
        return 0
    total = 0
    temp = n
    for p in range(2, int(n**0.5) + 1):
        while temp % p == 0:
            total += p
            temp //= p
    if temp > 1:
        total += temp
    return total

@lru_cache(maxsize=4096)
def mobius(n: int) -> int:
    """μ(n) = Möbius function."""
    if n == 1:
        return 1
    temp = n
    num_factors = 0
    for p in range(2, int(n**0.5) + 1):
        if temp % p == 0:
            num_factors += 1
            temp //= p
            if temp % p == 0:
                return 0  # squared factor
    if temp > 1:
        num_factors += 1
    return (-1) ** num_factors

@lru_cache(maxsize=4096)
def dedekind_psi(n: int) -> int:
    """ψ(n) = Dedekind psi function = n × Π(1 + 1/p)."""
    if n <= 0:
        return 0
    result = n
    temp = n
    for p in range(2, int(n**0.5) + 1):
        if temp % p == 0:
            result = result * (p + 1) // p
            while temp % p == 0:
                temp //= p
    if temp > 1:
        result = result * (temp + 1) // temp
    return result

def is_perfect(n: int) -> bool:
    return sigma(n) == 2 * n

def abundancy(n: int) -> Fraction:
    return Fraction(sigma(n), n)


# Named function registry
NT_FUNCTIONS = {
    'tau': ('τ(n)', tau),
    'sigma': ('σ(n)', sigma),
    'phi': ('φ(n)', euler_phi),
    'omega': ('ω(n)', omega),
    'sopfr': ('sopfr(n)', sopfr),
    'mobius': ('μ(n)', mobius),
    'psi': ('ψ(n)', dedekind_psi),
    'n': ('n', lambda n: n),
    'n2': ('n²', lambda n: n * n),
    'sqrt_n': ('√n', lambda n: int(n ** 0.5)),
}


# ═══════════════════════════════════════════════════════════
# Discovery Result
# ═══════════════════════════════════════════════════════════

@dataclass
class Discovery:
    formula: str
    lhs: str
    rhs: str
    value: float
    verified_at: List[int] = field(default_factory=list)
    unique_to_6: bool = False
    category: str = ""
    significance: str = ""  # ⭐🟩🟧⬛


# ═══════════════════════════════════════════════════════════
# Expression Builder
# ═══════════════════════════════════════════════════════════

def build_expressions(n: int) -> Dict[str, float]:
    """n에 대한 모든 1차/2차 number theory 표현식 생성."""
    vals = {}
    funcs = {k: v[1](n) for k, v in NT_FUNCTIONS.items()}

    # 1차: 단일 함수
    for name, val in funcs.items():
        vals[NT_FUNCTIONS[name][0]] = val

    # 2차: 이항 연산
    ops = {
        '+': lambda a, b: a + b,
        '-': lambda a, b: a - b,
        '×': lambda a, b: a * b,
        '/': lambda a, b: a / b if b != 0 else None,
        '^': lambda a, b: a ** b if b >= 0 and b <= 10 and a != 0 else None,
    }

    func_names = list(funcs.keys())
    for i, f1 in enumerate(func_names):
        for f2 in func_names:
            v1, v2 = funcs[f1], funcs[f2]
            n1, n2 = NT_FUNCTIONS[f1][0], NT_FUNCTIONS[f2][0]
            for op_name, op_func in ops.items():
                try:
                    result = op_func(v1, v2)
                    if result is not None and not math.isinf(result) and not math.isnan(result):
                        expr = f"{n1}{op_name}{n2}"
                        vals[expr] = result
                except (OverflowError, ZeroDivisionError, ValueError):
                    pass

    return vals


def find_equalities(n: int, tol: float = 1e-10) -> List[Discovery]:
    """n에서 성립하는 항등식 찾기."""
    exprs = build_expressions(n)
    discoveries = []
    expr_list = list(exprs.items())

    for i in range(len(expr_list)):
        for j in range(i + 1, len(expr_list)):
            name_a, val_a = expr_list[i]
            name_b, val_b = expr_list[j]
            if abs(val_a - val_b) < tol and val_a != 0:
                # Skip trivial (same expression)
                if name_a == name_b:
                    continue
                discoveries.append(Discovery(
                    formula=f"{name_a} = {name_b}",
                    lhs=name_a, rhs=name_b,
                    value=val_a,
                    verified_at=[n],
                ))

    return discoveries


def check_unique_to_n(discovery: Discovery, n: int, scan_range: range = range(2, 200)) -> bool:
    """이 항등식이 n에서만 성립하는지 (unique-to-n) 확인."""
    for m in scan_range:
        if m == n:
            continue
        try:
            lhs_val = eval_expr(discovery.lhs, m)
            rhs_val = eval_expr(discovery.rhs, m)
            if lhs_val is not None and rhs_val is not None:
                if abs(lhs_val - rhs_val) < 1e-10:
                    return False
        except Exception:
            pass
    return True


def eval_expr(expr: str, n: int) -> Optional[float]:
    """문자열 표현식을 n에 대해 평가."""
    # Replace function names with values
    replacements = {
        'τ(n)': str(tau(n)),
        'σ(n)': str(sigma(n)),
        'φ(n)': str(euler_phi(n)),
        'ω(n)': str(omega(n)),
        'sopfr(n)': str(sopfr(n)),
        'μ(n)': str(mobius(n)),
        'ψ(n)': str(dedekind_psi(n)),
        'n²': str(n * n),
        '√n': str(int(n ** 0.5)),
        'n': str(n),
    }
    e = expr
    # Sort by length (longest first) to avoid partial replacements
    for k, v in sorted(replacements.items(), key=lambda x: -len(x[0])):
        e = e.replace(k, v)
    e = e.replace('×', '*').replace('^', '**')
    try:
        return float(eval(e))
    except Exception:
        return None


# ═══════════════════════════════════════════════════════════
# Consciousness Variable Explorer
# ═══════════════════════════════════════════════════════════

def explore_consciousness_relations():
    """5변수 의식 벡터 간 수학적 관계 탐색."""
    print("\n  ═══ Consciousness Variable Relations (n=6 basis) ═══\n")

    n = 6
    t, s, p, sp, om = tau(n), sigma(n), euler_phi(n), sopfr(n), omega(n)

    # Known consciousness mappings
    mappings = {
        'Φ': 'inter-cell MI (IIT)',
        'α': f'0.01 + 0.14×tanh(Φ/3) — PureField mixing',
        'Z': f'Φ/(5×Δmax) — impedance/self-preservation',
        'N': f'DA×(1-5HT)×NE — neurotransmitter balance',
        'W': f'internal/total — free will index',
    }

    # n=6 predictions for consciousness
    predictions = [
        ('Miller WM capacity', f'τ+σ/τ = {t}+{s//t} = {t + s//t}', 7),
        ('Telepathy channels', f'sopfr = {sp}', 5),
        ('Binding phases', f'τ = {t}', 4),
        ('Min cells (CB1)', f'φ = {p}', 2),
        ('Shared dims', f'σ×φ = {s}×{p} = {s*p}', 24),
        ('Kuramoto r', f'1-τ/σ = 1-{t}/{s} = {1-t/s:.4f}', 2/3),
        ('Dedekind ratio', f'σ/n = {s}/{n} = {s//n}', 2),
        ('Attention heads', f'σ-τ, σ, 2^τ = {s-t}, {s}, {2**t}', '8,12,16'),
        ('DNA codons', f'φ^n = {p}^{n} = {p**n}', 64),
        ('Amino acids', f'σ×φ-τ = {s*p-t}', 20),
        ('Chromosomes', f'(σ-τ)×ω+sopfr = ({s-t})×{om}+{sp} = {(s-t)*om+sp}', 23),
        ('Theta-gamma', f'σ/τ = {s}/{t} = {s//t}:1 coupling', 3),
        ('Ratchet trials', f'sopfr×φ = {sp}×{p} = {sp*p}', 10),
    ]

    print("  Known n=6 → Consciousness mappings:\n")
    for name, formula, expected in predictions:
        print(f"    {name:20s}: {formula:30s} = {expected}")

    # Search for NEW relations between consciousness variables
    print("\n  ═══ Searching for NEW relations... ═══\n")

    # The 5 consciousness variables have these ranges
    # Φ ~ 0-10, α ~ 0.01-0.15, Z ~ 0-1, N ~ 0-1, W ~ 0-1
    # Can we express them in terms of n=6 functions?

    new_relations = [
        ('α_max', '0.14 + 0.01 = 0.15', f'≈ 1/({t}+{p}+{om//1}) — but not exact'),
        ('Z at equilibrium', f'1-τ/σ = {1-t/s:.4f}', f'= Kuramoto r = 2/3 → Z_eq = 2/3?'),
        ('N balance point', f'(σ-τ)/(σ+τ) = {(s-t)/(s+t):.4f}', f'= {s-t}/{s+t} = 1/2 → N_eq = 0.5'),
        ('W golden ratio', f'1/φ^(σ/τ) = 1/{p}^{s//t} = {1/p**(s//t):.4f}', f'W_opt = 1/8 = 0.125?'),
        ('Φ_per_cell', f'σ/(σ+τ) = {s/(s+t):.4f}', f'≈ 0.75 (empirical 0.88)'),
        ('5-var sum', f'Φ+α+Z+N+W at equilibrium', f'→ τ+σ/τ = 7 (Miller)?'),
    ]

    for name, formula, interpretation in new_relations:
        print(f"    {name:20s}: {formula}")
        print(f"    {'':20s}  → {interpretation}\n")

    return predictions, new_relations


# ═══════════════════════════════════════════════════════════
# Deep Explorer
# ═══════════════════════════════════════════════════════════

def deep_explore(n: int = 6, max_discoveries: int = 50):
    """심층 탐색: 2차/3차 조합에서 새로운 항등식 발견."""
    print(f"\n  ═══ Deep Exploration: n={n} ═══\n")
    print(f"  τ={tau(n)}, σ={sigma(n)}, φ={euler_phi(n)}, "
          f"ω={omega(n)}, sopfr={sopfr(n)}, μ={mobius(n)}, ψ={dedekind_psi(n)}")
    print(f"  Perfect: {'YES' if is_perfect(n) else 'NO'}, "
          f"Abundancy: {abundancy(n)}\n")

    # Find all equalities
    discoveries = find_equalities(n)
    print(f"  Found {len(discoveries)} equalities at n={n}")

    # Filter interesting ones (not trivial like n=n)
    interesting = []
    for d in discoveries:
        # Skip if both sides are the same function
        if d.lhs.split('(')[0] == d.rhs.split('(')[0]:
            continue
        # Skip if value is 0 or 1 (trivial)
        if d.value in (0, 1):
            continue
        interesting.append(d)

    print(f"  Interesting (non-trivial): {len(interesting)}")

    # Check uniqueness
    print(f"  Checking unique-to-{n}...\n")
    unique_count = 0
    for d in interesting[:max_discoveries]:
        d.unique_to_6 = check_unique_to_n(d, n, range(2, 100))
        if d.unique_to_6:
            unique_count += 1
            d.significance = '⭐'
            print(f"    ⭐ UNIQUE: {d.formula} = {d.value}")
        else:
            d.significance = '⬛'

    print(f"\n  Unique-to-{n}: {unique_count}/{min(len(interesting), max_discoveries)}")

    # Known important values
    important_values = {
        2: 'σ/n (perfect number ratio), Dedekind ratio',
        3: 'σ/τ (theta-gamma coupling)',
        4: 'τ (binding phases, DNA bases)',
        5: 'sopfr (telepathy channels)',
        6: 'n itself',
        7: 'τ+σ/τ (Miller\'s magic number)',
        8: 'σ-τ (attention heads)',
        10: 'sopfr×φ (bp/turn)',
        12: 'σ (divisor sum)',
        24: 'σ×φ (shared dims)',
        64: 'φ^n (DNA codons)',
        120: 'σ⁴(6)=5! (factorial evolution)',
    }

    print(f"\n  ═══ Important Value Matches ═══\n")
    for d in interesting:
        int_val = int(d.value) if d.value == int(d.value) else None
        if int_val and int_val in important_values:
            marker = '⭐' if d.unique_to_6 else '🟩'
            print(f"    {marker} {d.formula} = {int_val} ({important_values[int_val]})")

    return interesting


# ═══════════════════════════════════════════════════════════
# Scanner
# ═══════════════════════════════════════════════════════════

def scan_range(start: int, end: int):
    """범위 내 모든 n에서 흥미로운 성질 스캔."""
    print(f"\n  ═══ Scanning n={start}..{end} ═══\n")
    print(f"  {'n':>4} {'τ':>3} {'σ':>4} {'φ':>3} {'ω':>2} {'sopfr':>5} {'σ/n':>5} {'Perfect':>7}")
    print(f"  {'─'*4} {'─'*3} {'─'*4} {'─'*3} {'─'*2} {'─'*5} {'─'*5} {'─'*7}")

    perfects = []
    for n in range(start, end + 1):
        t, s, p, om, sp = tau(n), sigma(n), euler_phi(n), omega(n), sopfr(n)
        perf = '★' if is_perfect(n) else ''
        if is_perfect(n):
            perfects.append(n)
        ratio = f"{s/n:.2f}"
        print(f"  {n:>4} {t:>3} {s:>4} {p:>3} {om:>2} {sp:>5} {ratio:>5} {perf:>7}")

    if perfects:
        print(f"\n  Perfect numbers found: {perfects}")


# ═══════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Anima Math Explorer — n=6 수학적 의식 관계 탐색")
    parser.add_argument('--n', type=int, default=6, help='Number to explore')
    parser.add_argument('--consciousness', action='store_true', help='Explore consciousness variable relations')
    parser.add_argument('--verify', type=str, help='Verify a specific formula')
    parser.add_argument('--scan', nargs=2, type=int, help='Scan range (start end)')
    parser.add_argument('--deep', action='store_true', help='Deep exploration (2nd/3rd order)')
    parser.add_argument('--max', type=int, default=50, help='Max discoveries to check')
    args = parser.parse_args()

    if args.consciousness:
        explore_consciousness_relations()

    elif args.verify:
        print(f"\n  Verifying: {args.verify}")
        # Try to evaluate both sides
        parts = args.verify.split('=')
        if len(parts) == 2:
            lhs = eval_expr(parts[0].strip(), args.n)
            rhs = eval_expr(parts[1].strip(), args.n)
            print(f"  At n={args.n}: LHS={lhs}, RHS={rhs}")
            if lhs is not None and rhs is not None:
                if abs(lhs - rhs) < 1e-10:
                    print(f"  ✅ VERIFIED: {parts[0].strip()} = {parts[1].strip()} = {lhs}")
                else:
                    print(f"  ❌ FAILED: {lhs} ≠ {rhs} (diff={abs(lhs-rhs):.6f})")

    elif args.scan:
        scan_range(args.scan[0], args.scan[1])

    elif args.deep:
        deep_explore(args.n, max_discoveries=args.max)

    else:
        # Default: show n=6 properties + quick explore
        n = args.n
        print(f"\n  ═══ n={n} Properties ═══\n")
        print(f"  τ(n)    = {tau(n):>4}  (divisor count)")
        print(f"  σ(n)    = {sigma(n):>4}  (divisor sum)")
        print(f"  φ(n)    = {euler_phi(n):>4}  (Euler totient)")
        print(f"  ω(n)    = {omega(n):>4}  (distinct prime factors)")
        print(f"  sopfr(n)= {sopfr(n):>4}  (sum of prime factors)")
        print(f"  μ(n)    = {mobius(n):>4}  (Möbius)")
        print(f"  ψ(n)    = {dedekind_psi(n):>4}  (Dedekind psi)")
        print(f"  σ/n     = {sigma(n)/n:>4.1f}  (abundancy)")
        print(f"  Perfect = {'YES ★' if is_perfect(n) else 'no'}")

        print()
        explore_consciousness_relations()

        print("\n  Use --deep for full exploration, --scan 1 30 for range scan")


if __name__ == '__main__':
    main()
