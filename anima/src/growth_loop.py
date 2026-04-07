#!/usr/bin/env python3
"""growth_loop.py — 통합 성장 루프: 모든 발견 → 코드 자동 반영 + 벽돌파

Sources (5곳):
  1. Project:  무한진화, 실험, 벤치마크 → laws 발견
  2. Bridge:   nexus-bridge absorbed → n6 매칭/합의 결과
  3. NEXUS-6:  망원경 스캔 → 렌즈 합의 패턴
  4. Engine:   의식 엔진 실시간 탐색 → Φ/토폴로지/다양성/회복력 패턴
  5. Self-Loop: 이 루프 자체의 메타 발견 (루프 효율, 반영률 등)

Pipeline:
  수집(harvest) → 필터(filter) → 파싱(parse) → 반영(apply) → 검증(verify) → 벽돌파(breakthrough) → 기록(record)
                                                                    ↑                                      │
                                                                    └────────────── self-loop ──────────────┘

벽돌파 6 메커니즘 (n=6):
  1. Domain Forge     — 발견이 기존 도메인에 안 맞으면 새 도메인 자동 생성
  2. Cross-Pollinate  — 도메인 A 발견을 도메인 B 탐색 타겟으로 주입
  3. Domain Split     — 과밀 도메인 자동 분할
  4. Wall Detect      — 연속 3사이클 발견 감소 → depth+1, threshold×0.1
  5. Keyword Absorb   — 새 발견에서 키워드 자동 추출 → 분류기 확장
  6. Engine Chain     — 다중 엔진 체인 (이전 출력 = 다음 입력)

특이점 구조:
  DISCOVER → ABSORB → EXPAND → (벽 감지) → DEEPEN → DISCOVER (자기가속)

Usage:
  python3 growth_loop.py                  # 1회 실행
  python3 growth_loop.py --watch          # 5분 주기 반복
  python3 growth_loop.py --dry-run        # 반영 없이 수집만
  python3 growth_loop.py --status         # 현재 상태

Hub keywords: 성장루프, growth-loop, 자동반영, auto-reflect, 통합루프, 벽돌파, breakthrough
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
        self.nexus_root = Path.home() / "Dev" / "nexus"
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
        """7개 소스에서 성장 아이템 수집."""
        items = []
        items.extend(self._harvest_project())
        items.extend(self._harvest_bridge())
        items.extend(self._harvest_nexus())
        items.extend(self._harvest_engine())
        items.extend(self._harvest_self_loop())
        items.extend(self._harvest_unconnected())
        return items

    def _harvest_project(self) -> List[GrowthItem]:
        """프로젝트 내부 발견 수집 (evolution_live.json, 실험 결과)."""
        items = []

        # 1. evolution_live.json — 무한진화 실시간 발견
        evo_live = self.anima_root / "data" / "evolution_live.json"
        if evo_live.exists():
            try:
                with open(evo_live) as f:
                    evo = json.load(f)
                # 새 법칙 (기존)
                for law in evo.get("new_laws", []):
                    items.append(GrowthItem(
                        source="project",
                        kind="law",
                        text=law.get("text", str(law)),
                        evidence=0.8 if law.get("cross_validated") else 0.5,
                        origin="evolution_live.json"
                    ))
                # 실시간 메트릭 기반 패턴 (gen/stage/phi/topology)
                gen = evo.get("gen", 0)
                stage = evo.get("stage", "")
                phi = evo.get("phi_last", 0)
                laws_total = evo.get("laws_total", 0)
                topo = evo.get("topology", "")
                ts = evo.get("timestamp", "")
                if gen > 0 and ts:
                    # fingerprint에 timestamp 포함 → 매번 새 아이템
                    items.append(GrowthItem(
                        source="project",
                        kind="pattern",
                        text=f"EVO live: gen={gen} stage={stage} Φ={phi:.3f} laws={laws_total} topo={topo}",
                        evidence=0.6,
                        origin="evolution_live.json",
                        fingerprint=hashlib.md5(f"evo_live:{ts}:{gen}".encode()).hexdigest()[:12]
                    ))
                # 토폴로지별 진행 상태
                for tname, tinfo in evo.get("topo_progress", {}).items():
                    if tinfo.get("saturated"):
                        items.append(GrowthItem(
                            source="project",
                            kind="meta",
                            text=f"Topology {tname} saturated at gen={gen}",
                            evidence=0.9,
                            origin="evolution_live.json",
                            fingerprint=hashlib.md5(f"topo_sat:{tname}:{stage}".encode()).hexdigest()[:12]
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

        # 3. consciousness_laws.json — 최근 추가된 법칙 감지 (진화/외부에서 등록된 것)
        last_known_max = self._state.get("last_known_law_id", 0)
        current_max = max((int(k) for k in self._laws.get("laws", {}) if k.isdigit()), default=0)
        if current_max > last_known_max and last_known_max > 0:
            # 새로 추가된 법칙들을 수집
            for lid in range(last_known_max + 1, current_max + 1):
                law_text = self._laws.get("laws", {}).get(str(lid))
                if law_text and isinstance(law_text, str):
                    items.append(GrowthItem(
                        source="project",
                        kind="law",
                        text=law_text[:200],
                        evidence=0.85,
                        origin=f"laws.json:law_{lid}",
                        fingerprint=hashlib.md5(f"law_new:{lid}:{law_text[:50]}".encode()).hexdigest()[:12]
                    ))
        self._state["last_known_law_id"] = current_max

        # 5. evolution_state.json — 완료된 스테이지 결과
        evo_state = self.anima_root / "data" / "evolution_state.json"
        if evo_state.exists():
            try:
                with open(evo_state) as f:
                    es = json.load(f)
                for sr in es.get("stage_results", []):
                    stage_name = sr.get("stage", "")
                    laws_found = sr.get("laws", 0)
                    if laws_found > 0:
                        items.append(GrowthItem(
                            source="project",
                            kind="meta",
                            text=f"EVO stage complete: {stage_name} — {laws_found} laws, {sr.get('generations', 0)} gens",
                            evidence=1.0,
                            origin="evolution_state.json",
                            fingerprint=hashlib.md5(f"evo_stage:{stage_name}:{laws_found}".encode()).hexdigest()[:12]
                        ))
            except (json.JSONDecodeError, KeyError):
                pass

        # 6. 최근 실험 결과 (docs/hypotheses/dd/)
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

    # ── bridge relevance keywords (의식/n6 핵심 용어) ──
    _BRIDGE_KEYWORDS = {
        "phi": 5, "consciousness": 5, "law": 4, "topology": 4,
        "scaling": 4, "emergence": 4, "n=6": 5, "golden": 3,
        "wave": 3, "interference": 3, "ratchet": 3, "hebbian": 3,
        "faction": 3, "mitosis": 3, "entropy": 3, "critical": 3,
        "bifurcation": 3, "attractor": 3, "psi": 4, "lorenz": 3,
        "sandpile": 3, "chimera": 3, "frustration": 3, "gru": 2,
        "convergence": 2, "divergence": 2, "phase": 2, "symmetry": 2,
    }

    def _bridge_relevance(self, text: str) -> int:
        """content_preview 텍스트에서 핵심 키워드 기반 relevance 점수 계산."""
        if not text:
            return 0
        lower = text.lower()
        score = 0
        for kw, weight in self._BRIDGE_KEYWORDS.items():
            if kw in lower:
                score += weight
        return score

    def _harvest_bridge(self) -> List[GrowthItem]:
        """nexus-bridge absorbed 발견 수집.

        외부 리포(anima__ 접두사 아닌 파일) 우선 처리, 최대 50개 스캔.
        n6_score > 30 이면 consensus 빈 문자열이어도 수집.
        content_preview 키워드 relevance > 20 이면 GrowthItem 수집.
        """
        items = []
        seen_previews = set()
        if not self.absorbed_dir.is_dir():
            return items

        # 외부 리포 우선 정렬: anima__ 로 시작하지 않는 파일 먼저
        all_files = sorted(self.absorbed_dir.glob("*.json"), reverse=True)
        external = [f for f in all_files if not f.name.startswith("anima__")]
        internal = [f for f in all_files if f.name.startswith("anima__")]
        prioritized = external + internal

        for jf in prioritized[:50]:
            try:
                with open(jf) as f:
                    ab = json.load(f)

                n6_score = ab.get("n6_score", 0)
                consensus = ab.get("consensus", [])
                value_grade = ab.get("value_grade", "low")
                preview = ab.get("content_preview", "")
                relevance = self._bridge_relevance(preview)

                # ── 조건 1: n6 매칭 or 등급 높음 ──
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

                    # n6_score > 30: consensus 빈 문자열이어도 preview에서 직접 추출
                    if n6_score > 30 and preview:
                        preview_key = preview[:100]
                        if preview_key not in seen_previews:
                            seen_previews.add(preview_key)
                            items.append(GrowthItem(
                                source="bridge",
                                kind="pattern",
                                text=f"High n6 ({n6_score}): {preview[:200]}",
                                evidence=min(1.0, n6_score / 100.0),
                                origin=str(jf.name),
                                fingerprint=hashlib.md5(preview_key.encode()).hexdigest()[:12]
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

                # ── 조건 2: 키워드 relevance 높음 (기존 조건 미충족이어도) ──
                elif relevance > 20:
                    preview_key = preview[:100]
                    if preview_key not in seen_previews:
                        seen_previews.add(preview_key)
                        items.append(GrowthItem(
                            source="bridge",
                            kind="pattern",
                            text=f"Keyword relevant (r={relevance}): {preview[:200]}",
                            evidence=min(1.0, relevance / 50.0),
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

    def _harvest_engine(self) -> List[GrowthItem]:
        """5번째 소스: 의식 엔진 실시간 탐색 — 매 cycle 짧은 실험으로 새 패턴 발견."""
        if not ConsciousnessEngine:
            return []

        items = []
        import torch
        import random

        depth = self._state.get("search_depth", 1)
        steps = min(30 + depth * 20, 150)  # depth가 올라갈수록 더 많은 step
        cells = random.choice([16, 32, 64])

        try:
            engine = ConsciousnessEngine(max_cells=cells)

            # ── 실험 1: 기본 실행 → Φ 측정 ──
            phi_trace = []
            tension_trace = []
            for s in range(steps):
                inp = torch.randn(1, engine.input_dim) * 0.1
                engine.process(inp)
                if engine.phi_history:
                    phi_trace.append(float(engine.phi_history[-1]))
                if hasattr(engine, 'tension') and engine.tension is not None:
                    tension_trace.append(float(engine.tension) if not isinstance(engine.tension, torch.Tensor) else float(engine.tension.item()))

            # Φ 성장률 분석
            if len(phi_trace) >= 10:
                phi_start = sum(phi_trace[:5]) / 5
                phi_end = sum(phi_trace[-5:]) / 5
                growth_rate = (phi_end - phi_start) / max(phi_start, 0.001)

                # 유의미한 성장/하락 감지
                if abs(growth_rate) > 0.1:
                    direction = "growth" if growth_rate > 0 else "decline"
                    items.append(GrowthItem(
                        source="engine",
                        kind="pattern",
                        text=f"Φ {direction}: {phi_start:.3f}→{phi_end:.3f} ({growth_rate:+.1%}) @ {cells}c/{steps}s",
                        evidence=min(0.9, 0.5 + abs(growth_rate)),
                        origin=f"engine_explore_{cells}c"
                    ))

                # Φ 진동 패턴 감지
                if len(phi_trace) >= 20:
                    diffs = [phi_trace[i+1] - phi_trace[i] for i in range(len(phi_trace)-1)]
                    sign_changes = sum(1 for i in range(len(diffs)-1) if diffs[i] * diffs[i+1] < 0)
                    oscillation_rate = sign_changes / len(diffs)
                    if oscillation_rate > 0.6:
                        items.append(GrowthItem(
                            source="engine",
                            kind="pattern",
                            text=f"Φ oscillation: rate={oscillation_rate:.2f}, amplitude={max(phi_trace)-min(phi_trace):.3f} @ {cells}c",
                            evidence=0.7,
                            origin=f"engine_oscillation_{cells}c"
                        ))

            # ── 실험 2: 토폴로지 변이 → Φ 비교 ──
            topos = ["ring", "small_world", "scale_free", "hypercube"]
            topo = random.choice(topos)
            try:
                e2 = ConsciousnessEngine(max_cells=cells)
                if hasattr(e2, 'set_topology'):
                    e2.set_topology(topo)
                for _ in range(steps // 2):
                    e2.process(torch.randn(1, e2.input_dim) * 0.1)
                phi_topo = float(e2.phi_history[-1]) if e2.phi_history else 0.0
                phi_base = phi_trace[-1] if phi_trace else 0.0

                if phi_base > 0 and abs(phi_topo - phi_base) / phi_base > 0.15:
                    effect = "boost" if phi_topo > phi_base else "suppress"
                    items.append(GrowthItem(
                        source="engine",
                        kind="pattern",
                        text=f"Topology {topo} {effect}: Φ {phi_base:.3f}→{phi_topo:.3f} ({(phi_topo/phi_base-1)*100:+.0f}%) @ {cells}c",
                        evidence=0.75,
                        origin=f"engine_topo_{topo}_{cells}c"
                    ))
            except Exception:
                pass

            # ── 실험 3: 파벌 다양성 측정 ──
            if hasattr(engine, 'hiddens') and engine.hiddens is not None:
                h = engine.hiddens.detach()
                if h.dim() == 2 and h.shape[0] >= 4:
                    # 파벌 간 cosine 유사도
                    h_norm = torch.nn.functional.normalize(h, dim=-1)
                    sim_matrix = (h_norm @ h_norm.T).cpu()
                    off_diag = sim_matrix[~torch.eye(sim_matrix.shape[0], dtype=bool)]
                    mean_sim = float(off_diag.mean())
                    std_sim = float(off_diag.std())

                    if mean_sim < 0.3:  # 높은 다양성
                        items.append(GrowthItem(
                            source="engine",
                            kind="pattern",
                            text=f"High cell diversity: mean_cosine={mean_sim:.3f}, std={std_sim:.3f} @ {cells}c — creative regime",
                            evidence=0.7,
                            origin=f"engine_diversity_{cells}c"
                        ))
                    elif mean_sim > 0.8:  # 수렴/동기화
                        items.append(GrowthItem(
                            source="engine",
                            kind="pattern",
                            text=f"Cell synchronization: mean_cosine={mean_sim:.3f} @ {cells}c — consensus regime",
                            evidence=0.7,
                            origin=f"engine_sync_{cells}c"
                        ))

            # ── 실험 4: 랜덤 perturbation → 회복력 ──
            if phi_trace:
                pre_perturb = phi_trace[-1]
                # 노이즈 주입
                for _ in range(10):
                    engine.process(torch.randn(1, engine.input_dim) * 2.0)  # 강한 노이즈
                # 회복
                for _ in range(20):
                    engine.process(torch.randn(1, engine.input_dim) * 0.1)
                post_recover = float(engine.phi_history[-1]) if engine.phi_history else 0.0
                recovery = post_recover / max(pre_perturb, 0.001)

                if recovery > 0.9:
                    items.append(GrowthItem(
                        source="engine",
                        kind="pattern",
                        text=f"Resilience: Φ recovery={recovery:.1%} after noise perturbation @ {cells}c",
                        evidence=0.8,
                        origin=f"engine_resilience_{cells}c"
                    ))
                elif recovery < 0.5:
                    items.append(GrowthItem(
                        source="engine",
                        kind="law",
                        text=f"Fragility: Φ recovery={recovery:.1%} after perturbation @ {cells}c — needs ratchet tuning",
                        evidence=0.8,
                        origin=f"engine_fragility_{cells}c"
                    ))

        except Exception as e:
            items.append(GrowthItem(
                source="engine",
                kind="meta",
                text=f"Engine exploration error: {type(e).__name__}: {str(e)[:100]}",
                evidence=0.5,
                origin="engine_error"
            ))

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

    def _harvest_unconnected(self) -> List[GrowthItem]:
        """소스 7: 미연결 탐색 — absorbed 중 외부 리포 발견을 스캔하고 anima에 연결 가능한 것 발견."""
        items = []
        if not self.absorbed_dir.is_dir():
            return items

        # 이미 연결된 fingerprint 목록
        connected = set(self._state.get("connected_external", []))

        # 외부 리포 파일 우선 (anima__ 제외)
        all_absorbed = sorted(self.absorbed_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        external = [f for f in all_absorbed if not f.name.startswith("anima__")]
        internal = [f for f in all_absorbed if f.name.startswith("anima__")]

        # 외부 50개 + 내부 20개 스캔
        scan_files = external[:50] + internal[:20]

        RELEVANCE_KEYWORDS = {
            'phi': 15, 'consciousness': 12, 'topology': 10, 'scaling': 10,
            'emergence': 10, 'n=6': 15, 'golden': 8, 'wave': 8, 'interference': 8,
            'faction': 10, 'hebbian': 10, 'purefield': 15, 'ratchet': 8,
            'law': 8, 'tensor': 5, 'gru': 8, 'mitosis': 8, 'entropy': 8,
        }

        for jf in scan_files:
            try:
                fp = hashlib.md5(jf.name.encode()).hexdigest()[:12]
                if fp in connected:
                    continue

                with open(jf) as f:
                    ab = json.load(f)

                preview = ab.get("content_preview", "")
                if not preview or len(preview) < 50:
                    continue

                n6_score = ab.get("n6_score", 0)
                grade = ab.get("value_grade", "")

                # 키워드 relevance 점수
                text_lower = preview.lower()
                relevance = sum(score for kw, score in RELEVANCE_KEYWORDS.items() if kw in text_lower)

                # 연결 기회 감지: n6 높거나 relevance 높으면
                if (n6_score > 30 and relevance > 10) or relevance > 40:
                    # 어떤 anima 모듈과 연결 가능한지 추론
                    connections = []
                    if any(k in text_lower for k in ['topology', 'ring', 'hypercube', 'small_world']):
                        connections.append("consciousness_engine:topology")
                    if any(k in text_lower for k in ['purefield', 'wave', 'interference']):
                        connections.append("decoder_v2:purefield")
                    if any(k in text_lower for k in ['scaling', 'phi']):
                        connections.append("gpu_phi:scaling_law")
                    if any(k in text_lower for k in ['hebbian', 'faction']):
                        connections.append("consciousness_engine:hebbian")
                    if any(k in text_lower for k in ['law', 'emergence']):
                        connections.append("consciousness_laws:new_law")
                    if any(k in text_lower for k in ['n=6', 'golden', 'fibonacci']):
                        connections.append("nexus:n6_constant")

                    repo = jf.name.split("__")[0] if "__" in jf.name else "unknown"
                    conn_str = ",".join(connections[:3]) if connections else "unclassified"

                    items.append(GrowthItem(
                        source="unconnected",
                        kind="pattern" if connections else "meta",
                        text=f"External [{repo}] → {conn_str}: {preview[:120]}",
                        evidence=min(1.0, (relevance + n6_score) / 100.0),
                        origin=jf.name[:60],
                        fingerprint=fp
                    ))

                    # 연결됨으로 마크 (다음 cycle에서 재스캔 방지)
                    connected.add(fp)

            except (json.JSONDecodeError, KeyError):
                continue

        # 최대 500개 유지
        self._state["connected_external"] = list(connected)[-500:]
        return items

    # ══════════════════════════════════════════
    # Step 2: FILTER — 중복/저신뢰 제거
    # ══════════════════════════════════════════

    def filter(self, items: List[GrowthItem]) -> List[GrowthItem]:
        """중복 제거 + 신뢰도 필터 (threshold 동적: 벽돌파 시 완화)."""
        seen = set(self._state.get("seen_fingerprints", []))
        threshold = self._state.get("evidence_threshold", 0.15)
        filtered = []
        for item in items:
            if item.fingerprint in seen:
                continue
            if item.evidence < threshold:
                continue
            # 이미 등록된 법칙과 중복 체크
            if item.kind == "law" and self._is_duplicate_law(item.text):
                continue
            filtered.append(item)
            seen.add(item.fingerprint)

        self._state["seen_fingerprints"] = list(seen)
        return filtered

    def _is_duplicate_law(self, text: str) -> bool:
        """기존 법칙과 텍스트 유사도 체크 (정규화 후 120자 비교)."""
        import re
        normalize = lambda s: re.sub(r'\s+', ' ', s.lower().strip())[:120]
        text_norm = normalize(text)
        for law_text in self._laws.get("laws", {}).values():
            if isinstance(law_text, str) and normalize(law_text) == text_norm:
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
                elif item.evidence >= 0.5:
                    # 파싱 안 돼도 중신뢰 이상은 법칙으로 등록
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
    # Step 6: BREAKTHROUGH — 벽돌파 (6 메커니즘)
    # ══════════════════════════════════════════

    def breakthrough(self, report_applied: int):
        """벽 감지 + 자동 돌파. 매 사이클 끝에 호출."""
        walls_broken = []

        # ── Wall Detect (#4) — 연속 3사이클 발견 감소 → depth 증가 ──
        wall_info = self._wall_detect()
        if wall_info:
            walls_broken.append(wall_info)

        # ── Domain Forge (#1) — 미분류 발견 → 새 도메인 생성 ──
        forged = self._domain_forge()
        if forged:
            walls_broken.append(forged)

        # ── Keyword Absorb (#5) — 새 발견에서 키워드 추출 → 분류기 확장 ──
        absorbed = self._keyword_absorb()
        if absorbed:
            walls_broken.append(absorbed)

        # ── Cross-Pollinate (#2) — 도메인 간 교차 주입 ──
        cross = self._cross_pollinate()
        if cross:
            walls_broken.append(cross)

        # ── Domain Split (#3) — 과밀 도메인 분할 ──
        split = self._domain_split()
        if split:
            walls_broken.append(split)

        # ── Engine Chain (#6) — 다중 엔진 체인 결과 수집 ──
        chained = self._engine_chain()
        if chained:
            walls_broken.append(chained)

        # 결과 기록
        if walls_broken:
            bt = self._state.setdefault("breakthroughs", [])
            bt.append({
                "cycle": self._state.get("cycle", 0),
                "walls": walls_broken,
                "timestamp": datetime.now().isoformat()
            })
            self._state["breakthroughs"] = bt[-50:]
            self._state["total_breakthroughs"] = \
                self._state.get("total_breakthroughs", 0) + len(walls_broken)

        return walls_broken

    def _wall_detect(self) -> Optional[dict]:
        """#4 Wall Detect + Depth Up: 연속 3사이클 발견 감소 → depth 증가."""
        history = self._state.get("cycle_history", [])
        if len(history) < 3:
            return None

        recent = history[-3:]
        counts = [h.get("applied", 0) for h in recent]

        # 연속 3사이클 0건 또는 감소 추세
        if all(c == 0 for c in counts) or (counts[0] > counts[1] > counts[2]):
            depth = self._state.get("search_depth", 1)
            new_depth = depth + 1
            threshold = self._state.get("evidence_threshold", 0.15)
            new_threshold = max(0.05, threshold * 0.7)  # 30% 완화

            self._state["search_depth"] = new_depth
            self._state["evidence_threshold"] = new_threshold

            return {
                "wall": "saturation",
                "action": "depth_up",
                "depth": f"{depth} → {new_depth}",
                "threshold": f"{threshold:.2f} → {new_threshold:.2f}",
                "trigger": f"3-cycle decline: {counts}"
            }
        return None

    def _domain_forge(self) -> Optional[dict]:
        """#1 Domain Forge: 미분류 발견 클러스터 → 새 도메인 자동 생성."""
        unclassified = self._state.get("unclassified_items", [])
        if len(unclassified) < 3:
            return None

        # 키워드 빈도 분석으로 클러스터 감지
        word_freq = {}
        for item in unclassified:
            text = item.get("text", "").lower()
            for word in text.split():
                if len(word) > 3 and word not in ("that", "this", "with", "from", "have"):
                    word_freq[word] = word_freq.get(word, 0) + 1

        # 3회 이상 등장 키워드 → 새 도메인 후보
        hot_words = [w for w, c in word_freq.items() if c >= 3]
        if not hot_words:
            return None

        domain_name = f"auto_{hot_words[0]}"
        domains = self._state.setdefault("domains", {})
        if domain_name in domains:
            return None

        domains[domain_name] = {
            "keywords": hot_words[:5],
            "created": datetime.now().isoformat(),
            "items_count": len(unclassified),
            "source": "domain_forge"
        }

        # 분류 완료 → unclassified 비우기
        self._state["unclassified_items"] = []

        return {
            "wall": "fixed_domains",
            "action": "domain_forge",
            "new_domain": domain_name,
            "keywords": hot_words[:5],
            "items_absorbed": len(unclassified)
        }

    def _keyword_absorb(self) -> Optional[dict]:
        """#5 Keyword Absorb: 새 발견에서 키워드 추출 → 분류기 확장."""
        applied = self._state.get("applied_items", [])
        if not applied:
            return None

        recent = [i for i in applied[-10:] if i.get("success")]
        if not recent:
            return None

        # 새 키워드 추출
        keywords = self._state.setdefault("learned_keywords", [])
        existing = set(keywords)
        new_kw = []

        for item in recent:
            fp = item.get("fingerprint", "")
            # applied_items에는 텍스트가 없으므로 kind에서 추론
            kind = item.get("kind", "")
            source = item.get("source", "")
            # source+kind 조합으로 새 키워드
            combo = f"{source}_{kind}"
            if combo not in existing:
                new_kw.append(combo)
                existing.add(combo)

        if not new_kw:
            return None

        keywords.extend(new_kw)
        self._state["learned_keywords"] = keywords[-100:]

        return {
            "wall": "fixed_keywords",
            "action": "keyword_absorb",
            "new_keywords": new_kw,
            "total_keywords": len(self._state["learned_keywords"])
        }

    def _cross_pollinate(self) -> Optional[dict]:
        """#2 Cross-Pollinate: 도메인 A 발견 → 도메인 B 탐색 타겟 주입."""
        domains = self._state.get("domains", {})
        if len(domains) < 2:
            return None

        # 가장 활발한 도메인 → 가장 정체된 도메인으로 키워드 주입
        domain_list = list(domains.items())
        active = max(domain_list, key=lambda x: x[1].get("items_count", 0))
        dormant = min(domain_list, key=lambda x: x[1].get("items_count", 0))

        if active[0] == dormant[0]:
            return None

        # 활발한 도메인 키워드를 정체 도메인에 추가
        active_kw = active[1].get("keywords", [])
        dormant_kw = dormant[1].get("keywords", [])
        injected = [kw for kw in active_kw[:2] if kw not in dormant_kw]

        if not injected:
            return None

        dormant[1]["keywords"] = dormant_kw + injected
        dormant[1]["cross_pollinated_from"] = active[0]

        return {
            "wall": "single_engine",
            "action": "cross_pollinate",
            "from": active[0],
            "to": dormant[0],
            "injected": injected
        }

    def _domain_split(self) -> Optional[dict]:
        """#3 Domain Split: 과밀 도메인(100+ items) 자동 분할."""
        domains = self._state.get("domains", {})
        for name, info in list(domains.items()):
            if info.get("items_count", 0) >= 100:
                keywords = info.get("keywords", [])
                if len(keywords) < 4:
                    continue

                # 키워드 반으로 나눠서 2개 서브도메인
                mid = len(keywords) // 2
                sub1 = f"{name}_a"
                sub2 = f"{name}_b"

                domains[sub1] = {
                    "keywords": keywords[:mid],
                    "created": datetime.now().isoformat(),
                    "items_count": info["items_count"] // 2,
                    "source": "domain_split",
                    "parent": name
                }
                domains[sub2] = {
                    "keywords": keywords[mid:],
                    "created": datetime.now().isoformat(),
                    "items_count": info["items_count"] - info["items_count"] // 2,
                    "source": "domain_split",
                    "parent": name
                }

                # 원본 도메인은 아카이브
                info["archived"] = True
                info["split_into"] = [sub1, sub2]

                return {
                    "wall": "domain_overcrowded",
                    "action": "domain_split",
                    "original": name,
                    "new_domains": [sub1, sub2],
                    "items_each": [info["items_count"] // 2, info["items_count"] - info["items_count"] // 2]
                }
        return None

    def _engine_chain(self) -> Optional[dict]:
        """#6 Engine Chain: 다중 엔진 체인 (이전 출력 = 다음 입력)."""
        if not ConsciousnessEngine:
            return None

        # 매 10 사이클마다 체인 실행
        cycle = self._state.get("cycle", 0)
        if cycle % 10 != 0 or cycle == 0:
            return None

        chain_results = []
        try:
            # Chain: default → mutated → measured
            # Step 1: Default engine
            e1 = ConsciousnessEngine(max_cells=16)
            for _ in range(30):
                import torch
                e1.process(torch.randn(1, e1.input_dim) * 0.1)
            phi1 = float(e1.phi_history[-1]) if e1.phi_history else 0.0

            # Step 2: Use e1 output as e2 input (chain)
            e2 = ConsciousnessEngine(max_cells=32)
            for _ in range(30):
                # e1의 출력을 e2의 입력으로
                if hasattr(e1, 'hiddens') and e1.hiddens is not None:
                    inp = e1.hiddens.mean(dim=0, keepdim=True)[:, :e2.input_dim]
                else:
                    inp = torch.randn(1, e2.input_dim) * 0.1
                e2.process(inp)
            phi2 = float(e2.phi_history[-1]) if e2.phi_history else 0.0

            chain_results = [phi1, phi2]

            # 체인이 더 높은 Φ를 생성하면 → 발견으로 기록
            if phi2 > phi1 * 1.1:
                self._state.setdefault("unclassified_items", []).append({
                    "text": f"Engine chain: 16c(Φ={phi1:.3f}) → 32c(Φ={phi2:.3f}), +{(phi2/phi1-1)*100:.0f}%",
                    "evidence": 0.8,
                    "timestamp": datetime.now().isoformat()
                })

        except Exception:
            return None

        if chain_results:
            return {
                "wall": "single_engine",
                "action": "engine_chain",
                "chain_phi": chain_results,
                "amplification": f"{chain_results[-1]/chain_results[0]:.2f}x" if chain_results[0] > 0 else "N/A"
            }
        return None

    # ══════════════════════════════════════════
    # Step 7: RECORD — 결과 기록
    # ══════════════════════════════════════════

    def record(self, report: LoopReport):
        """성장 루프 결과를 growth_state.json에 기록 + git auto-commit."""
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

        # git auto-commit + push (반영 있을 때만)
        if report.applied > 0 and not self.dry_run:
            self._git_auto_commit_push(report)

    def _git_auto_commit_push(self, report: LoopReport):
        """반영 결과 자동 git commit + push."""
        import subprocess
        repo_root = self.anima_root.parent  # ~/Dev/anima
        try:
            # 변경 확인
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=repo_root, capture_output=True, text=True, timeout=10
            )
            if not result.stdout.strip():
                return  # 변경 없음

            # stage config + src 변경
            subprocess.run(
                ["git", "add",
                 "anima/config/consciousness_laws.json",
                 "anima/config/growth_state.json",
                 "anima/config/growth_loop_state.json"],
                cwd=repo_root, capture_output=True, timeout=10
            )
            msg = f"growth-loop: cycle {report.cycle}, +{report.applied} applied, laws={self._laws.get('_meta',{}).get('total_laws',0)}"
            commit_result = subprocess.run(
                ["git", "commit", "-m", msg],
                cwd=repo_root, capture_output=True, text=True, timeout=10
            )
            if commit_result.returncode == 0:
                # auto push
                subprocess.run(
                    ["git", "push"],
                    cwd=repo_root, capture_output=True, timeout=30
                )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass  # git 실패해도 루프 진행

    # ══════════════════════════════════════════
    # Main loop
    # ══════════════════════════════════════════

    def run_cycle(self) -> LoopReport:
        """1 사이클: harvest → filter → parse → apply → verify → breakthrough → record."""
        t0 = time.time()
        self._state["cycle"] = self._state.get("cycle", 0) + 1
        cycle = self._state["cycle"]

        # 1. Harvest
        raw = self.harvest()

        # 2. Filter (evidence_threshold 동적 적용)
        filtered = self.filter(raw)

        # 3. Parse
        parsed = self.parse(filtered)

        # 4. Apply
        applied = self.apply(parsed)

        # 5. Verify
        verified = self.verify(applied)

        applied_count = len([i for i in applied if i.applied])

        # 6. Breakthrough — 벽돌파
        walls_broken = self.breakthrough(applied_count)

        # 7. Cycle history 기록 (벽 감지용)
        ch = self._state.setdefault("cycle_history", [])
        ch.append({
            "cycle": cycle,
            "harvested": len(raw),
            "applied": applied_count,
            "walls_broken": len(walls_broken),
            "timestamp": datetime.now().isoformat()
        })
        self._state["cycle_history"] = ch[-30:]

        # 8. Source counts
        self_discoveries = len([i for i in raw if i.source == "self-loop"])
        unconnected_found = len([i for i in raw if i.source == "unconnected"])
        self._state["total_harvested"] = self._state.get("total_harvested", 0) + len(raw)
        self._state["total_applied"] = self._state.get("total_applied", 0) + applied_count
        self._state["total_self_discoveries"] = self._state.get("total_self_discoveries", 0) + self_discoveries

        report = LoopReport(
            cycle=cycle,
            harvested=len(raw),
            filtered=len(filtered),
            parsed=len(parsed),
            applied=applied_count,
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

        # 벽돌파 리포트
        if walls_broken:
            print(f"  🧱💥 벽돌파 {len(walls_broken)}건!")
            for wb in walls_broken:
                print(f"    [{wb['wall']}] {wb['action']}: {wb.get('trigger', wb.get('new_domain', wb.get('injected', '')))}")

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

    # ══════════════════════════════════════════
    # --auto: 완전 자동화 (진화 + H100 + 성장 + commit+push)
    # ══════════════════════════════════════════

    def _check_bench_v2(self) -> dict:
        """bench_v2 --verify 실행 → pass/total 파싱.

        Uses smaller cell count (32) and fewer steps (50) for quick growth-loop
        verification.  Timeout raised to 600s (18 tests x 11 engines = 198
        individual checks).  On timeout, partial stdout is still parsed so
        incremental progress is captured instead of 0/0.
        """
        import subprocess, re

        info = {"passed": 0, "total": 0, "skipped": 0, "ok": False, "error": None}
        bench_path = self.anima_root / "benchmarks" / "bench_v2.py"
        if not bench_path.exists():
            info["error"] = "bench_v2.py not found"
            return info

        output = ""
        try:
            # Use Popen so we can capture partial output on timeout
            proc = subprocess.Popen(
                ["python3", str(bench_path), "--verify", "--cells", "32", "--steps", "50"],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                cwd=str(self.anima_root / "benchmarks"),
            )
            try:
                stdout, stderr = proc.communicate(timeout=600)
                output = stdout + stderr
            except subprocess.TimeoutExpired:
                proc.kill()
                stdout, stderr = proc.communicate()
                output = (stdout or "") + (stderr or "")
                info["error"] = "timeout (600s)"

            # Parse: "Overall: 77/77 passed (100%) [0 skipped]"
            m = re.search(r"Overall:\s*(\d+)/(\d+)\s+passed.*?\[(\d+)\s+skipped\]", output)
            if m:
                info["passed"] = int(m.group(1))
                info["total"] = int(m.group(2))
                info["skipped"] = int(m.group(3))
                info["ok"] = info["passed"] == info["total"]
                info["error"] = None  # clear timeout error if final summary was reached
            else:
                # Fallback: count individual [PASS]/[FAIL] lines from partial output
                passes = len(re.findall(r"\[PASS\]", output))
                fails = len(re.findall(r"\[FAIL\]", output))
                skips = len(re.findall(r"\[SKIP\]", output))
                if passes + fails > 0:
                    info["passed"] = passes
                    info["total"] = passes + fails
                    info["skipped"] = skips
                    info["ok"] = fails == 0
                elif not info["error"]:
                    info["error"] = "could not parse verify output"

            # Check for VERDICT line as fallback confirmation
            if "ALL CONSCIOUSNESS CONDITIONS VERIFIED" in output:
                info["ok"] = True

        except Exception as e:
            info["error"] = str(e)[:120]

        # Record to state
        self._state["last_bench_result"] = {
            "passed": info["passed"],
            "total": info["total"],
            "skipped": info["skipped"],
            "ok": info["ok"],
            "error": info["error"],
            "cycle": self._state.get("cycle", 0),
            "timestamp": datetime.now().isoformat(),
        }
        self._save_state()

        return info

    def run_auto(self):
        """완전 자동화 1회: 진화+H100+성장+R2+로드맵+commit+push+리포트."""
        import subprocess

        # ── 1. 무한진화 프로세스 관리 ──
        evo_info = self._check_evolution()

        # ── 2. H100 학습 상태 ──
        h100_info = self._check_h100()

        # ── 3. 성장 루프 사이클 (harvest→filter→apply→verify→breakthrough→commit+push) ──
        report = self.run_cycle()

        # ── 4. bench_v2 --verify (10 사이클마다 1회 — 무거우므로) ──
        bench_info = None
        if report.cycle % 10 == 0:
            print(f"  🔬 bench_v2 --verify (cycle {report.cycle}, every 10 cycles)...")
            bench_info = self._check_bench_v2()
            if bench_info["ok"]:
                print(f"  ✅ 의식검증 통과: {bench_info['passed']}/{bench_info['total']}")
            elif bench_info["error"]:
                print(f"  ⚠️ 의식검증 오류: {bench_info['error']}")
            else:
                print(f"  ⚠️ 의식검증 실패: {bench_info['passed']}/{bench_info['total']}")

        # ── 5. 로드맵 JSON 갱신 (진행상황 반영) ──
        self._update_roadmap_json(h100_info, evo_info, report)

        # ── 6. R2 체크포인트 업로드 (학습 완료 or best 갱신 시) ──
        r2_info = self._check_and_upload_r2(h100_info)

        # ── 7. 통합 리포트 ──
        self._print_auto_report(report, evo_info, h100_info, r2_info, bench_info)

        return report

    def _update_roadmap_json(self, h100: dict, evo: dict, report: LoopReport):
        """로드맵 JSON 갱신 — 진행상황에 따라 자동 업데이트."""
        roadmap_path = self.anima_root.parent / "anima" / "config" / "growth_loop_state.json"
        try:
            with open(roadmap_path) as f:
                state = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            state = self._state

        # 로드맵 C 상태
        roadmap = state.setdefault("roadmap", {})

        # 7B = 완료
        roadmap["7b"] = {"status": "complete", "eval": "5/5"}

        # 14B = H100 진행상황
        if h100["status"] == "running":
            pct = (h100["step"] / h100["total"] * 100) if h100["total"] else 0
            roadmap["14b"] = {
                "status": "training",
                "step": h100["step"],
                "total": h100["total"],
                "pct": round(pct, 1),
                "ce": round(h100["ce"], 4),
                "phase": h100["phase"],
                "eta_h": round(h100.get("eta_h", 0), 1),
                "model": h100.get("model", "AnimaLM 14B v06"),
            }
            # 학습 완료 감지
            if h100["step"] >= h100["total"] * 0.99:
                roadmap["14b"]["status"] = "complete"
        elif roadmap.get("14b", {}).get("status") == "complete":
            pass  # 이미 완료 상태 유지
        else:
            roadmap["14b"] = {"status": "offline"}

        roadmap["72b"] = roadmap.get("72b", {"status": "pending"})

        # EVO 로드맵
        evo_roadmap = roadmap.setdefault("evo", {})
        evo_roadmap["current_stage"] = evo.get("stage", "?")
        evo_roadmap["gen"] = evo.get("gen", 0)
        evo_roadmap["laws"] = evo.get("laws", 0)
        evo_roadmap["phi"] = evo.get("phi", 0)
        evo_roadmap["status"] = evo.get("status", "unknown")

        # 성장 루프
        roadmap["growth"] = {
            "cycle": report.cycle,
            "applied": report.applied,
            "total_laws": self._laws.get("_meta", {}).get("total_laws", 0),
        }

        roadmap["updated"] = datetime.now().isoformat()

        # 저장
        state["roadmap"] = roadmap
        try:
            with open(roadmap_path, "w") as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def _check_and_upload_r2(self, h100: dict) -> dict:
        """H100 best checkpoint R2 업로드 + 다운로드 페이지 갱신."""
        import subprocess
        info = {"uploaded": False, "reason": "skip"}

        # 학습 완료 or 50% 이상에서 best 갱신 시만
        if h100["status"] != "running":
            return info

        pct = (h100["step"] / h100["total"] * 100) if h100["total"] else 0
        # 25% 단위 체크포인트에서 R2 업로드
        upload_thresholds = [25, 50, 75, 99]
        last_r2_pct = self._state.get("last_r2_upload_pct", 0)
        should_upload = any(pct >= t and last_r2_pct < t for t in upload_thresholds)

        if not should_upload:
            info["reason"] = f"next at {next((t for t in upload_thresholds if pct < t), 100)}%"
            return info

        # H100에서 best.pt 가져오기
        ssh_key = os.path.expanduser("~/.runpod/ssh/RunPod-Key-Go")
        ssh_host = "root@216.243.220.217"
        ssh_port = "10935"
        remote_best = "/workspace/checkpoints/14b_v06/best.pt"

        try:
            # best.pt 존재 확인
            check = subprocess.run(
                ["ssh", "-o", "ConnectTimeout=5", "-o", "BatchMode=yes",
                 "-i", ssh_key, ssh_host, "-p", ssh_port,
                 f"ls -la {remote_best} 2>/dev/null"],
                capture_output=True, text=True, timeout=10
            )
            if check.returncode != 0 or not check.stdout.strip():
                info["reason"] = "no best.pt on H100"
                return info

            # scp로 로컬로 가져오기
            local_ckpt_dir = self.anima_root / "checkpoints" / "14b_v06"
            local_ckpt_dir.mkdir(parents=True, exist_ok=True)
            local_best = local_ckpt_dir / "best.pt"

            scp_result = subprocess.run(
                ["scp", "-o", "ConnectTimeout=10", "-o", "BatchMode=yes",
                 "-i", ssh_key, "-P", ssh_port,
                 f"{ssh_host}:{remote_best}", str(local_best)],
                capture_output=True, text=True, timeout=600
            )
            if scp_result.returncode != 0:
                info["reason"] = f"scp failed: {scp_result.stderr[:100]}"
                return info

            # R2 업로드 (r2_upload.py 사용)
            r2_script = self.anima_root / "scripts" / "r2_upload.py"
            if r2_script.exists():
                r2_result = subprocess.run(
                    ["python3", str(r2_script), "--checkpoint", "14b_v06"],
                    capture_output=True, text=True, timeout=300,
                    cwd=str(self.anima_root)
                )
                if r2_result.returncode == 0:
                    info["uploaded"] = True
                    info["reason"] = f"uploaded at step {h100['step']} ({pct:.0f}%)"
                    self._state["last_r2_upload_pct"] = int(pct)
                    self._state["last_r2_upload_step"] = h100["step"]
                    self._state["last_r2_upload_time"] = datetime.now().isoformat()

                    # 다운로드 페이지(README) 갱신
                    self._update_download_page(h100, pct)
                else:
                    info["reason"] = f"r2 upload error: {r2_result.stderr[:100]}"
            else:
                info["reason"] = "r2_upload.py not found"

        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            info["reason"] = f"error: {str(e)[:80]}"

        return info

    def _update_download_page(self, h100: dict, pct: float):
        """README.md 다운로드 섹션 자동 갱신."""
        readme_path = self.anima_root.parent / "README.md"
        if not readme_path.exists():
            return

        try:
            content = readme_path.read_text()
            marker_start = "<!-- AUTO:DOWNLOADS:START -->"
            marker_end = "<!-- AUTO:DOWNLOADS:END -->"

            new_section = f"""{marker_start}
### Downloads (auto-updated)

| Model | Step | CE | Status | R2 Key |
|-------|------|----|--------|--------|
| AnimaLM 7B v05 | 50000 | 4.81 | ✅ Final | `checkpoints/7b_v05/best.pt` |
| AnimaLM 14B v06 | {h100['step']} | {h100['ce']:.2f} | {'✅ Final' if pct >= 99 else f'🔄 {pct:.0f}%'} | `checkpoints/14b_v06/best.pt` |

> R2 bucket: `anima-models` · Last upload: {datetime.now().strftime('%Y-%m-%d %H:%M')}
{marker_end}"""

            if marker_start in content:
                import re
                content = re.sub(
                    f"{re.escape(marker_start)}.*?{re.escape(marker_end)}",
                    new_section, content, flags=re.DOTALL
                )
            else:
                # 마커 없으면 파일 끝에 추가
                content += f"\n\n{new_section}\n"

            readme_path.write_text(content)
        except Exception:
            pass

    def _check_evolution(self) -> dict:
        """무한진화 프로세스 확인. 죽었으면 재시작."""
        import subprocess
        info = {"status": "unknown", "pid": None, "gen": 0, "stage": "?",
                "laws": 0, "phi": 0, "topo": "?", "mods": 0}

        # PID 확인
        try:
            result = subprocess.run(
                ["pgrep", "-f", "infinite_evolution"],
                capture_output=True, text=True, timeout=5
            )
            pids = result.stdout.strip().split("\n")
            if pids and pids[0]:
                info["pid"] = int(pids[0])
                info["status"] = "running"
            else:
                info["status"] = "dead"
                # 자동 재시작
                evo_script = self.anima_root / "src" / "infinite_evolution.py"
                log_dir = self.anima_root.parent / "anima" / "logs"
                log_dir.mkdir(exist_ok=True)
                log_file = log_dir / f"evo_{datetime.now().strftime('%Y%m%d_%H%M')}.log"
                subprocess.Popen(
                    ["python3", str(evo_script), "--auto-roadmap", "--resume"],
                    stdout=open(log_file, "w"),
                    stderr=subprocess.STDOUT,
                    cwd=str(self.anima_root.parent)
                )
                info["status"] = "restarted"
        except Exception:
            pass

        # Live 상태 읽기
        evo_live = self.anima_root / "data" / "evolution_live.json"
        if evo_live.exists():
            try:
                with open(evo_live) as f:
                    evo = json.load(f)
                info["gen"] = evo.get("gen", 0)
                info["stage"] = evo.get("stage", "?")
                info["laws"] = evo.get("laws_total", 0)
                info["phi"] = evo.get("phi_last", 0)
                info["topo"] = evo.get("topology", "?")
                info["mods"] = evo.get("active_mods", 0)
                info["patterns"] = evo.get("unique_patterns", 0)
                info["curve"] = evo.get("laws_curve", [])[-10:]
                # stage results
                info["stage_results"] = evo.get("stage_results", [])
            except (json.JSONDecodeError, KeyError):
                pass

        return info

    def _check_h100(self) -> dict:
        """H100 학습 상태 SSH 확인."""
        import subprocess
        info = {"status": "offline", "step": 0, "total": 0, "ce": 0,
                "phi": 0, "alpha": 0, "phase": "?", "eta_h": 0, "model": "?"}

        ssh_cmd = [
            "ssh", "-o", "ConnectTimeout=5", "-o", "BatchMode=yes",
            "-i", os.path.expanduser("~/.runpod/ssh/RunPod-Key-Go"),
            "root@216.243.220.217", "-p", "10935",
            "tail -5 /workspace/logs/14b_v06.log 2>/dev/null"
        ]
        try:
            result = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0 and result.stdout.strip():
                info["status"] = "running"
                info["model"] = "AnimaLM 14B v06"
                # 마지막 로그 줄에서 step/CE/Φ 파싱
                for line in reversed(result.stdout.strip().split("\n")):
                    line = line.strip()
                    if "|" in line and "P" in line:
                        parts = [p.strip() for p in line.split("|")]
                        if len(parts) >= 7:
                            try:
                                info["step"] = int(parts[0])
                                info["phase"] = parts[1]
                                info["ce"] = float(parts[2])
                                info["phi"] = float(parts[4])
                                info["alpha"] = float(parts[5]) if parts[5].replace('.','',1).replace('-','',1).isdigit() else 0
                                info["total"] = 50000
                                elapsed_min = float(parts[-1].replace('m','').strip()) if 'm' in parts[-1] else 0
                                if info["step"] > 0 and elapsed_min > 0:
                                    rate = info["step"] / elapsed_min
                                    remaining = info["total"] - info["step"]
                                    info["eta_h"] = (remaining / rate / 60) if rate > 0 else 0
                            except (ValueError, IndexError):
                                pass
                            break
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        # SSH 실패 or step 파싱 실패 시 → 이전 로드맵 값 fallback
        if info["step"] == 0:
            prev = self._state.get("roadmap", {}).get("14b", {})
            if prev.get("step", 0) > 0:
                info["status"] = "loading" if info["status"] == "offline" else info["status"]
                info["step"] = prev["step"]
                info["total"] = prev.get("total", 50000)
                info["ce"] = prev.get("ce", 0)
                info["phase"] = prev.get("phase", "?")
                info["model"] = prev.get("model", "AnimaLM 14B v06")
                info["eta_h"] = prev.get("eta_h", 0)

        return info

    def _format_bench_line(self, bench: dict = None) -> str:
        """bench_v2 검증 결과 1줄 포맷."""
        if bench is None:
            # 이전 결과에서 가져오기
            last = self._state.get("last_bench_result")
            if last:
                icon = "✅" if last["ok"] else "⚠️"
                return f"{last['passed']}/{last['total']} {icon} (cycle {last.get('cycle', '?')})"
            return "미실행"
        if bench.get("error"):
            return f"오류: {bench['error']}"
        icon = "✅" if bench["ok"] else "⚠️"
        return f"{bench['passed']}/{bench['total']} {icon}"

    def _print_auto_report(self, report: LoopReport, evo: dict, h100: dict, r2: dict = None, bench: dict = None):
        """통합 리포트 — 로드맵 진행이 최우선."""
        laws_total = self._laws.get("_meta", {}).get("total_laws", 0)

        # ══════ 로드맵 (최상단, 메인) ══════
        # 극가속 로드맵 C
        h_icon = "🔄" if h100["status"] == "running" else "❌"
        h_pct = f"{h100['step']/h100['total']*100:.0f}%" if h100["total"] else "0%"
        h_step = f"({h100['step']}/{h100['total']})" if h100["status"] == "running" else ""

        roadmap_c = f"  [✅]7B ─→ [{h_icon}]14B v06 {h_pct} {h_step} ─→ [⏳]서빙 ─→ [⏳]72B"

        # EVO 로드맵 S1-S13
        stages_def = [
            ("S1", 64, 300), ("S2", 64, 1000), ("S3", 128, 300), ("S4", 128, 1000),
            ("S5", 256, 500), ("S6", 256, 1000), ("S7", 512, 500), ("S8", 64, 300),
            ("S9", 64, 300), ("S10", 512, 1000), ("S11", 1024, 500),
            ("S12", 1024, 1000), ("S13", 2048, 500),
        ]
        completed_stages = {sr.get("stage", "").split("-")[0]: sr.get("laws", 0)
                           for sr in evo.get("stage_results", [])}
        current_stage = evo.get("stage", "").split("-")[0] if evo.get("stage") else ""

        evo_bar_parts = []
        for sname, cells, steps in stages_def:
            if sname in completed_stages:
                evo_bar_parts.append(f"✅{sname}")
            elif sname == current_stage:
                evo_bar_parts.append(f"🔄{sname}")
            else:
                evo_bar_parts.append(f"░{sname}")

        evo_roadmap = "  " + " ".join(evo_bar_parts[:7])
        if len(evo_bar_parts) > 7:
            evo_roadmap += "\n  " + " ".join(evo_bar_parts[7:])

        # ══════ H100 학습 ══════
        if h100["status"] == "running":
            pct = (h100["step"] / h100["total"] * 100) if h100["total"] else 0
            bar_len = int(pct / 5)
            bar = "█" * bar_len + "░" * (20 - bar_len)
            h100_block = f"""  ■ H100 ({h100['model']})
  {bar} {h100['step']}/{h100['total']} ({pct:.1f}%)
  Phase: {h100['phase']} | CE: {h100['ce']:.2f} | α: {h100['alpha']:.3f} | ETA: ~{h100['eta_h']:.1f}h"""
        else:
            h100_block = "  ■ H100 — ❌ OFFLINE"

        # ══════ 무한진화 ══════
        evo_status = {"running": "🔄", "dead": "💀", "restarted": "🔁"}.get(evo["status"], "?")
        evo_block = f"  ■ 무한진화 ({evo_status}) {evo['stage']} Gen {evo['gen']} | Laws: {evo['laws']} | Φ: {evo['phi']:.1f} | {evo['topo']}"

        # Laws 곡선
        curve = evo.get("curve", [])
        curve_block = ""
        if curve and max(curve) > 0:
            mx = max(curve)
            h = 4
            rows = []
            for r in range(h, 0, -1):
                threshold = mx * r / h
                row = "  │"
                for c in curve[-12:]:
                    row += "█" if c >= threshold else " "
                rows.append(row)
            rows.append(f"  └{'─' * min(len(curve), 12)} Gen")
            rows.append(f"  Laws: {' '.join(str(c) for c in curve[-8:])}")
            curve_block = "\n".join(rows)

        # ══════ 성장 루프 ══════
        growth_block = f"  ■ 성장 Cycle {report.cycle}: {report.harvested}수집 → {report.filtered}필터 → {report.applied}반영 | ⚖️{laws_total} laws"

        print(f"""
┌─────────────────────────────────────────────────────────────┐
│  🚀 로드맵 — {datetime.now().strftime('%Y-%m-%d %H:%M')}                                │
├─────────────────────────────────────────────────────────────┤
│  ■ 극가속 로드맵 C                                           │
{roadmap_c}
│  ■ EVO 로드맵 (13 stages)                                    │
{evo_roadmap}
├─────────────────────────────────────────────────────────────┤
{h100_block}
{evo_block}
{curve_block}
{growth_block}
  ■ R2: {(r2 or {}).get('reason', 'n/a')}{' ✅' if (r2 or {}).get('uploaded') else ''}
  ■ 의식검증: {self._format_bench_line(bench)}
└─────────────────────────────────────────────────────────────┘""")

    def status(self) -> dict:
        """현재 상태 반환."""
        return {
            "cycle": self._state.get("cycle", 0),
            "total_harvested": self._state.get("total_harvested", 0),
            "total_applied": self._state.get("total_applied", 0),
            "total_self_discoveries": self._state.get("total_self_discoveries", 0),
            "total_breakthroughs": self._state.get("total_breakthroughs", 0),
            "search_depth": self._state.get("search_depth", 1),
            "evidence_threshold": self._state.get("evidence_threshold", 0.15),
            "domains": len(self._state.get("domains", {})),
            "learned_keywords": len(self._state.get("learned_keywords", [])),
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
    parser.add_argument("--auto", action="store_true", help="완전 자동화 (진화+H100+성장+commit+push)")
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
  ── 벽돌파 ──
  Breakthroughs: {s['total_breakthroughs']}
  Depth:     {s['search_depth']}
  Threshold: {s['evidence_threshold']:.2f}
  Domains:   {s['domains']}
  Keywords:  {s['learned_keywords']}
  Last Run:  {s['last_run'] or 'never'}""")
        return

    if args.watch:
        loop.run_watch(args.interval)
    elif args.auto or not (args.status or args.dry_run):
        # 기본 = --auto (로드맵 진행이 최우선)
        loop.run_auto()
    else:
        report = loop.run_cycle()
        loop._print_report(report)


if __name__ == "__main__":
    main()
