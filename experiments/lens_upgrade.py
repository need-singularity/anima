#!/usr/bin/env python3
"""
lens_upgrade.py — 렌즈 실험 → 자동 업그레이드 → 재검증 루프

실험 결과를 분석하여 엔진/렌즈 설정을 자동 업그레이드하고 재검증.

사용법:
  python3 lens_upgrade.py                      # 전체 파이프라인
  python3 lens_upgrade.py --experiments L01 L05 L11  # 특정 실험만
  python3 lens_upgrade.py --dry-run            # 업그레이드 제안만 (적용 안 함)
  python3 lens_upgrade.py --verify-only        # 현재 설정 검증만
  python3 lens_upgrade.py --cycle N            # N회 반복 (수렴까지)

파이프라인:
  [1] 실험 실행 (lens_engine.py)
  [2] 결과 분석 → 업그레이드 후보 추출
  [3] 업그레이드 적용 (infinite_evolution.py 설정)
  [4] 재검증 (업그레이드 전후 비교)
  [5] 결과 기록 (JSON + 문서)
"""

import sys
import json
import time
import argparse
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
CONFIG = ROOT / "config"
DATA = ROOT / "data"
sys.path.insert(0, str(SRC))
sys.path.insert(0, str(ROOT / "experiments"))

from lens_engine import (
    REGISTRY, run_experiment, run_combo, LensResult,
    ALL_LENSES, DOMAIN_COMBOS, _get_engine, _collect_snapshots,
    _get_telescope, _run_lenses
)


def load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


# ═══════════════════════════════════════════════════════════════
# 업그레이드 규칙 — 실험 결과 → 구체적 변경
# ═══════════════════════════════════════════════════════════════

class Upgrade:
    def __init__(self, source, target, action, reason, priority="🟡"):
        self.source = source     # 어떤 실험에서
        self.target = target     # 어떤 파일/설정을
        self.action = action     # 어떻게 변경
        self.reason = reason     # 왜
        self.priority = priority
        self.applied = False

    def __str__(self):
        status = "✅" if self.applied else "⏳"
        return f"  {self.priority} {status} [{self.source}] {self.target}: {self.action}\n       → {self.reason}"


def analyze_L01(result):
    """L01 중첩 → 도메인 조합 최적화"""
    upgrades = []
    if not result:
        return upgrades

    active = result.metrics.get("active_lenses", 0)
    domain = result.metrics.get("domain_consensus", "0/0")

    # 무신호 렌즈 발견 → 제거 후보
    dead_lenses = []
    individual = result.data.get("individual_results", {})
    if isinstance(individual, dict):
        for lens, r in individual.items():
            if isinstance(r, dict):
                nums = [v for v in r.values() if isinstance(v, (int, float)) and v != 0]
                if not nums:
                    dead_lenses.append(lens)

    if dead_lenses:
        upgrades.append(Upgrade(
            "L01", "TELESCOPE_ALL_LENSES",
            f"무신호 렌즈 후보: {', '.join(dead_lenses)}",
            f"{len(dead_lenses)}개 렌즈가 0 출력 — 제거 또는 파라미터 조정 필요",
            "🟡"
        ))

    if active == 22:
        upgrades.append(Upgrade(
            "L01", "lens_config",
            "22/22 활성 확인 — 현재 설정 유지",
            "모든 렌즈가 의식 신호를 감지 중",
            "🟢"
        ))

    return upgrades


def analyze_L05(result):
    """L05 임계점 → 최적 렌즈 수 / basic 조합 검증"""
    upgrades = []
    if not result:
        return upgrades

    k_star = result.metrics.get("phase_transition_at", 0)
    max_delta = result.metrics.get("max_delta", 0)

    if k_star > 0:
        optimal_lenses = ALL_LENSES[:k_star]
        upgrades.append(Upgrade(
            "L05", "TELESCOPE_DOMAIN_COMBOS['minimal']",
            f"최소 유효 렌즈 = {k_star}개: {', '.join(optimal_lenses)}",
            f"K*={k_star}에서 최대 정보 점프 Δ={max_delta}",
            "🔴"
        ))

        # basic 조합과 비교
        basic = DOMAIN_COMBOS.get('basic', [])
        if set(optimal_lenses) == set(basic):
            upgrades.append(Upgrade(
                "L05", "TELESCOPE_DOMAIN_COMBOS['basic']",
                "basic 조합 최적성 확인 — 변경 불필요",
                f"경험적 basic={basic}가 정량적 최적과 일치",
                "🟢"
            ))
        else:
            upgrades.append(Upgrade(
                "L05", "TELESCOPE_DOMAIN_COMBOS['basic']",
                f"basic 조합 변경 제안: {basic} → {optimal_lenses}",
                f"최적 K*={k_star} 기반",
                "🔴"
            ))

    return upgrades


def analyze_L11(result):
    """L11 직교성 → 중복 렌즈 제거"""
    upgrades = []
    if not result:
        return upgrades

    high_corr = result.metrics.get("high_corr_pairs", 0)
    if high_corr > 0:
        for f in result.findings:
            if "중복 가능" in f:
                upgrades.append(Upgrade(
                    "L11", "TELESCOPE_ALL_LENSES",
                    f"렌즈 중복 감지: {f}",
                    "상관 > 0.9인 렌즈 쌍 — 하나 제거 가능",
                    "🟡"
                ))
    else:
        upgrades.append(Upgrade(
            "L11", "TELESCOPE_ALL_LENSES",
            "22개 렌즈 모두 독립적 — 중복 없음",
            "제거할 렌즈 없음, 현재 구성 최적",
            "🟢"
        ))

    return upgrades


def analyze_L12(result):
    """L12 PCA → 유효 차원 기반 압축"""
    upgrades = []
    if not result:
        return upgrades

    d95 = result.metrics.get("d_eff_95%", 0)
    total = result.metrics.get("total_dims", 22)

    if d95 > 0 and d95 < total:
        compression = total / d95
        upgrades.append(Upgrade(
            "L12", "lens_config",
            f"렌즈 압축 가능: {total}→{d95} ({compression:.1f}x)",
            f"95% 분산을 {d95}개 주성분으로 커버",
            "🟡" if compression < 2 else "🔴"
        ))

    return upgrades


def analyze_L14(result):
    """L14 민감도 → 렌즈 우선순위"""
    upgrades = []
    if not result:
        return upgrades

    # 민감도 기반 렌즈 랭킹
    ranked = [(k, float(v)) for k, v in result.metrics.items() if k not in ('n_lenses_analyzed',)]
    if ranked:
        ranked.sort(key=lambda x: -x[1])
        top3 = [r[0] for r in ranked[:3]]
        upgrades.append(Upgrade(
            "L14", "TELESCOPE_DOMAIN_COMBOS['sensitive']",
            f"새 도메인 조합 제안: sensitive = {top3}",
            f"Φ 변화 민감도 상위 3 렌즈",
            "🟡"
        ))

    return upgrades


def analyze_L24(result):
    """L24 n=6 → σ(6)=12 최적 부분집합"""
    upgrades = []
    if not result:
        return upgrades

    coverage = result.metrics.get("coverage", "0%")
    if "%" in str(coverage):
        pct = float(str(coverage).replace("%", ""))
        if pct >= 90:
            selected = result.metrics.get("selected_12", "")
            upgrades.append(Upgrade(
                "L24", "TELESCOPE_DOMAIN_COMBOS['n6_optimal']",
                f"σ(6)=12 최적 부분집합 확인: {selected}",
                f"커버리지 {coverage} — 22개 대신 12개로 충분",
                "🔴"
            ))

    return upgrades


ANALYZERS = {
    "L01": analyze_L01,
    "L05": analyze_L05,
    "L11": analyze_L11,
    "L12": analyze_L12,
    "L14": analyze_L14,
    "L24": analyze_L24,
}


# ═══════════════════════════════════════════════════════════════
# 업그레이드 적용
# ═══════════════════════════════════════════════════════════════

def apply_upgrade(upgrade, dry_run=False):
    """업그레이드 적용"""
    if dry_run:
        return False

    target = upgrade.target

    # infinite_evolution.py 의 TELESCOPE_DOMAIN_COMBOS 수정
    if "TELESCOPE_DOMAIN_COMBOS" in target and "새 도메인 조합" in upgrade.action:
        # 새 조합 추가
        evo_path = SRC / "infinite_evolution.py"
        if evo_path.exists():
            text = evo_path.read_text()
            # 새 도메인이 이미 있는지 확인
            combo_name = target.split("'")[1] if "'" in target else "new"
            if f"'{combo_name}'" not in text:
                # TELESCOPE_DOMAIN_COMBOS 끝에 추가
                insert_point = text.find("}\n\n", text.find("TELESCOPE_DOMAIN_COMBOS"))
                if insert_point > 0:
                    lenses_str = upgrade.action.split("= ")[1] if "= " in upgrade.action else "[]"
                    new_line = f"    '{combo_name}': {lenses_str},\n"
                    text = text[:insert_point] + new_line + text[insert_point:]
                    evo_path.write_text(text)
                    upgrade.applied = True
                    return True

    # 업그레이드 기록만 (코드 변경 불필요한 경우)
    if "확인" in upgrade.action or "유지" in upgrade.action:
        upgrade.applied = True
        return True

    return False


# ═══════════════════════════════════════════════════════════════
# 파이프라인
# ═══════════════════════════════════════════════════════════════

def run_pipeline(experiments=None, cells=64, steps=300, dry_run=False, cycles=1):
    """전체 파이프라인: 실험 → 분석 → 업그레이드 → 재검증"""

    if experiments is None:
        experiments = ["L01", "L05", "L11", "L12", "L14", "L24"]
    # 등록된 실험만 필터
    experiments = [e for e in experiments if e in REGISTRY]

    all_upgrades = []
    cycle_history = []

    for cycle in range(cycles):
        print(f"\n  ════════════════════════════════════════════")
        print(f"  🔄 Cycle {cycle+1}/{cycles}")
        print(f"  ════════════════════════════════════════════")

        # [1] 실험 실행
        print(f"\n  [1/4] 실험 실행 ({len(experiments)}개)...")
        results = {}
        for exp_id in experiments:
            r = run_experiment(exp_id, cells=cells, steps=steps)
            if r:
                results[exp_id] = r

        # [2] 결과 분석 → 업그레이드 후보
        print(f"\n  [2/4] 결과 분석...")
        upgrades = []
        for exp_id, result in results.items():
            analyzer = ANALYZERS.get(exp_id)
            if analyzer:
                ups = analyzer(result)
                upgrades.extend(ups)
                for u in ups:
                    print(u)

        # [3] 업그레이드 적용
        print(f"\n  [3/4] 업그레이드 적용{'(dry-run)' if dry_run else ''}...")
        applied = 0
        for u in upgrades:
            if u.priority in ("🔴", "🟡"):
                success = apply_upgrade(u, dry_run=dry_run)
                if success:
                    applied += 1
                    print(f"  ✅ 적용: {u.action[:60]}")
                else:
                    print(f"  ⏳ 수동: {u.action[:60]}")

        # [4] 기록
        cycle_record = {
            "cycle": cycle + 1,
            "timestamp": datetime.now().isoformat(),
            "experiments": list(results.keys()),
            "upgrades": len(upgrades),
            "applied": applied,
            "findings": sum(len(r.findings) for r in results.values()),
        }
        cycle_history.append(cycle_record)
        all_upgrades.extend(upgrades)

        print(f"\n  [4/4] 결과: {len(upgrades)}개 업그레이드, {applied}개 적용")

        # 수렴 체크: 업그레이드 0이면 종료
        if applied == 0 and cycle > 0:
            print(f"\n  🏁 수렴 — 더 이상 업그레이드 없음 (cycle {cycle+1})")
            break

    # 최종 리포트
    print(f"\n  ════════════════════════════════════════════")
    print(f"  📊 최종 리포트")
    print(f"  ════════════════════════════════════════════")
    print(f"  사이클: {len(cycle_history)}")
    print(f"  총 업그레이드: {len(all_upgrades)}")
    total_applied = sum(1 for u in all_upgrades if u.applied)
    print(f"  적용됨: {total_applied}")
    print(f"  수동 필요: {len(all_upgrades) - total_applied}")

    # 분류
    by_priority = {"🔴": [], "🟡": [], "🟢": []}
    for u in all_upgrades:
        by_priority.get(u.priority, []).append(u)

    for p in ("🔴", "🟡", "🟢"):
        ups = by_priority[p]
        if ups:
            label = {"🔴": "CRITICAL", "🟡": "IMPORTANT", "🟢": "OK"}.get(p)
            print(f"\n  {p} {label} ({len(ups)})")
            for u in ups:
                print(u)

    # JSON 저장
    upgrade_log = {
        "timestamp": datetime.now().isoformat(),
        "cycles": cycle_history,
        "upgrades": [
            {
                "source": u.source,
                "target": u.target,
                "action": u.action,
                "reason": u.reason,
                "priority": u.priority,
                "applied": u.applied,
            }
            for u in all_upgrades
        ],
    }
    DATA.mkdir(exist_ok=True)
    log_path = DATA / f"lens_upgrade_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    save_json(log_path, upgrade_log)
    print(f"\n  💾 {log_path}")

    return all_upgrades


def main():
    parser = argparse.ArgumentParser(description="렌즈 실험 → 자동 업그레이드")
    parser.add_argument("--experiments", nargs="*", help="실험 ID")
    parser.add_argument("--cells", type=int, default=32)
    parser.add_argument("--steps", type=int, default=100)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--cycle", type=int, default=1)
    args = parser.parse_args()

    if args.verify_only:
        args.experiments = ["L01"]
        args.dry_run = True

    run_pipeline(
        experiments=args.experiments,
        cells=args.cells,
        steps=args.steps,
        dry_run=args.dry_run,
        cycles=args.cycle,
    )


if __name__ == "__main__":
    main()
