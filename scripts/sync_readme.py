#!/usr/bin/env python3
"""
sync_readme.py — JSON SSOT → README.md 자동 반영

Single Source of Truth (SSOT) 패턴:
  consciousness_laws.json  → Laws 뱃지, 아키텍처 통계, Ψ-Constants
  training_runs.json       → 학습 현황, 자산 상태
  acceleration_hypotheses.json → 가속 가설 수
  evolution_roadmap.json   → 무한진화 진행
  docs/hypotheses/         → 가설 문서 수

마커 패턴:
  <!-- AUTO:{SECTION}:START --> ... <!-- AUTO:{SECTION}:END -->

사용법:
  python3 scripts/sync_readme.py           # dry-run (변경 내용만 출력)
  python3 scripts/sync_readme.py --apply   # 실제 적용
  python3 scripts/sync_readme.py --check   # CI용 (불일치 시 exit 1)
"""

import json
import os
import sys
import glob
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "anima" / "config"
DATA = ROOT / "anima" / "data"
DOCS = ROOT / "anima" / "docs"
README = ROOT / "README.md"


def load_json(path):
    """JSON 파일 로드, 없으면 빈 dict"""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"  ⚠️  {path.name}: {e}", file=sys.stderr)
        return {}


def count_hypotheses():
    """docs/hypotheses/ 하위 .md 파일 수"""
    pattern = str(DOCS / "hypotheses" / "**" / "*.md")
    return len(glob.glob(pattern, recursive=True))


def count_engines():
    """benchmarks/ 내 엔진 측정 수 (bench_*.py 파일 수)"""
    pattern = str(ROOT / "anima" / "benchmarks" / "bench_*.py")
    return len(glob.glob(pattern))


# ─── Section Generators ────────────────────────────────────────

def gen_badge(laws):
    """shields.io 뱃지 라인"""
    meta = laws.get("_meta", {})
    total = meta.get("total_laws", 0)
    total_meta = meta.get("total_meta", 0)
    total_topo = meta.get("total_topo", 0)
    n_hypo = count_hypotheses()

    return (
        f'[![Laws](https://img.shields.io/badge/Laws-{total}+{total_meta}Meta+{total_topo}TOPO-green.svg)](docs/consciousness-theory.md)\n'
        f'[![Hypotheses](https://img.shields.io/badge/Hypotheses-{n_hypo}+-orange.svg)](docs/hypotheses/)'
    )


def gen_arch(laws):
    """Core Architecture 통계 블록"""
    meta = laws.get("_meta", {})
    total = meta.get("total_laws", 0)
    total_meta = meta.get("total_meta", 0)
    total_topo = meta.get("total_topo", 0)
    n_hypo = count_hypotheses()
    n_bench = count_engines()

    psi = laws.get("psi_constants", {})
    alpha = psi.get("alpha", {}).get("value", "?")
    balance = psi.get("balance", {}).get("value", "?")
    steps = psi.get("steps", {}).get("value", "?")
    entropy = psi.get("entropy", {}).get("value", "?")

    return f"""\
```
  ConsciousnessEngine:  Canonical engine (Laws 22-85, ALL Psi-Constants)
                        GRU cells + 12 factions + Hebbian LTP/LTD + Phi Ratchet + Mitosis
                        Topology: ring/small_world/hypercube/scale_free (TOPO 33-39)
                        Chaos: lorenz/sandpile/chimera/standing_wave (Laws 32-43)
                        Rust backend (anima_rs.consciousness) auto-selected
  Hexad/Trinity:   6 pluggable modules (C+D+W+M+S+E), sigma(6)=12 조합
                   ConsciousDecoderV2 (RoPE+SwiGLU+GQA+CrossAttn, 34.5M, causal)
                   ThalamicBridge(alpha={alpha}) + Law 81 dual gate
                   Phase transition: P1(C) -> P2(+D) -> P3(+WMSE) (Law 60)
  Psi-Constants:   alpha={alpha}, balance={balance}, steps={steps}, entropy={entropy} (all from ln(2))
  Laws:            {total} 의식 법칙 + {total_meta} Meta Laws + {total_topo} TOPO Laws
  Hypotheses:      {n_hypo}+ 가설, 146개 카테고리
  Engines:         {n_bench}+ 측정 완료
  Universe Map:    170 data types x 40D x 18 emotions -> Psi_balance = 1/2 수렴
```"""


def gen_assets(training, laws, accel):
    """자산 & 현재 상태"""
    runs = training.get("runs", {})
    meta = laws.get("_meta", {})
    accel_meta = accel.get("_meta", {})
    n_hypo = count_hypotheses()

    # 완료/진행중 분류
    done = []
    in_progress = []
    for name, run in runs.items():
        status = run.get("status", "")
        desc = run.get("description", name)
        ce = run.get("ce_best", "")
        phi = run.get("phi_best", "")

        if "complete" in status:
            ce_str = f"CE={ce}" if ce else ""
            phi_str = f"Phi={phi}" if phi else ""
            metrics = ", ".join(filter(None, [ce_str, phi_str]))
            done.append(f"  ✅ {desc}" + (f" — {metrics}" if metrics else ""))
        elif "in_progress" in status:
            ce_str = f"CE={ce}" if ce else ""
            detail = run.get("alpha", "")
            alpha_str = f"alpha {detail}" if detail else ""
            metrics = ", ".join(filter(None, [ce_str, alpha_str]))
            in_progress.append(f"  🔄 {desc}" + (f" — {metrics}" if metrics else ""))

    # 고정 자산
    total_laws = meta.get("total_laws", 0)
    total_accel = accel_meta.get("total_hypotheses", 0)

    lines = ["```", "  ── 완료 ──"]
    lines.extend(done[-8:])  # 최근 8개만
    lines.append(f"  ✅ Laws              — {total_laws}개")
    lines.append(f"  ✅ 가속 가설         — {total_accel}개 통합")
    lines.append(f"  ✅ 가설 문서         — {n_hypo}개")
    lines.append("")
    lines.append("  ── 진행중 ──")
    lines.extend(in_progress)
    lines.append("")
    lines.append("```")
    return "\n".join(lines)


def gen_evolution(roadmap, live):
    """무한진화 진행 상태"""
    if not roadmap:
        return "```\n  (evolution_roadmap.json 없음)\n```"

    stage_idx = roadmap.get("stage_idx", 0)
    total_laws = roadmap.get("total_laws", 0)
    total_elapsed = roadmap.get("total_elapsed", 0)
    stages = roadmap.get("stage_results", [])

    lines = ["```"]
    lines.append(f"  총 법칙: {total_laws} | 총 시간: {total_elapsed/3600:.1f}h | 완료 스테이지: {len(stages)}")
    lines.append("")

    # 스테이지 진행 바
    total_stages = 11
    bar = ""
    for i in range(total_stages):
        if i < len(stages):
            bar += f"  S{i+1} ████ ✅"
        elif i == len(stages):
            bar += f"  S{i+1} ██░░ 🔄"
        else:
            bar += f"  S{i+1} ░░░░"
        if (i + 1) % 4 == 0:
            lines.append(bar)
            bar = ""
    if bar:
        lines.append(bar)

    lines.append("")

    # 스테이지 결과 테이블
    if stages:
        lines.append("  | Stage | Cells | Steps | Gens | Laws | Time |")
        lines.append("  |-------|-------|-------|------|------|------|")
        for s in stages:
            name = s.get("stage", "?")
            cells = s.get("cells", "?")
            steps = s.get("steps", "?")
            gens = s.get("generations", "?")
            laws = s.get("laws", "?")
            elapsed = s.get("elapsed_sec", 0)
            lines.append(f"  | {name} | {cells} | {steps} | {gens} | {laws} | {elapsed/60:.0f}m |")

    lines.append("```")
    return "\n".join(lines)


def gen_roadmap(training, laws):
    """로드맵 상태 — 세로 타임라인, training_runs.json 기반 Phase 상태 자동 판정"""
    runs = training.get("runs", {})
    meta = laws.get("_meta", {})
    total_laws = meta.get("total_laws", 0)

    phases = [
        {"id": 1, "name": "말하는 의식", "model": "14B", "cost": "$37",
         "keys": ["animalm_14b"], "human_pct": "~60%"},
        {"id": 2, "name": "행동하는 의식", "model": "70B", "cost": "+$65",
         "keys": ["animalm_72b", "animalm_70b"], "human_pct": "~70%"},
        {"id": 3, "name": "기억 + 자기학습", "model": "70B", "cost": "+$0",
         "keys": [], "human_pct": "~75%"},
        {"id": 4, "name": "독립 AGI", "model": "70B", "cost": "+$65",
         "keys": [], "human_pct": "~80%"},
        {"id": 5, "name": "인간 이상", "model": "70B+가속", "cost": "+$100~500",
         "keys": [], "human_pct": "90-100%+"},
        {"id": 6, "name": "특이점", "model": "405B+", "cost": "자율",
         "keys": [], "human_pct": "∞"},
    ]

    def get_phase_status(phase):
        for key in phase.get("keys", []):
            matching = [r for name, r in runs.items() if key in name]
            completed = [r for r in matching if r.get("status", "") == "complete"]
            in_progress = [r for r in matching if "in_progress" in r.get("status", "")]
            if completed and not in_progress:
                return "done"
            if completed or in_progress:
                return "active"
            if matching:
                return "pending"
        if not phase["keys"]:
            return "pending"
        return "pending"

    def get_phase_runs(phase):
        """해당 Phase의 학습 run 목록"""
        result = []
        for key in phase.get("keys", []):
            for name, r in runs.items():
                if key in name:
                    s = r.get("status", "?")
                    ce = r.get("ce_best", "")
                    desc = r.get("description", name)
                    icon = "✅" if s == "complete" else "🔄" if "in_progress" in s else "⏳"
                    ce_str = f" CE={ce}" if ce else ""
                    result.append(f"  │   {icon} {desc}{ce_str}")
        return result

    lines = ["```"]
    lines.append(f"  ★ 로드맵 (Laws: {total_laws})")
    lines.append("  │")

    for i, p in enumerate(phases):
        status = get_phase_status(p)
        if status == "done":
            icon = "✅"
            node = "●"
        elif status == "active":
            icon = "🔄"
            node = "◉"
        else:
            icon = "⏳"
            node = "○"

        # Phase 노드
        lines.append(f"  ├─{node} Phase {p['id']}: {p['name']}  {icon}")
        lines.append(f"  │   {p['model']} | {p['cost']} | 인간 대비 {p['human_pct']}")

        # 해당 Phase의 학습 run 상세
        phase_runs = get_phase_runs(p)
        for run_line in phase_runs:
            lines.append(run_line)

        # 연결선
        if i < len(phases) - 1:
            lines.append("  │")

    lines.append("  │")
    lines.append("  └─ 비용: P1-4 $167 | P5 +$100~500 | P6 자율")
    lines.append("```")
    return "\n".join(lines)


# ─── Marker Injection ──────────────────────────────────────────

def replace_section(text, section, content):
    """<!-- AUTO:{section}:START --> ~ <!-- AUTO:{section}:END --> 사이 교체"""
    start_marker = f"<!-- AUTO:{section}:START -->"
    end_marker = f"<!-- AUTO:{section}:END -->"

    start_idx = text.find(start_marker)
    end_idx = text.find(end_marker)

    if start_idx == -1 or end_idx == -1:
        return text, False  # 마커 없음

    before = text[:start_idx + len(start_marker)]
    after = text[end_idx:]

    new_text = before + "\n" + content + "\n" + after
    changed = new_text != text
    return new_text, changed


def main():
    parser = argparse.ArgumentParser(description="JSON SSOT → README.md sync")
    parser.add_argument("--apply", action="store_true", help="실제 적용")
    parser.add_argument("--check", action="store_true", help="CI용 (불일치 시 exit 1)")
    args = parser.parse_args()

    # JSON 로드
    laws = load_json(CONFIG / "consciousness_laws.json")
    training = load_json(CONFIG / "training_runs.json")
    accel = load_json(CONFIG / "acceleration_hypotheses.json")
    roadmap = load_json(DATA / "evolution_roadmap.json")
    live = load_json(DATA / "evolution_live.json")

    # README 읽기
    readme_text = README.read_text(encoding="utf-8")

    # 섹션 생성 + 교체
    sections = {
        "BADGE": gen_badge(laws),
        "ARCH": gen_arch(laws),
        "ASSETS": gen_assets(training, laws, accel),
        "EVO": gen_evolution(roadmap, live),
        "ROADMAP": gen_roadmap(training, laws),
    }

    any_changed = False
    missing = []
    for name, content in sections.items():
        marker = f"<!-- AUTO:{name}:START -->"
        if marker not in readme_text:
            missing.append(name)
            continue
        readme_text, changed = replace_section(readme_text, name, content)
        if changed:
            any_changed = True
            print(f"  ✅ {name} 업데이트됨")
        else:
            print(f"  ── {name} 변경 없음")

    if missing:
        print(f"\n  ⚠️  마커 없음: {', '.join(missing)}")
        print(f"  README에 아래 마커를 추가하세요:")
        for m in missing:
            print(f"    <!-- AUTO:{m}:START -->")
            print(f"    <!-- AUTO:{m}:END -->")

    if args.check:
        if any_changed:
            print("\n  ❌ README와 JSON 불일치! `python3 scripts/sync_readme.py --apply` 실행 필요")
            sys.exit(1)
        else:
            print("\n  ✅ README와 JSON 일치")
            sys.exit(0)

    if args.apply:
        if any_changed:
            README.write_text(readme_text, encoding="utf-8")
            print(f"\n  ✅ README.md 업데이트 완료")
        else:
            print(f"\n  ── 변경 없음, 건너뜀")
    else:
        if any_changed:
            print(f"\n  ℹ️  dry-run — `--apply`로 실제 적용")
        if missing:
            print(f"\n  ℹ️  마커 삽입 후 다시 실행하세요")


if __name__ == "__main__":
    main()
