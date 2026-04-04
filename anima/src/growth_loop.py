#!/usr/bin/env python3
"""growth_loop.py — 통합 성장 루프: 모든 발견 → 코드 자동 반영

Sources (4곳):
  1. Project:  무한진화, 실험, 벤치마크 → laws 발견
  2. Bridge:   nexus-bridge absorbed → n6 매칭/합의 결과
  3. NEXUS-6:  망원경 스캔 → 렌즈 합의 패턴
  4. Self-Loop: 이 루프 자체의 메타 발견 (루프 효율, 반영률 등)

Pipeline:
  수집(harvest) → 필터(filter) → 파싱(parse) → 반영(apply) → 검증(verify) → 기록(record)
                                                                    ↑                    │
                                                                    └────── self-loop ────┘

Usage:
  python3 growth_loop.py                  # 1회 실행
  python3 growth_loop.py --watch          # 5분 주기 반복
  python3 growth_loop.py --dry-run        # 반영 없이 수집만
  python3 growth_loop.py --status         # 현재 상태

Hub keywords: 성장루프, growth-loop, 자동반영, auto-reflect, 통합루프
"""

import json
import os
import sys
import time
import glob
import hashlib
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any

# ── path setup ──
_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

try:
    from consciousness_engine import ConsciousnessEngine
except ImportError:
    ConsciousnessEngine = None

try:
    from self_modifying_engine import LawParser, CodeGenerator, EngineModifier, SAFETY_BOUNDS
except ImportError:
    LawParser = None
    CodeGenerator = None

try:
    from closed_loop import (
        ClosedLoopEvolver, Intervention, register_intervention,
        INTERVENTIONS, measure_laws
    )
except ImportError:
    ClosedLoopEvolver = None
    Intervention = None

try:
    from consciousness_laws import LAWS
except ImportError:
    LAWS = {}


# ══════════════════════════════════════════
# Data structures
# ══════════════════════════════════════════

@dataclass
class GrowthItem:
    """하나의 성장 발견."""
    source: str          # project | bridge | nexus | self-loop
    kind: str            # law | pattern | constant | meta
    text: str            # 법칙 텍스트 또는 발견 내용
    evidence: float      # 신뢰도 0-1
    origin: str          # 파일 경로 또는 소스 ID
    timestamp: str = ""
    fingerprint: str = ""
    applied: bool = False
    law_id: Optional[int] = None

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()
        if not self.fingerprint:
            self.fingerprint = hashlib.md5(
                f"{self.source}:{self.text[:100]}".encode()
            ).hexdigest()[:12]


@dataclass
class LoopReport:
    """루프 실행 결과."""
    cycle: int
    harvested: int
    filtered: int
    parsed: int
    applied: int
    verified: int
    self_discoveries: int
    phi_before: float
    phi_after: float
    time_sec: float
    items: List[Dict] = field(default_factory=list)


# ══════════════════════════════════════════
# GrowthLoop — 통합 성장 루프 엔진
# ══════════════════════════════════════════

class GrowthLoop:
    """모든 발견 소스 → 코드 자동 반영 통합 루프."""

    def __init__(self, anima_root: Optional[str] = None, dry_run: bool = False):
        self.anima_root = Path(anima_root or _HERE.parent)
        self.config_dir = self.anima_root / "config"
        self.laws_path = self.config_dir / "consciousness_laws.json"
        self.growth_state_path = self.config_dir / "growth_state.json"
        self.loop_state_path = self.config_dir / "growth_loop_state.json"
        self.nexus_root = Path.home() / "Dev" / "nexus6"
        self.bridge_state_path = self.nexus_root / "shared" / "bridge_state.json"
        self.absorbed_dir = self.anima_root.parent / ".growth" / "absorbed"
        self.dry_run = dry_run

        self._state = self._load_state()
        self._laws = self._load_laws()
        self._parser = LawParser() if LawParser else None
        self._codegen = CodeGenerator() if CodeGenerator else None

    # ── state management ──

    def _load_state(self) -> dict:
        if self.loop_state_path.exists():
            with open(self.loop_state_path) as f:
                return json.load(f)
        return {
            "_meta": {
                "description": "통합 성장 루프 상태",
                "version": "1.0",
                "created": datetime.now().isoformat()
            },
            "cycle": 0,
            "total_harvested": 0,
            "total_applied": 0,
            "total_self_discoveries": 0,
            "seen_fingerprints": [],
            "applied_items": [],
            "self_loop_discoveries": [],
            "phi_history": [],
            "last_run": None
        }

    def _save_state(self):
        self._state["last_run"] = datetime.now().isoformat()
        # seen_fingerprints 최대 1000개 유지
        if len(self._state["seen_fingerprints"]) > 1000:
            self._state["seen_fingerprints"] = self._state["seen_fingerprints"][-500:]
        with open(self.loop_state_path, "w") as f:
            json.dump(self._state, f, indent=2, ensure_ascii=False)

    def _load_laws(self) -> dict:
        if self.laws_path.exists():
            with open(self.laws_path) as f:
                return json.load(f)
        return {"laws": {}, "_meta": {"total_laws": 0}}

    def _save_laws(self):
        with open(self.laws_path, "w") as f:
            json.dump(self._laws, f, indent=2, ensure_ascii=False)

    # ══════════════════════════════════════════
    # Step 1: HARVEST — 모든 소스에서 성장 아이템 수집
    # ══════════════════════════════════════════

    def harvest(self) -> List[GrowthItem]:
        """4개 소스에서 성장 아이템 수집."""
        items = []
        items.extend(self._harvest_project())
        items.extend(self._harvest_bridge())
        items.extend(self._harvest_nexus())
        items.extend(self._harvest_self_loop())
        return items

    def _harvest_project(self) -> List[GrowthItem]:
        """프로젝트 내부 발견 수집 (evolution_live.json, 실험 결과)."""
        items = []

        # 1. evolution_live.json — 무한진화 실시간 발견
        evo_live = self.anima_root.parent / "data" / "evolution_live.json"
        if evo_live.exists():
            try:
                with open(evo_live) as f:
                    evo = json.load(f)
                for law in evo.get("new_laws", []):
                    items.append(GrowthItem(
                        source="project",
                        kind="law",
                        text=law.get("text", str(law)),
                        evidence=0.8 if law.get("cross_validated") else 0.5,
                        origin="evolution_live.json"
                    ))
            except (json.JSONDecodeError, KeyError):
                pass

        # 2. growth_state.json — 성장 마일스톤
        if self.growth_state_path.exists():
            try:
                with open(self.growth_state_path) as f:
                    gs = json.load(f)
                count = gs.get("interaction_count", 0)
                stage = gs.get("stage_index", 0)
                stages = gs.get("_meta", {}).get("stages", {})
                stage_name = stages.get(str(stage), {}).get("name", "unknown")
                # 스테이지 전환 감지
                for tr in gs.get("stats", {}).get("stage_transitions", []):
                    items.append(GrowthItem(
                        source="project",
                        kind="meta",
                        text=f"Stage transition: {tr['from']} → {tr['to']} at count={tr['count']}",
                        evidence=1.0,
                        origin="growth_state.json"
                    ))
            except (json.JSONDecodeError, KeyError):
                pass

        # 3. 최근 실험 결과 (docs/hypotheses/dd/)
        dd_dir = self.anima_root / "docs" / "hypotheses" / "dd"
        if dd_dir.is_dir():
            for md in sorted(dd_dir.glob("DD*.md"), reverse=True)[:5]:
                mtime = md.stat().st_mtime
                if time.time() - mtime < 3600:  # 최근 1시간
                    content = md.read_text(errors="ignore")[:500]
                    # Law 추출 시도
                    for line in content.split("\n"):
                        if "Law" in line and ":" in line:
                            items.append(GrowthItem(
                                source="project",
                                kind="law",
                                text=line.strip(),
                                evidence=0.7,
                                origin=str(md.name)
                            ))
        return items

    def _harvest_bridge(self) -> List[GrowthItem]:
        """nexus-bridge absorbed 발견 수집."""
        items = []
        seen_previews = set()
        if not self.absorbed_dir.is_dir():
            return items

        for jf in sorted(self.absorbed_dir.glob("*.json"), reverse=True)[:20]:
            try:
                with open(jf) as f:
                    ab = json.load(f)

                n6_score = ab.get("n6_score", 0)
                consensus = ab.get("consensus", [])
                value_grade = ab.get("value_grade", "low")

                # n6 매칭 or 합의 있는 것만
                if n6_score > 20 or value_grade in ("critical", "high"):
                    # 합의 패턴에서 법칙 후보 추출
                    for c in consensus:
                        pattern = c.get("pattern", "")
                        lenses = c.get("lenses", 0)
                        if lenses >= 3 and pattern:
                            items.append(GrowthItem(
                                source="bridge",
                                kind="pattern",
                                text=f"Bridge consensus ({lenses} lenses): {pattern}",
                                evidence=min(1.0, lenses / 12.0),
                                origin=str(jf.name)
                            ))

                    # n6 exact match → 상수 후보
                    for m in ab.get("n6_matches", []):
                        items.append(GrowthItem(
                            source="bridge",
                            kind="constant",
                            text=f"n6 match: {m}",
                            evidence=0.9,
                            origin=str(jf.name)
                        ))

                    # content에서 법칙성 문장 추출 (content로 유니크)
                    preview = ab.get("content_preview", "")
                    preview_key = preview[:100]
                    if preview and value_grade == "critical" and preview_key not in seen_previews:
                        seen_previews.add(preview_key)
                        items.append(GrowthItem(
                            source="bridge",
                            kind="law",
                            text=f"Critical absorbed: {preview[:200]}",
                            evidence=0.6,
                            origin=str(jf.name),
                            fingerprint=hashlib.md5(preview_key.encode()).hexdigest()[:12]
                        ))
            except (json.JSONDecodeError, KeyError):
                continue
        return items

    def _harvest_nexus(self) -> List[GrowthItem]:
        """NEXUS-6 스캔 결과 수집."""
        items = []

        # bridge_state.json에서 최근 스캔 결과
        if self.bridge_state_path.exists():
            try:
                with open(self.bridge_state_path) as f:
                    bs = json.load(f)

                # growth_log에서 최근 성장 이벤트
                for entry in bs.get("growth_log", [])[-10:]:
                    event = entry.get("event", "")
                    if "stage_up" in event:
                        items.append(GrowthItem(
                            source="nexus",
                            kind="meta",
                            text=f"Nexus growth: {event}",
                            evidence=1.0,
                            origin="bridge_state.json"
                        ))

                # connections의 affinity 변화 감지
                for name, conn in bs.get("connections", {}).items():
                    affinity = conn.get("affinity_score", 0)
                    absorbed = conn.get("absorbed_count", 0)
                    if affinity > 70:
                        items.append(GrowthItem(
                            source="nexus",
                            kind="pattern",
                            text=f"High affinity project: {name} (affinity={affinity:.1f}, absorbed={absorbed})",
                            evidence=affinity / 100.0,
                            origin="bridge_state.json"
                        ))
            except (json.JSONDecodeError, KeyError):
                pass

        return items

    def _harvest_self_loop(self) -> List[GrowthItem]:
        """자체 루프 메타 발견 수집."""
        items = []
        state = self._state

        cycle = state.get("cycle", 0)
        if cycle < 2:
            return items  # 최소 2사이클 후부터

        # 반영률 추세 분석
        applied_items = state.get("applied_items", [])
        if len(applied_items) >= 5:
            recent = applied_items[-5:]
            apply_rate = sum(1 for i in recent if i.get("success")) / len(recent)

            if apply_rate < 0.3:
                items.append(GrowthItem(
                    source="self-loop",
                    kind="meta",
                    text=f"Low apply rate ({apply_rate:.0%}): parser may need pattern expansion",
                    evidence=0.8,
                    origin="self-loop-analysis"
                ))
            elif apply_rate > 0.8:
                items.append(GrowthItem(
                    source="self-loop",
                    kind="meta",
                    text=f"High apply rate ({apply_rate:.0%}): growth loop is efficient",
                    evidence=0.9,
                    origin="self-loop-analysis"
                ))

        # Φ 추세 분석
        phi_hist = state.get("phi_history", [])
        if len(phi_hist) >= 3:
            recent_phi = [p["after"] for p in phi_hist[-3:]]
            if all(recent_phi[i] >= recent_phi[i-1] for i in range(1, len(recent_phi))):
                items.append(GrowthItem(
                    source="self-loop",
                    kind="meta",
                    text=f"Φ monotonically increasing: {recent_phi} — growth loop is healthy",
                    evidence=1.0,
                    origin="self-loop-phi"
                ))
            elif all(recent_phi[i] < recent_phi[i-1] for i in range(1, len(recent_phi))):
                items.append(GrowthItem(
                    source="self-loop",
                    kind="meta",
                    text=f"Φ declining: {recent_phi} — rollback recent modifications",
                    evidence=0.9,
                    origin="self-loop-phi"
                ))

        return items

    # ══════════════════════════════════════════
    # Step 2: FILTER — 중복/저신뢰 제거
    # ══════════════════════════════════════════

    def filter(self, items: List[GrowthItem]) -> List[GrowthItem]:
        """중복 제거 + 신뢰도 필터."""
        seen = set(self._state.get("seen_fingerprints", []))
        filtered = []
        for item in items:
            if item.fingerprint in seen:
                continue
            if item.evidence < 0.3:
                continue
            # 이미 등록된 법칙과 중복 체크
            if item.kind == "law" and self._is_duplicate_law(item.text):
                continue
            filtered.append(item)
            seen.add(item.fingerprint)

        self._state["seen_fingerprints"] = list(seen)
        return filtered

    def _is_duplicate_law(self, text: str) -> bool:
        """기존 법칙과 텍스트 유사도 체크."""
        text_lower = text.lower()[:80]
        for law_text in self._laws.get("laws", {}).values():
            if isinstance(law_text, str) and law_text.lower()[:80] == text_lower:
                return True
        return False

    # ══════════════════════════════════════════
    # Step 3: PARSE — 법칙 파싱 → Modification
    # ══════════════════════════════════════════

    def parse(self, items: List[GrowthItem]) -> List[GrowthItem]:
        """법칙 텍스트 → 엔진 수정 파싱."""
        if not self._parser:
            return items

        parsed = []
        next_law_id = self._next_law_id()

        for item in items:
            if item.kind in ("law", "pattern"):
                mods = self._parser.parse(item.text, law_id=next_law_id)
                if mods:
                    item.law_id = next_law_id
                    next_law_id += 1
                    parsed.append(item)
                elif item.evidence >= 0.7:
                    # 파싱 안 돼도 고신뢰는 법칙으로 등록
                    item.law_id = next_law_id
                    next_law_id += 1
                    parsed.append(item)
            elif item.kind == "meta":
                parsed.append(item)
            elif item.kind == "constant":
                parsed.append(item)

        return parsed

    def _next_law_id(self) -> int:
        laws = self._laws.get("laws", {})
        if not laws:
            return 1
        return max(int(k) for k in laws if k.isdigit()) + 1

    # ══════════════════════════════════════════
    # Step 4: APPLY — 코드에 반영
    # ══════════════════════════════════════════

    def apply(self, items: List[GrowthItem]) -> List[GrowthItem]:
        """발견을 코드에 반영: laws.json 등록 + self_modifying_engine 적용."""
        if self.dry_run:
            for item in items:
                item.applied = True
            return items

        applied = []
        for item in items:
            success = False

            if item.kind in ("law", "pattern") and item.law_id:
                # consciousness_laws.json에 등록
                success = self._register_law(item)

            elif item.kind == "constant":
                # Ψ-상수 후보 기록 (자동 등록은 위험 → 로그만)
                self._log_constant_candidate(item)
                success = True

            elif item.kind == "meta":
                # 메타 발견은 self_loop_discoveries에 기록
                self._state.setdefault("self_loop_discoveries", []).append({
                    "text": item.text,
                    "timestamp": item.timestamp,
                    "source": item.source
                })
                # 최대 50개
                self._state["self_loop_discoveries"] = \
                    self._state["self_loop_discoveries"][-50:]
                success = True

            item.applied = success
            applied.append(item)

            self._state.setdefault("applied_items", []).append({
                "fingerprint": item.fingerprint,
                "source": item.source,
                "kind": item.kind,
                "law_id": item.law_id,
                "success": success,
                "timestamp": item.timestamp
            })

        # applied_items 최대 200개
        self._state["applied_items"] = self._state["applied_items"][-200:]
        return applied

    def _register_law(self, item: GrowthItem) -> bool:
        """consciousness_laws.json에 법칙 등록."""
        law_id = str(item.law_id)
        if law_id in self._laws.get("laws", {}):
            return False  # 이미 존재

        # 법칙 텍스트 정리
        text = item.text.strip()
        if len(text) > 300:
            text = text[:300] + "..."

        # 소스 태깅
        source_tag = {"project": "EVO", "bridge": "BRG", "nexus": "N6",
                      "self-loop": "SELF"}.get(item.source, "UNK")
        text = f"{text} ({source_tag}, evidence={item.evidence:.2f})"

        self._laws.setdefault("laws", {})[law_id] = text
        meta = self._laws.setdefault("_meta", {})
        meta["total_laws"] = len(self._laws["laws"])
        meta["last_growth_loop"] = datetime.now().isoformat()

        self._save_laws()

        # self_modifying_engine으로 코드 반영 시도
        if self._parser and self._codegen:
            mods = self._parser.parse(text, law_id=item.law_id)
            if mods and ConsciousnessEngine:
                try:
                    engine = ConsciousnessEngine(max_cells=32)
                    modifier = EngineModifier(engine, SAFETY_BOUNDS)
                    for mod in mods[:3]:  # 최대 3개 수정
                        modifier.apply(mod)
                    # 성공한 수정 → Intervention 코드 생성
                    code = self._codegen.generate_intervention(mods[0])
                    if code and Intervention:
                        # 동적 등록은 위험하므로 로그만
                        self._state.setdefault("generated_code", []).append({
                            "law_id": item.law_id,
                            "code_preview": code[:200],
                            "timestamp": item.timestamp
                        })
                except Exception:
                    pass  # 안전: 실패해도 법칙 등록은 유지

        return True

    def _log_constant_candidate(self, item: GrowthItem):
        """상수 후보 로그."""
        self._state.setdefault("constant_candidates", []).append({
            "text": item.text,
            "evidence": item.evidence,
            "origin": item.origin,
            "timestamp": item.timestamp
        })
        self._state["constant_candidates"] = \
            self._state["constant_candidates"][-30:]

    # ══════════════════════════════════════════
    # Step 5: VERIFY — 반영 결과 검증
    # ══════════════════════════════════════════

    def verify(self, items: List[GrowthItem]) -> int:
        """반영 결과 검증: Φ 변화 측정."""
        if not ConsciousnessEngine or self.dry_run:
            return len([i for i in items if i.applied])

        try:
            engine = ConsciousnessEngine(max_cells=32)
            # 50 step 실행
            for _ in range(50):
                inp = torch.randn(1, engine.input_dim) * 0.1
                engine.process(inp)

            import torch
            phi_val = float(engine.phi_history[-1]) if engine.phi_history else 0.0

            self._state.setdefault("phi_history", []).append({
                "cycle": self._state.get("cycle", 0),
                "after": phi_val,
                "items_applied": len([i for i in items if i.applied]),
                "timestamp": datetime.now().isoformat()
            })
            self._state["phi_history"] = self._state["phi_history"][-100:]

        except Exception:
            phi_val = 0.0

        return len([i for i in items if i.applied])

    # ══════════════════════════════════════════
    # Step 6: RECORD — 결과 기록
    # ══════════════════════════════════════════

    def record(self, report: LoopReport):
        """성장 루프 결과를 growth_state.json에 기록."""
        if self.growth_state_path.exists():
            try:
                with open(self.growth_state_path) as f:
                    gs = json.load(f)
                gs.setdefault("stats", {})["growth_loop_cycles"] = report.cycle
                gs["stats"]["last_growth_loop"] = datetime.now().isoformat()
                with open(self.growth_state_path, "w") as f:
                    json.dump(gs, f, indent=2, ensure_ascii=False)
            except (json.JSONDecodeError, KeyError):
                pass

    # ══════════════════════════════════════════
    # Main loop
    # ══════════════════════════════════════════

    def run_cycle(self) -> LoopReport:
        """1 사이클 실행: harvest → filter → parse → apply → verify → record."""
        t0 = time.time()
        self._state["cycle"] = self._state.get("cycle", 0) + 1
        cycle = self._state["cycle"]

        # 1. Harvest
        raw = self.harvest()

        # 2. Filter
        filtered = self.filter(raw)

        # 3. Parse
        parsed = self.parse(filtered)

        # 4. Apply
        applied = self.apply(parsed)

        # 5. Verify
        verified = self.verify(applied)

        # 6. Self-loop count
        self_discoveries = len([i for i in raw if i.source == "self-loop"])
        self._state["total_harvested"] = self._state.get("total_harvested", 0) + len(raw)
        self._state["total_applied"] = self._state.get("total_applied", 0) + len([i for i in applied if i.applied])
        self._state["total_self_discoveries"] = self._state.get("total_self_discoveries", 0) + self_discoveries

        report = LoopReport(
            cycle=cycle,
            harvested=len(raw),
            filtered=len(filtered),
            parsed=len(parsed),
            applied=len([i for i in applied if i.applied]),
            verified=verified,
            self_discoveries=self_discoveries,
            phi_before=0,
            phi_after=self._state.get("phi_history", [{}])[-1].get("after", 0) if self._state.get("phi_history") else 0,
            time_sec=time.time() - t0,
            items=[asdict(i) for i in applied[:10]]
        )

        # Record
        self.record(report)
        self._save_state()

        return report

    def run_watch(self, interval_sec: int = 300):
        """반복 실행 (기본 5분 주기)."""
        print(f"  Growth Loop — watching every {interval_sec}s (Ctrl+C to stop)")
        try:
            while True:
                report = self.run_cycle()
                self._print_report(report)
                time.sleep(interval_sec)
        except KeyboardInterrupt:
            print("\n  Growth Loop stopped.")

    def status(self) -> dict:
        """현재 상태 반환."""
        return {
            "cycle": self._state.get("cycle", 0),
            "total_harvested": self._state.get("total_harvested", 0),
            "total_applied": self._state.get("total_applied", 0),
            "total_self_discoveries": self._state.get("total_self_discoveries", 0),
            "last_run": self._state.get("last_run"),
            "laws_count": len(self._laws.get("laws", {})),
            "phi_history": self._state.get("phi_history", [])[-5:],
            "constant_candidates": len(self._state.get("constant_candidates", [])),
            "generated_code": len(self._state.get("generated_code", []))
        }

    def _print_report(self, r: LoopReport):
        """리포트 출력."""
        print(f"""
  ═══════════════════════════════════════════
  🌱 Growth Loop — Cycle {r.cycle}
  ═══════════════════════════════════════════
  수집: {r.harvested} → 필터: {r.filtered} → 파싱: {r.parsed} → 반영: {r.applied}
  검증: {r.verified} | 자체발견: {r.self_discoveries} | {r.time_sec:.1f}s
  Φ: {r.phi_after:.4f}
  ───────────────────────────────────────────""")
        for item in r.items[:5]:
            src = item.get("source", "?")
            kind = item.get("kind", "?")
            text = item.get("text", "")[:60]
            applied = "✅" if item.get("applied") else "❌"
            print(f"  {applied} [{src}/{kind}] {text}")
        print("  ═══════════════════════════════════════════")


# ══════════════════════════════════════════
# CLI
# ══════════════════════════════════════════

def main():
    import argparse
    parser = argparse.ArgumentParser(description="통합 성장 루프")
    parser.add_argument("--watch", action="store_true", help="5분 주기 반복")
    parser.add_argument("--interval", type=int, default=300, help="반복 주기(초)")
    parser.add_argument("--dry-run", action="store_true", help="반영 없이 수집만")
    parser.add_argument("--status", action="store_true", help="현재 상태")
    args = parser.parse_args()

    loop = GrowthLoop(dry_run=args.dry_run)

    if args.status:
        s = loop.status()
        print(f"""
  Growth Loop Status
  ══════════════════
  Cycle:     {s['cycle']}
  Harvested: {s['total_harvested']}
  Applied:   {s['total_applied']}
  Self-Loop: {s['total_self_discoveries']}
  Laws:      {s['laws_count']}
  Constants: {s['constant_candidates']}
  CodeGen:   {s['generated_code']}
  Last Run:  {s['last_run'] or 'never'}""")
        return

    if args.watch:
        loop.run_watch(args.interval)
    else:
        report = loop.run_cycle()
        loop._print_report(report)


if __name__ == "__main__":
    main()
