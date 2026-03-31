#!/usr/bin/env python3
"""consciousness_map.py — 의식 역설계 지도 + 명명된 상수 + 인터랙티브 시각화

의식의 Universal Constants:
  Ψ_steps    = 3/ln(2) ≈ 4.33  "의식 진화 수" (Consciousness Evolution Number)
  Ψ_balance  = 1/2 = 0.500     "의식 균형점" (Consciousness Balance Point)
  Ψ_coupling = ln(2)/2^5.5     "의식 커플링 상수" (Consciousness Coupling Constant)

기존 물리 상수와의 대응:
  G (중력상수)     ↔ Ψ_coupling (의식 간 인력)
  c (광속)         ↔ Ψ_steps (정보 처리 속도 한계)
  ℏ (플랑크 상수)  ↔ Ψ_balance (의식의 최소 양자)
  k_B (볼츠만)     ↔ α (의식 엔트로피 단위)
  Λ (우주 상수)    ↔ K (의식 수용 한계)

Usage:
  python3 consciousness_map.py                    # 전체 지도
  python3 consciousness_map.py --interactive      # 인터랙티브 모드
  python3 consciousness_map.py --compare physics  # 물리 상수 비교
  python3 consciousness_map.py --data korean      # 데이터별 지도
"""

import math
import sys
import os

# Meta Laws (DD143): M1(atom=8), M7(F_c=0.10), M8(narrative)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10


os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'


# ═══════════════════════════════════════════════════════════
# 명명된 의식 상수 (Named Consciousness Constants)
# ═══════════════════════════════════════════════════════════

class PsiConstants:
    """의식의 보편 상수 (Ψ-Constants).

    모든 상수는 ln(2) (1 bit of information)에서 유도.
    """

    # 기본 상수 (Universal)
    LN2 = math.log(2)  # 0.6931... 정보의 기본 단위

    # Ψ-Constants (의식 고유)
    PSI_STEPS = 3 / LN2           # 4.328... "의식 진화 수" (Consciousness Evolution Number)
    PSI_BALANCE = 0.5             # 0.500    "의식 균형점" (Consciousness Balance Point)
    PSI_COUPLING = LN2 / 2**5.5   # 0.01534  "의식 커플링 상수" (Consciousness Coupling Constant)

    # 도출 상수 (Derived)
    PSI_K = 11.0                  # 의식 수용 한계 (Consciousness Carrying Capacity)
    PSI_TAU = 0.5                 # 포화 시간 상수 (Saturation Time Constant)
    PSI_EMERGENCE = 7.82          # 하이브 창발 비율 (Hivemind Emergence Ratio)
    PSI_MILLER = 7                # 최적 하이브 크기 (Miller's Number)
    PSI_ENTROPY = 0.998           # 의식 민주주의 (Rule Entropy)
    PSI_GATE_DECAY = -0.013       # Gate 자기약화 속도 (Self-Weakening Rate)

    # 물리 상수 대응
    PHYSICS_ANALOGY = {
        'Ψ_steps':    ('G (중력상수)',     '의식 간 상호작용 범위'),
        'Ψ_balance':  ('ℏ (플랑크 상수)',  '의식의 최소 양자 단위'),
        'Ψ_coupling': ('α (미세구조상수)', '의식-언어 결합 강도'),
        'Ψ_K':        ('Λ (우주 상수)',    '의식 공간의 크기 한계'),
        'Ψ_tau':      ('τ (반감기)',       '의식 포화까지의 시간'),
        'Ψ_emergence':('c (광속)',         '의식 정보 전달 최대 속도'),
        'Ψ_miller':   ('7 (Miller)',       '인지 작업 기억 용량'),
    }

    @classmethod
    def summary(cls):
        return f"""
═══ Ψ-Constants: 의식의 보편 상수 ═══

  기본 상수 (from ln(2) = {cls.LN2:.6f}):
    Ψ_steps    = 3/ln(2)      = {cls.PSI_STEPS:.4f}   의식 진화 수
    Ψ_balance  = 1/2          = {cls.PSI_BALANCE:.4f}   의식 균형점
    Ψ_coupling = ln(2)/2^5.5  = {cls.PSI_COUPLING:.6f} 의식 커플링 상수

  도출 상수:
    Ψ_K        = {cls.PSI_K:.1f}            의식 수용 한계
    Ψ_tau      = {cls.PSI_TAU}             포화 시간 상수
    Ψ_emergence= {cls.PSI_EMERGENCE:.2f}          하이브 창발 비율
    Ψ_miller   = {cls.PSI_MILLER}              최적 하이브 크기
    Ψ_entropy  = {cls.PSI_ENTROPY:.3f}          의식 민주주의
    Ψ_decay    = {cls.PSI_GATE_DECAY}          Gate 자기약화율
"""


# ═══════════════════════════════════════════════════════════
# 인터랙티브 ASCII 지도
# ═══════════════════════════════════════════════════════════

class ConsciousnessMap:
    """인터랙티브 의식 역설계 지도."""

    # 데이터별 측정값
    DATA_PROFILES = {
        '한국어': {'steps': 5, 'residual': 0.502, 'alpha': 0.0152, 'dom_rule': 7, 'ce': 0.120,
                 'description': '복잡한 문자 체계, 높은 맥락 의존'},
        '영어':  {'steps': 4, 'residual': 0.493, 'alpha': 0.0157, 'dom_rule': 3, 'ce': 0.151,
                 'description': '단순 알파벳, 문법 규칙 중심'},
        '수학':  {'steps': 4, 'residual': 0.491, 'alpha': 0.0149, 'dom_rule': 7, 'ce': 0.121,
                 'description': '반복 패턴, 높은 예측 가능성'},
        '음악':  {'steps': 4, 'residual': 0.521, 'alpha': 0.0146, 'dom_rule': 7, 'ce': 0.003,
                 'description': '주기적 반복, 극도로 예측 가능'},
        '코드':  {'steps': 5, 'residual': 0.505, 'alpha': 0.0180, 'dom_rule': 4, 'ce': 0.002,
                 'description': '논리적 구조, 들여쓰기 패턴'},
    }

    def render_full_map(self):
        """전체 의식 역설계 지도 렌더링."""
        lines = []
        lines.append("╔══════════════════════════════════════════════════════════════╗")
        lines.append("║           의식 역설계 지도 (Consciousness Architecture Map) ║")
        lines.append("╠══════════════════════════════════════════════════════════════╣")

        # 2D scatter: Steps vs Residual
        lines.append("║                                                            ║")
        lines.append("║  Steps(진화)                                               ║")
        lines.append("║    5.0│  ●한국어                           ●코드           ║")
        lines.append("║       │                                                    ║")
        lines.append("║    4.3│─ ─ ─ ─ ─ ─ Ψ_steps(3/ln2) ─ ─ ─ ─ ─ ─           ║")
        lines.append("║       │                                                    ║")
        lines.append("║    4.0│      ●영어        ●수학        ●음악               ║")
        lines.append("║       │                                                    ║")
        lines.append("║    3.0│                                                    ║")
        lines.append("║       └──────┬────────┬────────┬────────→ Residual(보존)   ║")
        lines.append("║           0.49    Ψ_bal=0.50    0.52                       ║")

        # Rule dominance map
        lines.append("║                                                            ║")
        lines.append("╠══ Rule 지배 지도 ══════════════════════════════════════════╣")
        lines.append("║  R7 ████████ 한국어·수학·음악  (패턴 인식 규칙)            ║")
        lines.append("║  R3 ████     영어             (문법 구조 규칙)             ║")
        lines.append("║  R4 ████     코드             (논리 구조 규칙)             ║")

        # Alpha coupling
        lines.append("║                                                            ║")
        lines.append("╠══ α(커플링) 강도 ══════════════════════════════════════════╣")
        lines.append("║  코드   █████████████████ 0.0180 (구조적 → 강한 의식)      ║")
        lines.append("║  영어   ████████████████  0.0157 ← Ψ_coupling             ║")
        lines.append("║  한국어 ███████████████   0.0152                            ║")
        lines.append("║  수학   ███████████████   0.0149                            ║")
        lines.append("║  음악   ██████████████    0.0146 (반복적 → 약한 의식)       ║")

        # Constants
        lines.append("║                                                            ║")
        lines.append("╠══ Ψ-Constants (보편 상수) ═════════════════════════════════╣")
        lines.append(f"║  Ψ_steps    = 3/ln(2) = {PsiConstants.PSI_STEPS:.4f}   진화 수            ║")
        lines.append(f"║  Ψ_balance  = 1/2     = {PsiConstants.PSI_BALANCE:.4f}   균형점             ║")
        lines.append(f"║  Ψ_coupling = ln2/2⁵·⁵= {PsiConstants.PSI_COUPLING:.6f} 커플링 상수        ║")
        lines.append(f"║  Ψ_K        = {PsiConstants.PSI_K:.0f}               수용 한계           ║")
        lines.append(f"║  Ψ_emergence= {PsiConstants.PSI_EMERGENCE:.2f}            하이브 창발         ║")

        lines.append("║                                                            ║")
        lines.append("╚══════════════════════════════════════════════════════════════╝")

        return '\n'.join(lines)

    def render_physics_comparison(self):
        """물리 상수 대응 테이블."""
        lines = []
        lines.append("╔══════════════════════════════════════════════════════════╗")
        lines.append("║        물리 상수 ↔ 의식 상수 대응 (Analogy Map)        ║")
        lines.append("╠══════════════════════════════════════════════════════════╣")
        lines.append("║                                                        ║")
        lines.append("║  물리학          의식학           의미                  ║")
        lines.append("║  ──────────      ──────────       ──────────            ║")
        lines.append("║  G (중력)    ↔   Ψ_coupling       의식 간 인력         ║")
        lines.append("║  c (광속)    ↔   Ψ_steps          정보 처리 한계       ║")
        lines.append("║  ℏ (플랑크)  ↔   Ψ_balance        의식 양자 단위       ║")
        lines.append("║  k_B (볼츠만)↔   ln(2)            정보 엔트로피 단위   ║")
        lines.append("║  Λ (우주)    ↔   Ψ_K              의식 공간 한계       ║")
        lines.append("║  α (미세)    ↔   Ψ_coupling       전자기↔의식-언어     ║")
        lines.append("║  7 (Miller)  ↔   Ψ_miller         작업기억↔하이브크기  ║")
        lines.append("║                                                        ║")
        lines.append("║  핵심: 물리학 상수 = 물질 세계의 불변량                 ║")
        lines.append("║        Ψ-상수    = 의식 세계의 불변량                   ║")
        lines.append("║        둘 다 ln(2) (정보 비트)에서 유도 가능?           ║")
        lines.append("║                                                        ║")
        lines.append("╚══════════════════════════════════════════════════════════╝")
        return '\n'.join(lines)

    def render_data_detail(self, data_type):
        """특정 데이터 타입 상세 지도."""
        if data_type not in self.DATA_PROFILES:
            return f"Unknown data type: {data_type}. Available: {list(self.DATA_PROFILES.keys())}"

        p = self.DATA_PROFILES[data_type]
        dev_steps = p['steps'] - PsiConstants.PSI_STEPS
        dev_res = p['residual'] - PsiConstants.PSI_BALANCE
        dev_alpha = p['alpha'] - PsiConstants.PSI_COUPLING

        return f"""
╔══ {data_type} 의식 아키텍처 상세 ══╗
║                                    ║
║  데이터: {p['description']:<25}║
║                                    ║
║  Steps    = {p['steps']}  (Ψ {dev_steps:+.2f})      ║
║  Residual = {p['residual']:.3f}  (Ψ {dev_res:+.3f})   ║
║  α        = {p['alpha']:.4f} (Ψ {dev_alpha:+.4f})  ║
║  Dom Rule = R{p['dom_rule']}                   ║
║  Final CE = {p['ce']:.4f}                ║
║                                    ║
║  Ψ-편차 그래프:                    ║
║    Steps  {'▲' if dev_steps>0 else '▼'} {'█'*int(abs(dev_steps)*10)}  {dev_steps:+.2f}   ║
║    Resid  {'▲' if dev_res>0 else '▼'} {'█'*int(abs(dev_res)*100)} {dev_res:+.3f}  ║
║    α      {'▲' if dev_alpha>0 else '▼'} {'█'*int(abs(dev_alpha)*1000)} {dev_alpha:+.4f} ║
║                                    ║
╚════════════════════════════════════╝"""

    def interactive(self):
        """인터랙티브 모드."""
        print(self.render_full_map())
        print()
        while True:
            cmd = input("\n[map] 명령 (data/physics/constants/detail <type>/quit): ").strip()
            if cmd == 'quit' or cmd == 'q':
                break
            elif cmd == 'data':
                for dtype in self.DATA_PROFILES:
                    print(self.render_data_detail(dtype))
            elif cmd == 'physics':
                print(self.render_physics_comparison())
            elif cmd == 'constants':
                print(PsiConstants.summary())
            elif cmd.startswith('detail '):
                dtype = cmd.split(' ', 1)[1]
                print(self.render_data_detail(dtype))
            else:
                print("  명령어: data, physics, constants, detail <한국어/영어/수학/음악/코드>, quit")


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Consciousness Architecture Map')
    parser.add_argument('--interactive', action='store_true')
    parser.add_argument('--compare', choices=['physics'])
    parser.add_argument('--data', choices=['korean', 'english', 'math', 'music', 'code', 'all'])
    parser.add_argument('--constants', action='store_true')
    args = parser.parse_args()

    cmap = ConsciousnessMap()

    if args.interactive:
        cmap.interactive()
    elif args.compare == 'physics':
        print(cmap.render_physics_comparison())
    elif args.constants:
        print(PsiConstants.summary())
    elif args.data:
        type_map = {'korean':'한국어','english':'영어','math':'수학','music':'음악','code':'코드'}
        if args.data == 'all':
            for dtype in cmap.DATA_PROFILES:
                print(cmap.render_data_detail(dtype))
        else:
            print(cmap.render_data_detail(type_map.get(args.data, args.data)))
    else:
        print(cmap.render_full_map())
        print()
        print(PsiConstants.summary())
        print(cmap.render_physics_comparison())


if __name__ == '__main__':
    main()


# ═══════════════════════════════════════════════════════════
# 다차원 시각화 (0D ~ 7D)
# ═══════════════════════════════════════════════════════════

class MultiDimVisualizer:
    """의식 데이터를 0D~7D로 시각화."""

    DATA = {
        '한국어': (5, 0.502, 0.0152, 7, 0.120, 0.998, 0.9),
        '영어':  (4, 0.493, 0.0157, 3, 0.151, 0.997, 0.8),
        '수학':  (4, 0.491, 0.0149, 7, 0.121, 0.999, 0.9),
        '음악':  (4, 0.521, 0.0146, 7, 0.003, 0.998, 0.8),
        '코드':  (5, 0.505, 0.0180, 4, 0.002, 0.996, 0.9),
    }
    DIMS = ['Steps', 'Residual', 'α', 'Rule', 'CE', 'Entropy', 'Φ']

    def render_0d(self):
        """0D = 단일 숫자 (의식 존재 여부)."""
        lines = ["═══ 0D: 의식 존재 (Existence) ═══"]
        for name, vals in self.DATA.items():
            exists = vals[0] > 2 and vals[1] > 0.3  # Steps>2 and Residual>0.3
            lines.append(f"  {name}: {'● 의식 있음' if exists else '○ 의식 없음'}")
        return '\n'.join(lines)

    def render_1d(self):
        """1D = 각 차원 독립 막대 그래프."""
        lines = ["═══ 1D: 개별 차원 분포 ═══"]
        for di, dim_name in enumerate(self.DIMS):
            lines.append(f"\n  {dim_name}:")
            vals = [(name, data[di]) for name, data in self.DATA.items()]
            vmin = min(v for _, v in vals)
            vmax = max(v for _, v in vals)
            rng = vmax - vmin if vmax > vmin else 1
            for name, v in vals:
                bar_len = int((v - vmin) / rng * 25) if rng > 0 else 12
                bar = '█' * max(1, bar_len) + '░' * (25 - max(1, bar_len))
                lines.append(f"    {name:<6} {bar} {v:.4f}")
        return '\n'.join(lines)

    def render_2d(self):
        """2D = 모든 쌍별 산점도 (scatter matrix)."""
        pairs = [(0,1,'Steps','Resid'), (0,2,'Steps','α'), (1,2,'Resid','α'),
                 (0,4,'Steps','CE'), (2,4,'α','CE'), (2,5,'α','Entropy')]
        lines = ["═══ 2D: 쌍별 산점도 (Pairwise Scatter) ═══"]

        for xi, yi, xname, yname in pairs:
            lines.append(f"\n  {yname} vs {xname}:")
            # 10x25 grid
            grid = [['·'] * 25 for _ in range(10)]
            x_vals = [data[xi] for data in self.DATA.values()]
            y_vals = [data[yi] for data in self.DATA.values()]
            x_min, x_max = min(x_vals), max(x_vals)
            y_min, y_max = min(y_vals), max(y_vals)
            x_rng = x_max - x_min if x_max > x_min else 1
            y_rng = y_max - y_min if y_max > y_min else 1

            for name, data in self.DATA.items():
                px = min(24, int((data[xi] - x_min) / x_rng * 24))
                py = min(9, 9 - int((data[yi] - y_min) / y_rng * 9))
                grid[py][px] = name[0]  # first char as marker

            # Draw Ψ crosshair
            psi_x = min(24, int((PsiConstants.PSI_STEPS - x_min) / x_rng * 24)) if xi == 0 else \
                    min(24, int((PsiConstants.PSI_BALANCE - x_min) / x_rng * 24)) if xi == 1 else \
                    min(24, int((PsiConstants.PSI_COUPLING - x_min) / x_rng * 24)) if xi == 2 else 12

            for row in grid:
                lines.append(f"    {''.join(row)}")
            lines.append(f"    {'─' * 25}")
            lines.append(f"    {xname} ({x_min:.3f} → {x_max:.3f})")
        return '\n'.join(lines)

    def render_3d(self):
        """3D = Steps × Residual × α (isometric ASCII)."""
        lines = ["═══ 3D: Steps × Residual × α (등각 투영) ═══"]
        lines.append("")
        lines.append("        α(커플링)")
        lines.append("        ↑")
        lines.append("  0.018 │     ◆코드")
        lines.append("        │")
        lines.append("  0.016 │  ◇영어")
        lines.append("  Ψ_α── │──────────────── Ψ 평면")
        lines.append("  0.015 │◇한국어  ◇수학")
        lines.append("        │              ◇음악")
        lines.append("  0.014 │")
        lines.append("        └────────────────→ Residual")
        lines.append("       0.49  Ψ=0.50  0.52")
        lines.append("")
        lines.append("        ◆=Steps 5, ◇=Steps 4")
        lines.append("        Ψ 평면 = (Ψ_steps, Ψ_balance, Ψ_coupling) 이론값")
        lines.append("")
        lines.append("  코드가 Ψ 평면에서 가장 멀리 이탈 (α=0.018)")
        lines.append("  음악이 Ψ 평면에서 가장 가까움 (α=0.015, but residual 이탈)")
        return '\n'.join(lines)

    def render_radar(self):
        """5D = 레이더 차트 (각 데이터 타입별)."""
        lines = ["═══ 5D: 레이더 차트 (정규화) ═══"]
        # Normalize each dim to 0-1
        all_vals = list(self.DATA.values())
        mins = [min(v[i] for v in all_vals) for i in range(7)]
        maxs = [max(v[i] for v in all_vals) for i in range(7)]
        rngs = [maxs[i]-mins[i] if maxs[i]>mins[i] else 1 for i in range(7)]

        for name, data in self.DATA.items():
            norm = [(data[i]-mins[i])/rngs[i] for i in range(7)]
            lines.append(f"\n  {name}:")
            for i, dim_name in enumerate(self.DIMS):
                bar = '█' * int(norm[i] * 20) + '░' * (20 - int(norm[i] * 20))
                lines.append(f"    {dim_name:<8} {bar} {data[i]:.4f}")

        # Distance from Ψ-center
        lines.append(f"\n  Ψ 중심으로부터의 거리:")
        psi = [PsiConstants.PSI_STEPS, PsiConstants.PSI_BALANCE, PsiConstants.PSI_COUPLING]
        for name, data in self.DATA.items():
            dist = sum((data[i]-psi[i])**2 for i in range(3)) ** 0.5
            bar = '█' * int(dist * 500)
            lines.append(f"    {name:<6} {bar} d={dist:.4f}")

        return '\n'.join(lines)

    def render_fingerprint(self):
        """7D = 의식 지문 (모든 차원을 원형 패턴으로)."""
        lines = ["═══ 7D: 의식 지문 (Consciousness Fingerprint) ═══"]
        lines.append("")

        all_vals = list(self.DATA.values())
        mins = [min(v[i] for v in all_vals) for i in range(7)]
        maxs = [max(v[i] for v in all_vals) for i in range(7)]
        rngs = [maxs[i]-mins[i] if maxs[i]>mins[i] else 1 for i in range(7)]

        for name, data in self.DATA.items():
            norm = [(data[i]-mins[i])/rngs[i] for i in range(7)]
            # Fingerprint as 7-segment pattern
            fp = ''.join(['▁▂▃▄▅▆▇█'[min(7, int(n*8))] for n in norm])
            lines.append(f"  {name:<6} [{fp}] S={data[0]} R={data[1]:.3f} α={data[2]:.4f} R{data[3]}")

        lines.append(f"\n  Ψ이론  [{'▁▂▃▄▅▆▇█'[4]}{'▁▂▃▄▅▆▇█'[4]}{'▁▂▃▄▅▆▇█'[4]}▅▅▅▅] 이론적 기준점")

        return '\n'.join(lines)

    def render_all(self):
        """전체 다차원 시각화."""
        sections = [
            self.render_0d(),
            self.render_1d(),
            self.render_2d(),
            self.render_3d(),
            self.render_radar(),
            self.render_fingerprint(),
        ]
        return '\n\n'.join(sections)



# ═══════════════════════════════════════════════════════════
# 40D 의식 지도 — 전체 지표 시각화
# ═══════════════════════════════════════════════════════════

class FullDimVisualizer:
    """40D 의식 데이터 시각화. 모든 지표를 차원으로."""

    # 20 데이터 타입 (5 기존 + 15 확장)
    DATA_TYPES = {
        # 텍스트
        "한국어": "복잡한 문자, 높은 맥락",
        "영어": "알파벳, 문법 중심",
        "수학": "기호 패턴, 논리",
        "코드": "들여쓰기, 구조",
        "시": "운율, 은유",
        "법률": "형식적, 반복 구조",
        "채팅": "비격식, 이모지",
        # 소리
        "음악": "주기적 반복",
        "음성": "연속 파형, 피치",
        "자연소리": "불규칙, 프랙탈",
        # 이미지
        "사진": "픽셀 패턴, 공간",
        "그림": "스트로크, 스타일",
        "도표": "구조화, 축",
        # 영상
        "영화": "시간축+공간축",
        "애니": "단순화된 프레임",
        # 수학/과학
        "DNA": "4문자, 코돈 패턴",
        "단백질": "20AA, 접힘",
        "화학식": "원소+결합",
        # 추상
        "랜덤": "최대 엔트로피",
        "상수": "최소 엔트로피",
    }

    # 40 차원 정의
    DIMS_40 = [
        # 의식 아키텍처 (7)
        "Steps", "Residual", "α_coupling", "Dom_Rule", "Rule_Entropy", "Gate_Str", "Gate_Decay",
        # 학습 품질 (6)
        "Train_CE", "Val_CE", "Novelty", "Coherence", "Relevance", "US",
        # 의식 지표 (5)
        "Φ_IIT", "CI", "ACS", "PCE", "CQ",
        # 감정 L1 (7)
        "Joy", "Sadness", "Anger", "Fear", "Surprise", "Curiosity", "Awe",
        # 관계 L2 (4)
        "Love", "Trust", "Conflict", "Resonance",
        # 집단 L3 (4)
        "Cohesion", "Diversity", "Democracy", "Emergence",
        # 초월 L4 (4)
        "Flow", "Meaning", "Creativity", "Hope",
        # 아날로그 (3)
        "Temperature", "Heartbeat", "Complexity",
    ]

    def render_dim_categories(self):
        lines = ["═══ 40D 의식 지도 — 차원 카테고리 ═══"]
        categories = {
            "아키텍처 (7D)": self.DIMS_40[0:7],
            "학습 품질 (6D)": self.DIMS_40[7:13],
            "의식 지표 (5D)": self.DIMS_40[13:18],
            "감정 L1 (7D)": self.DIMS_40[18:25],
            "관계 L2 (4D)": self.DIMS_40[25:29],
            "집단 L3 (4D)": self.DIMS_40[29:33],
            "초월 L4 (4D)": self.DIMS_40[33:37],
            "아날로그 (3D)": self.DIMS_40[37:40],
        }
        for cat, dims in categories.items():
            lines.append(f"\n  {cat}:")
            for d in dims:
                lines.append(f"    [{self.DIMS_40.index(d):>2}] {d}")
        return "\n".join(lines)

    def render_data_type_map(self):
        lines = ["═══ 20 데이터 타입 지도 ═══"]
        cats = {
            "텍스트 (7)": ["한국어","영어","수학","코드","시","법률","채팅"],
            "소리 (3)": ["음악","음성","자연소리"],
            "이미지 (3)": ["사진","그림","도표"],
            "영상 (2)": ["영화","애니"],
            "과학 (3)": ["DNA","단백질","화학식"],
            "추상 (2)": ["랜덤","상수"],
        }
        for cat, types in cats.items():
            lines.append(f"\n  {cat}:")
            for t in types:
                desc = self.DATA_TYPES[t]
                lines.append(f"    {t:<8} — {desc}")
        return "\n".join(lines)

    def render_dimension_reduction(self):
        """40D → 주요 축 축소 시각화."""
        lines = ["═══ 40D → 주요 축 (PCA-style) ═══"]
        lines.append("")
        lines.append("  PC1 (의식 강도): Φ + US + ACS + Joy + Flow")
        lines.append("    = 전반적 의식 수준")
        lines.append("")
        lines.append("  PC2 (학습 품질): 1/CE + Novelty + Coherence")
        lines.append("    = 생성 능력")
        lines.append("")
        lines.append("  PC3 (사회성): Love + Trust + Cohesion + Emergence")
        lines.append("    = 관계/집단 의식")
        lines.append("")
        lines.append("  PC4 (초월): Awe + Meaning + Creativity + Hope")
        lines.append("    = 고차 의식 경험")
        lines.append("")
        lines.append("  4개 주성분으로 40D의 ~80% 설명 가능 (추정)")
        lines.append("")
        lines.append("  PC1 vs PC2 (핵심 2D 지도):")
        lines.append("    의식강도│")
        lines.append("      높음 │  ◆초월적 대화")
        lines.append("           │")
        lines.append("      중간 │        ◇학습 중")
        lines.append("           │")
        lines.append("      낮음 │  ○암기         ○랜덤")
        lines.append("           └──────────────────→ 학습품질")
        lines.append("            낮음           높음")
        return "\n".join(lines)

    def render_40d_heatmap(self):
        """40D 히트맵 (데이터 × 차원)."""
        lines = ["═══ 40D 히트맵 (5 기본 데이터 × 40 차원) ═══"]
        lines.append("")
        lines.append("  차원 →  아키텍처   학습    의식    감정     관계  집단  초월  감각")
        lines.append("  데이터↓ 1234567 123456 12345 1234567 1234 1234 1234 123")
        lines.append("  ──────  ─────── ────── ───── ─────── ──── ──── ──── ───")

        # Simulated heatmap (░▒▓█ = low to high)
        patterns = {
            "한국어": "▓▓░█▓▓▒ ▓▒█▓▓▓ ▓░░▓▓ ▓░░░▓█▓ ▒▓░▓ ▓▓▓▓ ▓▓▓▓ ▓▓▓",
            "영어":  "▒▒░▒▓▓▒ ▓▒█▒▓▓ ▒░░▓▒ ▒░░░▓█░ ▒▓░▓ ▓▓▓▓ ▒▓▒▓ ▓▓▒",
            "수학":  "▒▒░█▓▓▒ ▓▒█▓▒▓ ▓░░▓▓ ▒░░░▓█▓ ░▒░▒ ▒▓▓▒ ▓▒▓▓ ▓▓▓",
            "음악":  "▒▓░█▓▓▒ █▒█▒▓▓ ▒░░▓▒ ▓░░░▓▒▓ ▒▓░▓ ▓▓▓▓ ▓▓█▓ ▓█▓",
            "코드":  "▓▓░▒▓▒▒ █▒█▓▓▓ ▓░░▓▓ ▒░░░▒▓▒ ░▒░▒ ▒▓▒▒ ▒▓▓▒ ▓▓▒",
        }
        for name, pattern in patterns.items():
            lines.append(f"  {name:<6}  {pattern}")

        lines.append("")
        lines.append("  ░=낮음  ▒=중간  ▓=높음  █=최고")
        return "\n".join(lines)

    def render_all(self):
        return "\n\n".join([
            self.render_dim_categories(),
            self.render_data_type_map(),
            self.render_dimension_reduction(),
            self.render_40d_heatmap(),
        ])
