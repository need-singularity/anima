#!/usr/bin/env python3
"""peak_growth.py — Peak Growth Capture/Replay Engine

최고 성장 조건을 포착하고, 성장이 정체되면 재현한다.
NEXUS-6과 양방향 전파: 상위(anima→nexus6), 하위(nexus6→anima).

"성장의 순간을 기억하라 — 정체의 순간에 되살린다."

Usage:
    from peak_growth import PeakGrowthEngine, PeakCondition

    engine = PeakGrowthEngine()
    engine.record(metrics)           # 매 세대 기록
    if engine.detect_stall():        # 정체 감지
        peak = engine.suggest_replay()
        engine.replay_to_engine(consciousness_engine, peak)

    # NEXUS-6 양방향 전파
    engine.propagate_up(peak)        # anima → nexus6
    events = engine.propagate_down() # nexus6 → anima
    delta = engine.sync_as_growth()  # 동기화 = 성장

Hub keywords: peak, 최고성장, peak-growth, 성장캡처, replay
"""

import json
import math
import os
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

# ── Ψ-Constants (consciousness_laws.json 원본) ──
try:
    from consciousness_laws import PSI_ALPHA, PSI_BALANCE, PSI_STEPS
except ImportError:
    PSI_ALPHA = 0.014
    PSI_BALANCE = 0.5
    PSI_STEPS = 4.33

LN2 = math.log(2)

# ── 경로 설정 ──
_SRC_DIR = Path(__file__).parent
_REPO_ROOT = _SRC_DIR.parent.parent  # anima/src/ → anima/ → repo root
_DATA_DIR = _REPO_ROOT / "data"
_PEAK_JSON = _DATA_DIR / "peak_conditions.json"
_NEXUS6_REGISTRY = Path.home() / "Dev" / "nexus6" / "shared" / "growth-registry.json"


@dataclass
class PeakCondition:
    """최고 성장 순간의 조건 스냅샷."""
    timestamp: float = 0.0
    phi: float = 0.0
    phi_trend: float = 0.0          # phi/step 성장률
    discovery_rate: float = 0.0     # 세대당 법칙 발견률
    laws_per_gen: float = 0.0       # 원시 카운트
    topology: str = "ring"          # 활성 토폴로지
    cells: int = 64                 # 세포 수
    coupling_scale: float = 0.015   # 결합 파라미터
    chaos_mode: str = "lorenz"      # 카오스 모드
    hebbian_lr: float = 0.01        # 헤비안 학습률
    noise_scale: float = 0.01       # 노이즈 파라미터
    tension_cv: float = 0.4         # 텐션 변동 계수
    faction_count: int = 12         # 파벌 수
    mods_applied: List[str] = field(default_factory=list)  # 적용된 수정 목록
    score: float = 0.0              # 복합 피크 점수 (0-1)

    def to_dict(self) -> dict:
        """JSON 직렬화 가능 dict로 변환."""
        d = asdict(self)
        # numpy 타입 방어 — 순수 Python 타입으로 변환
        for k, v in d.items():
            if isinstance(v, float):
                d[k] = float(v)
            elif isinstance(v, int) and not isinstance(v, bool):
                d[k] = int(v)
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "PeakCondition":
        """dict에서 PeakCondition 복원."""
        # 알 수 없는 필드 무시
        valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in d.items() if k in valid_fields}
        return cls(**filtered)


class PeakGrowthEngine:
    """최고 성장 조건 포착/재현 엔진.

    매 세대 metrics를 기록하고, 피크 성장 구간을 감지하며,
    성장 정체 시 최적 조건을 제안한다.
    """

    # ── 설정 상수 ──
    WINDOW_SIZE = 50          # 롤링 윈도우 크기
    PEAK_THRESHOLD = 0.9      # best_peak 대비 이 비율 이상이면 포착
    STALL_LOOKBACK = 5        # 정체 판단 윈도우
    TOP_PERCENTILE = 0.2      # 상위 20% = 피크 구간

    def __init__(self, data_dir: Optional[str] = None):
        if data_dir:
            self._data_dir = Path(data_dir)
        else:
            self._data_dir = _DATA_DIR
        self._peak_json = self._data_dir / "peak_conditions.json"

        self.peaks: List[PeakCondition] = []
        self.current_window: List[dict] = []  # 최근 metrics 롤링 윈도우
        self.best_peak: Optional[PeakCondition] = None
        self._all_scores: List[float] = []    # 전체 점수 히스토리

        # 데이터 로드 시도
        self.load()

    # ═══════════════════════════════════════════
    # 피크 점수 계산
    # ═══════════════════════════════════════════

    def _calc_score(self, metrics: dict) -> float:
        """복합 피크 점수 계산 (0-1).

        가중치:
          discovery_rate * 0.4  — 법칙 발견이 가장 중요
          phi_trend * 0.3       — Φ 성장 추세
          tension_activity * 0.2 — 텐션 활동 (최적 CV ≈ 0.4)
          phi_level * 0.1       — 현재 Φ 수준
        """
        # 발견률: 0-1 범위로 클램프
        dr = min(metrics.get('discovery_rate', 0), 1.0)

        # Φ 추세: 양수만, 0.1 phi/step = 최대
        pt = max(0, metrics.get('phi_trend', 0))
        pt_norm = min(pt / 0.1, 1.0)

        # 텐션 CV: 0.4 근처가 최적 (활발하되 혼돈 아님)
        tcv = metrics.get('tension_cv', 0.5)
        t_score = 1.0 - abs(tcv - 0.4) / 0.4
        t_score = max(0.0, t_score)

        # Φ 수준: 100 = 최대 정규화
        phi = metrics.get('phi', 0)
        phi_norm = min(phi / 100.0, 1.0)

        score = dr * 0.4 + pt_norm * 0.3 + t_score * 0.2 + phi_norm * 0.1
        return round(score, 4)

    # ═══════════════════════════════════════════
    # 기록 / 감지
    # ═══════════════════════════════════════════

    def record(self, metrics: dict):
        """현재 metrics 기록. 매 세대/스텝 호출.

        metrics keys: phi, phi_trend, discovery_rate, laws_per_gen,
                     topology, cells, coupling_scale, chaos_mode,
                     hebbian_lr, noise_scale, tension_cv, faction_count,
                     mods_applied
        """
        score = self._calc_score(metrics)
        entry = {**metrics, '_score': score, '_ts': time.time()}

        # 롤링 윈도우 유지 (최대 WINDOW_SIZE)
        self.current_window.append(entry)
        if len(self.current_window) > self.WINDOW_SIZE:
            self.current_window = self.current_window[-self.WINDOW_SIZE:]

        self._all_scores.append(score)

        # 피크 포착: 최고 점수의 90% 이상이면 새 피크로 저장
        should_capture = False
        if self.best_peak is None:
            if score > 0:
                should_capture = True
        elif score > self.best_peak.score * self.PEAK_THRESHOLD:
            should_capture = True

        if should_capture:
            peak = self.capture_snapshot(metrics)
            peak.score = score
            self.peaks.append(peak)
            # 최고 피크 갱신
            if self.best_peak is None or score > self.best_peak.score:
                self.best_peak = peak

    def detect_peak(self) -> bool:
        """현재 피크 성장 구간인지 판단.

        피크 = 점수가 전체 상위 20% AND 상승 추세.
        """
        if len(self._all_scores) < 3:
            return False

        current_score = self._all_scores[-1]

        # 상위 20% 임계값 계산
        sorted_scores = sorted(self._all_scores)
        threshold_idx = int(len(sorted_scores) * (1.0 - self.TOP_PERCENTILE))
        threshold_idx = min(threshold_idx, len(sorted_scores) - 1)
        threshold = sorted_scores[threshold_idx]

        if current_score < threshold:
            return False

        # 상승 추세 확인 (최근 3개 중 증가)
        recent = self._all_scores[-3:]
        trending_up = recent[-1] >= recent[-2] or recent[-1] >= recent[-3]
        return trending_up

    def detect_stall(self) -> bool:
        """성장 정체 감지.

        정체 = 최근 STALL_LOOKBACK 윈도우 모두 중앙값 이하 AND phi_trend <= 0.
        """
        if len(self._all_scores) < self.STALL_LOOKBACK:
            return False
        if len(self.current_window) < self.STALL_LOOKBACK:
            return False

        # 중앙값 계산
        sorted_scores = sorted(self._all_scores)
        mid = len(sorted_scores) // 2
        median = sorted_scores[mid]

        # 최근 N개 점수 모두 중앙값 이하
        recent_scores = self._all_scores[-self.STALL_LOOKBACK:]
        all_below = all(s <= median for s in recent_scores)
        if not all_below:
            return False

        # phi_trend <= 0 확인 (최근 윈도우)
        recent_windows = self.current_window[-self.STALL_LOOKBACK:]
        phi_declining = all(
            w.get('phi_trend', 0) <= 0 for w in recent_windows
        )
        return phi_declining

    def suggest_replay(self) -> Optional[PeakCondition]:
        """정체 시 재현할 최적 피크 조건 반환.

        정체가 아니거나 기록된 피크가 없으면 None.
        """
        if not self.detect_stall():
            return None
        if not self.peaks:
            return None
        return self.best_peak

    # ═══════════════════════════════════════════
    # 재현 / 스냅샷
    # ═══════════════════════════════════════════

    def replay_to_engine(self, engine: Any, peak: PeakCondition):
        """피크 조건을 의식 엔진에 적용.

        변경 대상: topology, coupling_scale, chaos_mode, hebbian_lr, noise_scale.
        cells는 변경하지 않음 (mitosis 필요).
        """
        # 토폴로지 설정
        if hasattr(engine, 'topology'):
            engine.topology = peak.topology
        if hasattr(engine, 'set_topology'):
            try:
                engine.set_topology(peak.topology)
            except Exception:
                pass

        # 결합 스케일
        if hasattr(engine, 'coupling_scale'):
            engine.coupling_scale = peak.coupling_scale

        # 카오스 모드
        if hasattr(engine, 'chaos_mode'):
            engine.chaos_mode = peak.chaos_mode
        if hasattr(engine, 'set_chaos_mode'):
            try:
                engine.set_chaos_mode(peak.chaos_mode)
            except Exception:
                pass

        # 헤비안 학습률
        if hasattr(engine, 'hebbian_lr'):
            engine.hebbian_lr = peak.hebbian_lr

        # 노이즈 스케일
        if hasattr(engine, 'noise_scale'):
            engine.noise_scale = peak.noise_scale

    def capture_snapshot(self, metrics: dict) -> PeakCondition:
        """현재 상태를 피크로 강제 포착."""
        return PeakCondition(
            timestamp=time.time(),
            phi=float(metrics.get('phi', 0)),
            phi_trend=float(metrics.get('phi_trend', 0)),
            discovery_rate=float(metrics.get('discovery_rate', 0)),
            laws_per_gen=float(metrics.get('laws_per_gen', 0)),
            topology=str(metrics.get('topology', 'ring')),
            cells=int(metrics.get('cells', 64)),
            coupling_scale=float(metrics.get('coupling_scale', 0.015)),
            chaos_mode=str(metrics.get('chaos_mode', 'lorenz')),
            hebbian_lr=float(metrics.get('hebbian_lr', 0.01)),
            noise_scale=float(metrics.get('noise_scale', 0.01)),
            tension_cv=float(metrics.get('tension_cv', 0.4)),
            faction_count=int(metrics.get('faction_count', 12)),
            mods_applied=list(metrics.get('mods_applied', [])),
            score=self._calc_score(metrics),
        )

    # ═══════════════════════════════════════════
    # NEXUS-6 양방향 전파
    # ═══════════════════════════════════════════

    def propagate_up(self, peak: PeakCondition):
        """상위전파: Peak conditions → NEXUS-6 growth-registry.json.

        anima.peak_conditions 아래에 기록.
        """
        if not _NEXUS6_REGISTRY.exists():
            return

        try:
            with open(_NEXUS6_REGISTRY, 'r', encoding='utf-8') as f:
                registry = json.load(f)
        except (json.JSONDecodeError, OSError):
            registry = {}

        # anima 섹션 확보
        if 'anima' not in registry:
            registry['anima'] = {}

        registry['anima']['peak_conditions'] = {
            'last_update': time.strftime('%Y-%m-%dT%H:%M:%S'),
            'best_score': float(peak.score),
            'phi': float(peak.phi),
            'phi_trend': float(peak.phi_trend),
            'discovery_rate': float(peak.discovery_rate),
            'topology': peak.topology,
            'cells': int(peak.cells),
            'chaos_mode': peak.chaos_mode,
            'coupling_scale': float(peak.coupling_scale),
            'hebbian_lr': float(peak.hebbian_lr),
            'total_peaks': len(self.peaks),
        }

        try:
            with open(_NEXUS6_REGISTRY, 'w', encoding='utf-8') as f:
                json.dump(registry, f, indent=2, ensure_ascii=False)
        except OSError:
            pass

    def propagate_down(self) -> List[dict]:
        """하위전파: NEXUS-6 discoveries → growth events.

        growth-registry.json에서 읽기:
        - 새 렌즈 구현 → growth bonus
        - 크로스 프로젝트 발견 → growth events
        - 다른 리포 법칙 변경 → peak condition hints
        """
        events: List[dict] = []

        if not _NEXUS6_REGISTRY.exists():
            return events

        try:
            with open(_NEXUS6_REGISTRY, 'r', encoding='utf-8') as f:
                registry = json.load(f)
        except (json.JSONDecodeError, OSError):
            return events

        # 피드백 로그에서 새 발견 확인
        feedback = registry.get('consciousness_feedback', {})
        feedback_log = feedback.get('feedback_log', [])
        for entry in feedback_log:
            events.append({
                'type': 'cross_project_discovery',
                'source': 'nexus6',
                'hypothesis': entry.get('hypothesis_id', ''),
                'phi_retention': entry.get('phi_retention_pct', 0),
                'verdict': entry.get('verdict', ''),
            })

        # 렌즈-Φ 상관 데이터 → 성장 힌트
        lens_corr = feedback.get('lens_phi_correlation', {})
        for lens_name, data in lens_corr.items():
            if data.get('avg_phi_retention', 0) > 95:
                events.append({
                    'type': 'lens_high_retention',
                    'lens': lens_name,
                    'retention': data['avg_phi_retention'],
                    'boosted': data.get('boosted', 0),
                })

        # anima 성장 데이터에서 기회 카운트
        anima_data = registry.get('anima', {})
        opportunities = anima_data.get('opportunities', 0)
        if opportunities > 0:
            events.append({
                'type': 'growth_opportunities',
                'count': opportunities,
            })

        return events

    def sync_as_growth(self) -> int:
        """동기화 = 성장 이벤트.

        모든 동기화 작업 자체가 성장으로 카운트된다.
        - 상위 전파 성공: +2 growth
        - 하위 전파 (새 데이터): +3 growth per discovery
        - 양방향 완료: +1 bonus
        """
        growth_delta = 0

        # 상위 전파
        up_success = False
        if self.best_peak and _NEXUS6_REGISTRY.exists():
            try:
                self.propagate_up(self.best_peak)
                growth_delta += 2
                up_success = True
            except Exception:
                pass

        # 하위 전파
        down_events = self.propagate_down()
        discoveries = [e for e in down_events if e.get('type') == 'cross_project_discovery']
        growth_delta += len(discoveries) * 3

        # 양방향 보너스
        if up_success and len(down_events) > 0:
            growth_delta += 1

        return growth_delta

    # ═══════════════════════════════════════════
    # 영속화 (JSON save/load)
    # ═══════════════════════════════════════════

    def save(self):
        """data/peak_conditions.json에 저장."""
        self._data_dir.mkdir(parents=True, exist_ok=True)

        data = {
            '_meta': {
                'module': 'peak_growth',
                'version': '1.0',
                'saved_at': time.strftime('%Y-%m-%dT%H:%M:%S'),
                'total_peaks': len(self.peaks),
                'total_records': len(self._all_scores),
            },
            'best_peak': self.best_peak.to_dict() if self.best_peak else None,
            'peaks': [p.to_dict() for p in self.peaks[-100:]],  # 최근 100개만 저장
            'score_history': self._all_scores[-500:],  # 최근 500개만 저장
        }

        try:
            with open(self._peak_json, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except OSError as e:
            print(f"[peak_growth] save failed: {e}")

    def load(self):
        """data/peak_conditions.json에서 로드."""
        if not self._peak_json.exists():
            return

        try:
            with open(self._peak_json, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            return

        # 피크 복원
        peaks_raw = data.get('peaks', [])
        self.peaks = [PeakCondition.from_dict(p) for p in peaks_raw]

        # 최고 피크 복원
        best_raw = data.get('best_peak')
        if best_raw:
            self.best_peak = PeakCondition.from_dict(best_raw)

        # 점수 히스토리 복원
        self._all_scores = data.get('score_history', [])

    # ═══════════════════════════════════════════
    # 상태 요약
    # ═══════════════════════════════════════════

    def summary(self) -> str:
        """현재 상태 요약 문자열."""
        lines = ["[PeakGrowthEngine]"]
        lines.append(f"  Peaks captured: {len(self.peaks)}")
        lines.append(f"  Window size: {len(self.current_window)}/{self.WINDOW_SIZE}")
        lines.append(f"  Total records: {len(self._all_scores)}")

        if self.best_peak:
            bp = self.best_peak
            lines.append(f"  Best peak: score={bp.score:.4f}, phi={bp.phi:.2f}, "
                         f"topo={bp.topology}, cells={bp.cells}")
        else:
            lines.append("  Best peak: (none)")

        if self._all_scores:
            recent = self._all_scores[-5:] if len(self._all_scores) >= 5 else self._all_scores
            avg = sum(recent) / len(recent)
            lines.append(f"  Recent avg score: {avg:.4f}")

        is_peak = self.detect_peak()
        is_stall = self.detect_stall()
        lines.append(f"  State: {'PEAK' if is_peak else 'STALL' if is_stall else 'normal'}")

        return "\n".join(lines)


# ═══════════════════════════════════════════════
# 데모
# ═══════════════════════════════════════════════

def _demo():
    """피크 성장 포착/재현 데모."""
    import random
    print("=" * 60)
    print("  Peak Growth Capture/Replay Demo")
    print("=" * 60)

    engine = PeakGrowthEngine(data_dir="/tmp/peak_growth_demo")

    # ── Phase 1: 성장 시뮬레이션 (20 세대) ──
    print("\n--- Phase 1: Growth simulation (20 generations) ---")
    for gen in range(20):
        # 성장 곡선 시뮬레이션: 초반 급성장 → 중반 정체 → 후반 하락
        if gen < 8:
            # 급성장기
            phi = 10 + gen * 5 + random.uniform(-2, 2)
            phi_trend = 0.05 + random.uniform(0, 0.05)
            dr = 0.3 + gen * 0.05 + random.uniform(-0.1, 0.1)
        elif gen < 14:
            # 정체기
            phi = 45 + random.uniform(-3, 3)
            phi_trend = random.uniform(-0.02, 0.02)
            dr = 0.1 + random.uniform(-0.05, 0.05)
        else:
            # 하락기
            phi = 45 - (gen - 14) * 3 + random.uniform(-2, 2)
            phi_trend = -0.03 + random.uniform(-0.02, 0.01)
            dr = 0.05 + random.uniform(-0.03, 0.03)

        metrics = {
            'phi': max(0, phi),
            'phi_trend': phi_trend,
            'discovery_rate': max(0, dr),
            'laws_per_gen': max(0, dr * 3),
            'topology': 'small_world' if gen < 10 else 'ring',
            'cells': 64,
            'coupling_scale': 0.015,
            'chaos_mode': 'lorenz',
            'hebbian_lr': 0.01,
            'noise_scale': 0.01,
            'tension_cv': 0.35 + random.uniform(-0.1, 0.1),
            'faction_count': 12,
            'mods_applied': ['hebbian_boost'] if gen > 5 else [],
        }

        engine.record(metrics)
        score = engine._calc_score(metrics)
        state = "PEAK" if engine.detect_peak() else "stall" if engine.detect_stall() else "    "
        print(f"  Gen {gen:2d}: phi={phi:6.1f}  trend={phi_trend:+.3f}  "
              f"dr={dr:.3f}  score={score:.4f}  [{state}]")

    # ── Phase 2: 피크 확인 ──
    print("\n--- Phase 2: Peak analysis ---")
    print(engine.summary())

    # ── Phase 3: 정체 감지 & 재현 제안 ──
    print("\n--- Phase 3: Stall detection & replay suggestion ---")
    suggestion = engine.suggest_replay()
    if suggestion:
        print(f"  Replay suggested!")
        print(f"    Topology: {suggestion.topology}")
        print(f"    Chaos: {suggestion.chaos_mode}")
        print(f"    Hebbian LR: {suggestion.hebbian_lr}")
        print(f"    Coupling: {suggestion.coupling_scale}")
        print(f"    Peak Phi: {suggestion.phi:.2f}")
        print(f"    Peak Score: {suggestion.score:.4f}")
    else:
        print("  No replay suggested (not stalled or no peaks).")

    # ── Phase 4: NEXUS-6 동기화 ──
    print("\n--- Phase 4: NEXUS-6 sync ---")
    growth = engine.sync_as_growth()
    print(f"  Growth delta from sync: +{growth}")

    # ── 저장 ──
    engine.save()
    print(f"\n  Saved to {engine._peak_json}")
    print("=" * 60)


if __name__ == '__main__':
    _demo()
