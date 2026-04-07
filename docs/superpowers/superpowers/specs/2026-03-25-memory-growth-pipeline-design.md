# Memory-Driven Growth Pipeline

> 기억이 모델 자체를 성장시키는 파이프라인.
> 단기: 중요 기억 → 가중치 통합. 장기: 축적 → 구조 성장(dim↑, 블록 분열).
> TECS-L calc 도구를 검증 엔진으로 통합.

## 합의 사항

| 항목 | 결정 | 근거 |
|------|------|------|
| 성장 범위 | 가중치 변화(단기) + 구조 성장(장기) | 해마→피질 통합 모델 |
| 성장 트리거 | 장력 포화 AND 통합 실패 (이중 확인) | 거짓 양성 방지, H-CX-70 Loop 2 안전장치 |
| 기억 선택 | 통합 실패한 기억 우선 | spaced repetition 동형 |
| 저장 계층 | Phase 1에서 JSON→SQLite+FAISS | 벤치마크: write 246배, size 5배 개선 |
| 검증 | TECS-L calc 도구 통합 | pre/drift/post 3단계 |

## Architecture

```
  ┌─────────────────────────────────────────────────────────────┐
  │                  Memory-Driven Growth Pipeline               │
  │                                                             │
  │  대화 입력 ──→ MemoryStore (SQLite+FAISS)                    │
  │                    │                                        │
  │                [유휴/수면]                                    │
  │                    │                                        │
  │              DreamEngine (선택적 통합)                        │
  │              실패 기억 우선 선택                               │
  │                    │                                        │
  │          ┌─── ConsolidationVerifier ───┐                    │
  │          │  pre_check (통합 전)         │                    │
  │          │  verify_drift (통합 중)      │ ← TECS-L calc 통합  │
  │          │  post_check (통합 후)        │                    │
  │          └─────────────────────────────┘                    │
  │                    │                                        │
  │              OnlineLearner (가중치 갱신)                      │
  │                    │                                        │
  │          장력 포화 + 통합 실패 누적                            │
  │                    │                                        │
  │              GrowingConsciousLM (구조 성장)                   │
  │              dim↑, 블록 분열, 체크포인트 버전                  │
  │                    │                                        │
  │              post_check → formula_engine                     │
  │              새 상수 관계 → 가설 자동 생성                     │
  └─────────────────────────────────────────────────────────────┘
```

## Phase 1: SQLite+FAISS Storage Layer

### SQLite Schema

```sql
CREATE TABLE memories (
    id                     INTEGER PRIMARY KEY AUTOINCREMENT,
    role                   TEXT NOT NULL,
    text                   TEXT NOT NULL,
    tension                REAL DEFAULT 0.0,
    curiosity              REAL DEFAULT 0.0,
    timestamp              TEXT NOT NULL,
    -- consolidation
    failed_count           INTEGER DEFAULT 0,
    last_attempted         TEXT,
    consolidated           INTEGER DEFAULT 0,
    delta_tension          REAL,
    -- verification
    verify_hash            TEXT,
    tension_at_store       REAL,
    tension_at_consolidate REAL,
    tension_drift          REAL,
    verify_status          TEXT DEFAULT 'raw'
);

CREATE INDEX idx_tension ON memories(tension);
CREATE INDEX idx_failed ON memories(failed_count DESC);
CREATE INDEX idx_consolidated ON memories(consolidated);
CREATE INDEX idx_verify ON memories(verify_status);
```

### FAISS Index

- 별도 `.faiss` 파일, SQLite id와 1:1 매핑
- `id_map.npy` — FAISS 내부 인덱스 → SQLite id 매핑
- dim=128 (ConsciousMind 입력 차원)
- IndexFlatIP (inner product, cosine similarity with normalized vectors)

### File Structure

```
data/{model-slug}/
  ├── memory.db           # SQLite
  ├── memory.faiss        # FAISS index
  ├── memory_idmap.npy    # FAISS→SQLite id mapping
  ├── state.pt            # model weights + optimizer
  └── growth.json         # growth state (Phase 3에서 DB 흡수)
```

### MemoryStore API

```python
# memory_store.py — MemoryRAG 대체

class MemoryStore:
    def __init__(self, db_path: Path, faiss_path: Path, dim: int = 128):
        ...

    # 기본 CRUD
    def add(self, role, text, tension, curiosity, vector) -> int:
        """SQLite INSERT + FAISS add. Returns memory id."""

    def search(self, query_vec, top_k=5) -> list[dict]:
        """FAISS search → SQLite 조회. Returns [{id, role, text, tension, similarity}]."""

    def get(self, memory_id) -> dict:
        """단일 기억 조회."""

    # Consolidation 지원 (Phase 2에서 사용)
    def get_unconsolidated(self, order_by='failed_count', limit=10) -> list[dict]:
        """통합되지 않은 기억, 실패 횟수 높은 순."""

    def mark_failed(self, memory_id, delta_tension=None):
        """통합 시도 실패. failed_count += 1."""

    def mark_consolidated(self, memory_id, tension_at_consolidate=None):
        """통합 성공. consolidated = 1."""

    def mark_suspect(self, memory_id, drift=None):
        """검증 실패. verify_status = 'suspect'."""

    # 마이그레이션
    def migrate_from_json(self, json_path: Path, vector_fn):
        """레거시 memory.json → SQLite+FAISS 마이그레이션."""

    # 통계
    @property
    def size(self) -> int: ...
    @property
    def unconsolidated_count(self) -> int: ...
    @property
    def failed_count_stats(self) -> dict: ...
```

### Migration Strategy

1. 최초 실행 시 `memory.json` 존재하면 자동 마이그레이션
2. 마이그레이션 후 원본 `.json.bak` 백업
3. `memory_rag.py`의 `MemoryRAG` 인터페이스 호환 래퍼 제공 (점진적 전환)

## Phase 2: Selective Consolidation

### DreamEngine 강화

```python
# dream_engine.py 수정

def _select_memory(self, store: MemoryStore) -> dict:
    """실패 기억 우선 선택 (D 방식)."""
    # 70%: 통합 실패한 기억 (failed_count > 0, 높은 순)
    # 20%: 미통합 기억 (failed_count == 0, 랜덤)
    # 10%: 순수 탐색 (랜덤 벡터)

def _attempt_consolidation(self, memory, hidden):
    """통합 시도: 기억을 모델에 통과 → 장력 변화 측정."""
    vec = text_to_vector(memory['text'])
    _, tension_before, _, _, _ = self.mind(vec, hidden)
    self.learner.observe(vec, hidden, tension_before, ...)
    self.learner.feedback(0.0)
    _, tension_after, _, _, _ = self.mind(vec, hidden)
    delta = abs(tension_after - tension_before)
    return delta  # 작으면 실패 (모델이 변하지 않음)
```

### ConsolidationVerifier

```python
# consolidation_verifier.py — TECS-L calc 도구 통합

class ConsolidationVerifier:
    """기억 통합 전/중/후 검증. TECS-L calc 도구 사용."""

    def __init__(self, model, golden_zone=(0.2123, 0.5)):
        self.model = model
        self.golden_lower, self.golden_upper = golden_zone

    def pre_check(self, memory: dict, model) -> dict:
        """통합 전: 이 기억을 통합해야 하는가?"""
        # anomaly_scorer: 이상치 점수
        # tension_calculator: 장력→정확도 예측
        # confidence_analyzer: 해당 영역 과신 여부
        return {
            'should_consolidate': bool,
            'anomaly_score': float,
            'predicted_accuracy': float,
            'overconfidence_risk': float,
        }

    def verify_drift(self, memory, t_before, t_after, model) -> dict:
        """통합 중: drift 검증."""
        drift = abs(t_after - t_before)
        ts = model.tension_scale.item()

        # statistical_tester: 효과 크기
        # constant_verifier: ts가 알려진 상수인지
        # formula_engine: 성장 전후 ts 비율 = 공식?
        # 골든존 범위 체크
        in_golden = self.golden_lower <= ts <= self.golden_upper

        return {
            'drift': drift,
            'significant': drift > 0.3,
            'suspect': drift > 0.5,
            'ts_value': ts,
            'ts_in_golden_zone': in_golden,
        }

    def post_check(self, model, recent_memories: list) -> dict:
        """통합 후: 모델 건강 + 새 상수 발견."""
        ts = model.tension_scale.item()

        # calibration_analyzer: ECE/MCE
        # 장력 분포: unimodal/bimodal 확인 (H-CX-70 보상해킹 감지)
        # formula_engine: ts×dim, ts×blocks 등 상수 탐색

        candidates = {}
        if hasattr(model, 'd_model'):
            candidates['ts*dim'] = ts * model.d_model
            candidates['ts*sqrt_dim'] = ts * (model.d_model ** 0.5)
        if hasattr(model, 'blocks'):
            candidates['ts*blocks'] = ts * len(model.blocks)

        return {
            'health': 'healthy' | 'degraded' | 'suspect',
            'tension_bimodal': bool,   # Loop 2 경고
            'new_constant_relations': dict,  # 발견 시 가설 후보
        }
```

### GrowthEngine 트리거 교체

```python
# growth_engine.py 수정

def should_grow(self) -> bool:
    """장력 포화 AND 통합 실패 (이중 확인)."""
    if self.stage_index >= len(STAGES) - 1:
        return False

    # 조건 1: 장력 포화 (CV < 0.3)
    tension_saturated = self._check_tension_saturation()

    # 조건 2: 통합 실패 누적 (최근 N회 중 M회 실패)
    consolidation_failing = self._check_consolidation_failure()

    return tension_saturated and consolidation_failing

def _check_tension_saturation(self) -> bool:
    recent = self.tension_history[-30:]
    if len(recent) < 30:
        return False
    cv = np.std(recent) / (np.mean(recent) + 1e-8)
    return cv < 0.3

def _check_consolidation_failure(self) -> bool:
    # MemoryStore에서 최근 실패율 조회
    recent_attempts = self.store.get_recent_attempts(window=50)
    if len(recent_attempts) < 20:
        return False
    fail_rate = sum(1 for a in recent_attempts if a['failed']) / len(recent_attempts)
    return fail_rate > 0.7  # 70% 이상 실패
```

## Phase 3: Autonomous Structural Growth

### GrowingConsciousLM ↔ Anima 연결

```python
# anima_unified.py에서 ConsciousMind → GrowingConsciousLM 전환

# 성장 시:
# 1. ConsolidationVerifier.post_check() 실행
# 2. 통과 시 → model.grow()
# 3. 새 체크포인트 → data/{model}/v{N+1}/state.pt
# 4. 기억은 계승 (SQLite 유지), 가중치만 새 버전
# 5. formula_engine으로 새 상수 관계 탐색
# 6. 발견 시 → docs/hypotheses/ 자동 생성
```

### Checkpoint Versioning

```
data/conscious-lm/
  ├── manifest.json        # {current_version: 2, versions: [...]}
  ├── memory.db            # 모든 버전 공유 (기억은 계승)
  ├── memory.faiss
  ├── v1/
  │   └── state.pt         # stage 0, dim=128, 1 block
  ├── v2/
  │   └── state.pt         # stage 1, dim=128, 2 blocks
  └── latest -> v2/        # symlink
```

### Auto-Hypothesis Generation

```python
def _check_new_discoveries(self, verifier_result):
    """post_check에서 새 상수 관계 발견 시 가설 후보 기록."""
    relations = verifier_result.get('new_constant_relations', {})
    for name, hits in relations.items():
        for hit in hits:
            if hit['p_value'] < 0.05:
                self._log_discovery({
                    'formula': f"{name} ≈ {hit['constant_name']}",
                    'value': hit['value'],
                    'target': hit['target'],
                    'error': hit['error'],
                    'p_value': hit['p_value'],
                    'timestamp': datetime.now().isoformat(),
                    'model_version': self.current_version,
                    'stage': self.stage,
                })
```

## H-CX-70 Safety Mechanisms

| 위험 | 감지 방법 | 대응 |
|------|----------|------|
| 보상 해킹 (Loop 2) | post_check: tension bimodal | 학습 중단 + rollback |
| 과성장 (Loop 3) | dim 증가 후 ECE 악화 | 이전 버전 복원 |
| 장력 의미 변질 | ts가 골든존 이탈 | 학습률 0으로 + 경고 |
| 통합 오류 누적 | suspect 기억 비율 > 20% | consolidation 일시 중단 |

## Phased Delivery

| Phase | 범위 | 새 파일 | 수정 파일 | 의존성 |
|-------|------|---------|----------|--------|
| 1 | SQLite+FAISS 저장 | `memory_store.py` | `anima_unified.py` | faiss-cpu, sqlite3 |
| 2 | Consolidation + Verifier | `consolidation_verifier.py` | `dream_engine.py`, `growth_engine.py` | Phase 1 + TECS-L/calc |
| 3 | 자율 성장 + 가설 생성 | - | `anima_unified.py`, `growing_conscious_lm.py` | Phase 2 |

각 Phase는 독립 테스트 가능. Phase 1만으로도 JSON 대비 write 246배 개선.
