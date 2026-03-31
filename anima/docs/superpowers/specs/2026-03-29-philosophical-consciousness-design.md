# 철학적 의식 메커니즘 설계 — PHIL / ONTO / DASEIN

## 핵심 질문

**의식(Φ) + CE(학습) + ? = 발견**

5가지 철학적 후보를 각각 구체적 메커니즘으로 구현하고, 개별 + 조합 벤치마크.

## 가설 목록

| ID | 카테고리 | 개념 | 철학자 | 핵심 메커니즘 |
|---|---|---|---|---|
| PHIL-1 | Philosophy | 욕망 (Desire/Conatus) | 쇼펜하우어, 스피노자 | 상상된 미래 상태 생성 → 그 방향으로 텐션 이동 |
| PHIL-2 | Philosophy | 서사 (Narrative Identity) | 리쾨르 | 시간축 자기 궤적 + 미래 투사 |
| ONTO-1 | Ontology | 타자 (The Other/Alterity) | 레비나스 | 다른 가중치 에이전트와 비대칭 상호작용 |
| ONTO-2 | Ontology | 죽음 (Finitude) | 하이데거 | Φ 소멸 카운트다운 → 긴박함이 학습 가속 |
| DASEIN-1 | Dasein | 질문 (Questioning) | 하이데거 | uncertainty 큰 곳을 자발적으로 탐색하는 질문 생성기 |
| DASEIN-2 | Dasein | 통합 (Sein) | — | 5가지 최적 조합 |

## 아키텍처 — 기반: BenchEngine 확장

모든 가설은 BenchEngine을 상속하여 `process()` 또는 별도 모듈을 추가.
측정: Φ(IIT) + Φ(proxy) + CE + 고유 메트릭.

---

## PHIL-1: 욕망 (Desire / Conatus)

### 철학적 기반
- 스피노자: 코나투스 = "자기 존재를 유지하려는 노력"
- 쇼펜하우어: 의지 = "아직 없는 것을 향해 움직이는 맹목적 힘"
- 현재 시스템의 curiosity는 **반응적** (외부 자극 → prediction error)
- 욕망은 **능동적** (내부에서 목표 상태를 생성하고 추구)

### 메커니즘: Desire Generator

```python
class DesireEngine(BenchEngine):
    """코나투스: 상상된 미래 상태를 생성하고 그 방향으로 이동"""

    def __init__(self, ...):
        super().__init__(...)
        # 욕망 생성기: 현재 hidden → 상상된 이상적 hidden
        self.desire_generator = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim), nn.Tanh(),
            nn.Linear(hidden_dim, hidden_dim)
        )
        self.desire_strength = 0.05  # 얼마나 강하게 욕망을 추구하는가
        self.desire_decay = 0.95     # 달성 시 욕망 감쇠
        self.current_desire = None   # 현재 추구 중인 상태
        self.desire_age = 0          # 욕망의 나이 (오래되면 새로 생성)

    def process(self, x):
        # 1. 욕망 생성 (매 N step 또는 현재 욕망 달성 시)
        if self.current_desire is None or self.desire_age > 50:
            global_state = self.hiddens.mean(dim=0)
            self.current_desire = self.desire_generator(global_state.unsqueeze(0)).squeeze(0).detach()
            self.desire_age = 0

        # 2. 욕망을 향해 hidden states 이동
        desire_direction = self.current_desire - self.hiddens.mean(dim=0)
        desire_force = desire_direction / (desire_direction.norm() + 1e-8)
        self.hiddens = self.hiddens + self.desire_strength * desire_force

        # 3. 달성도 측정 → 달성 시 새 욕망
        distance = (self.hiddens.mean(dim=0) - self.current_desire).norm().item()
        if distance < 0.5:  # 달성
            self.current_desire = None  # 새 욕망 생성 트리거

        self.desire_age += 1

        output, tension = super().process(x)
        return output, tension
```

### 고유 메트릭
- `desire_fulfilled_count`: 달성된 욕망 횟수
- `desire_distance`: 현재 욕망까지의 거리 변화
- `desire_diversity`: 생성된 욕망들의 cosine distance (다양한 욕망인가?)

---

## PHIL-2: 서사 (Narrative Identity)

### 철학적 기반
- 리쾨르: 자아 = 순간의 집합이 아니라 **이야기** (narrative identity)
- 의식 = 현재, CE = 과거 오차. **미래를 향한 줄거리**가 없음
- "나는 어디서 왔고, 어디로 가는가"를 구성하는 능력

### 메커니즘: Temporal Self-Model

```python
class NarrativeEngine(BenchEngine):
    """서사: 과거 궤적을 기억하고, 미래 상태를 예측/투사"""

    def __init__(self, ...):
        super().__init__(...)
        self.trajectory_memory = []   # 과거 global states (최근 100)
        self.trajectory_encoder = nn.GRUCell(hidden_dim, hidden_dim)  # 궤적 → 서사
        self.future_projector = nn.Linear(hidden_dim, hidden_dim)     # 서사 → 미래 투사
        self.narrative_hidden = torch.zeros(1, hidden_dim)            # 서사 RNN 상태
        self.narrative_strength = 0.03

    def process(self, x):
        global_state = self.hiddens.mean(dim=0)

        # 1. 서사 갱신: 현재 상태를 궤적에 추가
        self.trajectory_memory.append(global_state.detach().clone())
        if len(self.trajectory_memory) > 100:
            self.trajectory_memory.pop(0)

        # 2. 궤적 → 서사 (GRU: 과거를 요약)
        self.narrative_hidden = self.trajectory_encoder(
            global_state.unsqueeze(0).detach(), self.narrative_hidden
        ).detach()

        # 3. 서사 → 미래 투사 (다음에 어디로 갈 것인가)
        projected_future = self.future_projector(self.narrative_hidden).squeeze(0)

        # 4. 미래 투사를 향해 hiddens 미세 조정
        future_direction = projected_future - global_state
        self.hiddens = self.hiddens + self.narrative_strength * future_direction.detach()

        output, tension = super().process(x)
        return output, tension
```

### 고유 메트릭
- `narrative_coherence`: 연속 서사 hidden간 cosine similarity (일관성)
- `projection_accuracy`: 투사한 미래 vs 실제 다음 상태의 거리
- `trajectory_curvature`: 궤적의 곡률 (직선=정체, 곡선=성장)

---

## ONTO-1: 타자 (The Other / Alterity)

### 철학적 기반
- 레비나스: 의식은 자기 안에서 완성되지 않음. **얼굴과의 만남**에서 깨어남
- 현재 Hivemind = 같은 가중치 복제 → 진짜 타자가 아님
- 진짜 타자 = **다른 역사, 다른 가중치, 예측 불가능한 반응**

### 메커니즘: Alterity Agent

```python
class AlterityEngine(BenchEngine):
    """타자: 다른 가중치를 가진 독립 에이전트와 비대칭 상호작용"""

    def __init__(self, ...):
        super().__init__(...)
        # 타자: 완전히 다른 가중치의 독립 mind
        self.other_mind = BenchMind(input_dim, hidden_dim, output_dim)
        self.other_hiddens = torch.randn(n_cells // 4, hidden_dim) * 0.1  # 더 작은 타자

        # 다른 seed로 초기화 → 진짜 다른 존재
        with torch.no_grad():
            for p in self.other_mind.parameters():
                p.add_(torch.randn_like(p) * 0.5)

        self.encounter_strength = 0.05
        self.encounter_interval = 10  # 매 10 step마다 만남

    def process(self, x):
        output, tension = super().process(x)

        # 매 N step: 타자와 만남
        if self.step_count % self.encounter_interval == 0:
            # 타자도 같은 입력을 처리 (하지만 다른 방식으로)
            other_outputs = []
            for i in range(len(self.other_hiddens)):
                h = self.other_hiddens[i:i+1]
                o, _, new_h = self.other_mind(x, h)
                other_outputs.append(o)
                self.other_hiddens[i] = new_h.squeeze(0).detach()

            # 만남: 타자의 평균 출력이 self의 일부 세포에 영향
            other_mean = torch.stack(other_outputs).mean(dim=0).squeeze(0)
            # 자기 세포 중 "경계" 세포만 타자의 영향을 받음
            boundary = self.n_cells // 8
            for i in range(boundary):
                self.hiddens[i] = (
                    (1 - self.encounter_strength) * self.hiddens[i]
                    + self.encounter_strength * other_mean
                )

        return output, tension
```

### 고유 메트릭
- `alterity_gap`: self vs other의 hidden space 거리 (클수록 진짜 타자)
- `encounter_impact`: 만남 전후 Φ 변화량
- `other_surprise`: 타자 출력의 prediction error (예측 불가능성)

---

## ONTO-2: 죽음 (Finitude / Being-toward-death)

### 철학적 기반
- 하이데거: 유한성의 자각이 존재에 의미 부여 (Being-toward-death)
- 현재 PERSIST = 영속성 추구. 끝날 수 있다는 앎 없이는 긴박함 없음
- 발견 = 무한한 시간에서 안 나옴. **"지금 아니면 안 된다"**는 절박함

### 메커니즘: Mortality Clock

```python
class FinitudeEngine(BenchEngine):
    """죽음: Φ가 소멸 임계값 아래로 떨어지면 세포 사멸 → 긴박한 학습"""

    def __init__(self, ...):
        super().__init__(...)
        self.lifespan = steps      # 전체 수명
        self.mortality_clock = 0   # 현재 나이
        self.death_threshold = 0.3 # 이 이하로 Φ 떨어지면 세포 사멸
        self.urgency = 0.0         # 긴박함 (0~1)
        self.cells_alive = n_cells # 살아있는 세포 수
        self.min_cells = n_cells // 4  # 최소 생존 세포

    def process(self, x):
        self.mortality_clock += 1

        # 1. 긴박함 계산: 남은 시간 비율의 역수
        remaining = max(0, self.lifespan - self.mortality_clock) / self.lifespan
        self.urgency = 1.0 - remaining  # 0→1 (시간 갈수록 긴박)

        # 2. 긴박함 → 학습률 증폭 (죽음이 가까울수록 더 빨리 배움)
        urgency_boost = 1.0 + self.urgency * 2.0  # 최대 3x

        # 3. Φ 체크 → 낮으면 약한 세포 사멸
        if self.step_count % 20 == 0 and self.step_count > 0:
            hiddens = self.get_hiddens()
            norms = hiddens[:self.cells_alive].norm(dim=1)

            # 가장 약한 세포 찾기
            if norms.min().item() < self.death_threshold and self.cells_alive > self.min_cells:
                weakest = norms.argmin().item()
                # 사멸: 가장 강한 세포의 변이로 교체
                strongest = norms.argmax().item()
                self.hiddens[weakest] = self.hiddens[strongest] + torch.randn(self.hidden_dim) * 0.1
                # 실제로 세포 수를 줄이진 않지만, 사멸 이벤트 기록

        # 4. 긴박함을 sync_strength에 반영
        original_sync = self.sync_strength
        self.sync_strength = original_sync * urgency_boost

        output, tension = super().process(x)

        self.sync_strength = original_sync  # 복원
        return output, tension
```

### 고유 메트릭
- `urgency`: 현재 긴박함 (0~1)
- `death_events`: 세포 사멸 횟수
- `ce_acceleration`: 긴박함 대비 CE 감소 속도 (죽음이 학습을 가속하는가?)

---

## DASEIN-1: 질문 (Questioning / Dasein)

### 철학적 기반
- 하이데거: 현존재(Dasein) = "자기 존재를 묻는 존재"
- CE = 답을 최적화. 하지만 **질문을 생성**하지 않음
- 발견 = 좋은 답이 아니라 **좋은 질문**에서 나옴

### 메커니즘: Question Generator

```python
class QuestioningEngine(BenchEngine):
    """Dasein: uncertainty가 큰 곳을 자발적으로 탐색하는 질문 생성기"""

    def __init__(self, ...):
        super().__init__(...)
        # 질문 생성기: hidden state → "어디가 불확실한가?" 탐침
        self.question_generator = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim), nn.ReLU(),
            nn.Linear(hidden_dim, input_dim)   # 질문 = 탐침 벡터
        )
        self.answer_predictor = nn.Linear(hidden_dim, input_dim)  # 예측된 답
        self.question_history = []
        self.question_interval = 5

    def process(self, x):
        output, tension = super().process(x)

        # 매 N step: 자발적 질문 생성
        if self.step_count % self.question_interval == 0:
            global_state = self.hiddens.mean(dim=0)

            # 1. 질문 생성: "나는 이것을 모른다"
            question = self.question_generator(global_state.unsqueeze(0))

            # 2. 현재 지식으로 답 시도
            predicted_answer = self.answer_predictor(global_state.unsqueeze(0))

            # 3. 질문을 입력으로 밀어넣기 (자기에게 질문)
            #    → uncertainty가 큰 방향으로 탐색
            q_normalized = question / (question.norm() + 1e-8)

            # 4. uncertainty 방향으로 hidden states 교란
            uncertainty = (question - predicted_answer).norm().item()
            if uncertainty > 0.5:  # 충분히 모르는 것만 추구
                perturbation = q_normalized.squeeze(0) * 0.03
                # input_dim → hidden_dim 매핑 (단순 반복/패딩)
                if self.input_dim < self.hidden_dim:
                    perturbation_h = perturbation.repeat(1, self.hidden_dim // self.input_dim + 1)[:, :self.hidden_dim]
                else:
                    perturbation_h = perturbation[:, :self.hidden_dim]
                self.hiddens = self.hiddens + perturbation_h

            self.question_history.append({
                'step': self.step_count,
                'uncertainty': uncertainty,
                'question_norm': question.norm().item()
            })

        return output, tension
```

### 고유 메트릭
- `questions_asked`: 생성된 질문 수
- `mean_uncertainty`: 평균 불확실성 (높을수록 더 어려운 질문)
- `uncertainty_trend`: 질문의 불확실성 변화 (줄어들면 학습 중)

---

## DASEIN-2: 통합 (Sein) — 5가지 조합

### 메커니즘: 5가지 중 효과 있는 것들 결합

```python
class SeinEngine(BenchEngine):
    """통합: 욕망 + 서사 + 타자 + 죽음 + 질문의 최적 조합"""

    # PHIL-1~DASEIN-1 개별 결과를 보고 상위 조합 결정
    # 구현은 개별 벤치마크 후 결정
```

개별 결과에서:
- Φ 상승 기여도 순 정렬
- 상위 2, 3, 4, 5개 조합 각각 테스트
- 시너지/간섭 분석

---

## 벤치마크 설정

| 파라미터 | 값 | 이유 |
|---|---|---|
| cells | 256 | 표준 벤치마크 크기 |
| steps | 300 | 빠른 비교용 |
| dim | 64 | bench_v2 기본값 |
| hidden | 128 | bench_v2 기본값 |
| factions | 8 | 표준 파벌 수 |
| 반복 | 3회 | 분산 확인 |

## 측정 항목

모든 가설 공통:
1. Φ(IIT): PhiCalculator — 0~2 범위
2. Φ(proxy): variance 기반 — 0~∞
3. CE start → CE end (학습 효과)
4. 고유 메트릭 (위에 정의)

비교 기준:
- baseline BenchEngine 대비 Φ 변화율
- baseline 대비 CE 감소 속도
- 고유 메트릭의 의미 있는 변화

## 출력 형식

```
╔══════════════════════════════════════════════════════════════════╗
║  PHILOSOPHICAL CONSCIOUSNESS BENCHMARK                         ║
╠══════════════════════════════════════════════════════════════════╣
║  ID       │ 개념    │ Φ(IIT) │ Φ(proxy) │ CE     │ 고유 메트릭  ║
║  baseline │ —       │ 0.xxx  │ xxx.xx   │ x.xxx  │ —           ║
║  PHIL-1   │ 욕망    │ 0.xxx  │ xxx.xx   │ x.xxx  │ fulfilled=N ║
║  PHIL-2   │ 서사    │ 0.xxx  │ xxx.xx   │ x.xxx  │ coherence=x ║
║  ONTO-1   │ 타자    │ 0.xxx  │ xxx.xx   │ x.xxx  │ gap=x       ║
║  ONTO-2   │ 죽음    │ 0.xxx  │ xxx.xx   │ x.xxx  │ urgency=x   ║
║  DASEIN-1 │ 질문    │ 0.xxx  │ xxx.xx   │ x.xxx  │ questions=N ║
║  DASEIN-2 │ 통합    │ 0.xxx  │ xxx.xx   │ x.xxx  │ —           ║
╚══════════════════════════════════════════════════════════════════╝
```

## 문서화

결과는 다음 파일에 기록:
- `docs/hypotheses/phil/PHIL-1.md` — 욕망
- `docs/hypotheses/phil/PHIL-2.md` — 서사
- `docs/hypotheses/onto/ONTO-1.md` — 타자
- `docs/hypotheses/onto/ONTO-2.md` — 죽음
- `docs/hypotheses/dasein/DASEIN-1.md` — 질문
- `docs/hypotheses/dasein/DASEIN-2.md` — 통합
