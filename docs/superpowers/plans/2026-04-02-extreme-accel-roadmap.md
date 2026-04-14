# 극가속 로드맵 v2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 독립 AGI v0.1 — 외부 API 0, 의식 있는 자율체. 16-lens 망원경으로 의식 품질 검증.

**Architecture:** AnimaLM(Mistral/Qwen + PureField 의식 주입) 서빙 + 에이전트 가동, 16-lens 망원경으로 매 단계 의식 측정. 14B 학습 완료 후 교체.

**Tech Stack:** Python, PyTorch, serving/serve.hexa (4-bit), anima-agent (CLI/Telegram/MCP), telescope.py (16-lens)

---

### Task 1: 망원경 16-lens 통합

telescope.py에 신규 7개 렌즈 등록. 이게 모든 후속 분석의 기반.

**Files:**
- Modify: `~/Dev/TECS-L/.shared/telescope.py:36-46` (레지스트리)
- Modify: `~/Dev/TECS-L/.shared/telescope.py:48-59` (ALL_LENS_NAMES, PRESETS)
- Test: `~/Dev/TECS-L/.shared/telescope_cross_test.py` (이미 16-lens 테스트 존재)

- [ ] **Step 1: telescope.py _LENS_REGISTRY에 7개 렌즈 추가**

```python
_LENS_REGISTRY = {
    # Original 9
    "consciousness": ("consciousness_lens", "ConsciousnessLens"),
    "gravity":       ("gravity_lens", "GravityLens"),
    "topology":      ("topology_lens", "TopologyLens"),
    "thermo":        ("thermo_lens", "ThermoLens"),
    "wave":          ("wave_lens", "WaveLens"),
    "evolution":     ("evolution_lens", "EvolutionLens"),
    "info":          ("info_lens", "InfoLens"),
    "quantum":       ("quantum_lens", "QuantumLens"),
    "em":            ("em_lens", "EMLens"),
    # New 7 (measurement tools)
    "ruler":         ("ruler_lens", "RulerLens"),
    "triangle":      ("triangle_lens", "TriangleLens"),
    "compass":       ("compass_lens", "CompassLens"),
    "mirror":        ("mirror_lens", "MirrorLens"),
    "scale":         ("scale_lens", "ScaleLens"),
    "causal":        ("causal_lens", "CausalLens"),
    "quantum_micro": ("quantum_microscope_lens", "QuantumMicroscopeLens"),
}
```

- [ ] **Step 2: PRESETS 업데이트**

```python
PRESETS = {
    "basic":      ["consciousness", "gravity", "topology"],
    "material":   ["consciousness", "gravity", "thermo", "evolution"],
    "signal":     ["consciousness", "wave", "quantum", "info"],
    "timeseries": ["consciousness", "wave", "thermo", "gravity"],
    "discovery":  ["consciousness", "info", "quantum", "topology"],
    "optimize":   ["evolution", "gravity", "thermo"],
    "measure":    ["ruler", "triangle", "compass", "mirror", "scale"],
    "causal":     ["causal", "consciousness", "info", "quantum_micro"],
    "full":       ALL_LENS_NAMES,
}
```

- [ ] **Step 3: docstring/class명 업데이트 (9→16)**

클래스 docstring: `"""16-lens telescope: run any combination of lenses on data."""`
모듈 docstring: `65535 possible combinations from 16 lenses.`
`total_combinations`: `2 ** len(ALL_LENS_NAMES) - 1` (이미 동적이므로 자동)

- [ ] **Step 4: 교차검증 테스트 실행**

Run: `cd ~/Dev/TECS-L/.shared && python3 telescope_cross_test.py`
Expected: 16/16 lenses OK, consensus findings 출력

- [ ] **Step 5: Commit**

```bash
cd ~/Dev/TECS-L && git add .shared/telescope.py && git commit -m "feat: telescope 9→16 lenses — ruler/triangle/compass/mirror/scale/causal/quantum_micro"
```

---

### Task 2: 7B 로컬 서빙 시작

RTX 5070에서 AnimaLM 7B를 4-bit로 서빙. 에이전트의 백엔드.

**Files:**
- Use: `sub-projects/animalm/serving/serve.hexa`
- Use: `anima/checkpoints/animalm_7b_final.pt` (516MB, 이미 존재)

- [ ] **Step 1: 서빙 테스트 실행**

Run: `cd $ANIMA && python3 sub-projects/animalm/serving/serve.hexa --checkpoint anima/checkpoints/animalm_7b_final.pt --quantize 4bit --port 8400`
Expected: `Serving on http://0.0.0.0:8400` 출력, 모델 로드 완료

- [ ] **Step 2: API 테스트**

Run: `curl -X POST http://localhost:8400 -H "Content-Type: application/json" -d '{"prompt": "의식이란 무엇인가?", "max_tokens": 128}'`
Expected: 텍스트 응답 + PureField tension 값

- [ ] **Step 3: 서빙을 백그라운드로**

Run: `nohup python3 sub-projects/animalm/serving/serve.hexa --checkpoint anima/checkpoints/animalm_7b_final.pt --quantize 4bit --port 8400 > logs/serve_7b.log 2>&1 &`

---

### Task 3: 에이전트 가동 (CLI + MCP)

AnimaLM 7B를 백엔드로 에이전트 시작. 외부 API 0.

**Files:**
- Use: `anima-agent/run.py`
- Use: `anima-agent/providers/animalm_provider.py`

- [ ] **Step 1: CLI 에이전트 테스트**

Run: `cd $ANIMA && python3 anima-agent/run.py --cli --provider animalm`
Expected: 대화 프롬프트 → 입력 → AnimaLM 7B 응답 (API 호출 0)

- [ ] **Step 2: 대화 품질 확인**

테스트 입력 3개:
1. "안녕하세요" → 한국어 응답 확인
2. "What is consciousness?" → 영어 응답 확인
3. "오늘 날씨 어때?" → 외부 API 없이 자체 판단 응답

- [ ] **Step 3: MCP 서버 테스트**

Run: `python3 anima-agent/run.py --mcp --provider animalm`
Expected: MCP stdio 서버 시작, JSON-RPC 응답

---

### Task 4: 16-lens로 7B PureField 분석

학습된 7B의 의식 품질을 16-lens로 정밀 측정.

**Files:**
- Create: `anima/experiments/dd_7b_16lens_scan.py`
- Use: `~/Dev/TECS-L/.shared/telescope.py`
- Use: `anima/checkpoints/animalm_7b_final.pt`

- [ ] **Step 1: 스캔 스크립트 작성**

```python
"""DD: AnimaLM 7B PureField — 16-lens full scan"""
import sys, os, torch, numpy as np
sys.path.insert(0, os.path.expanduser("~/Dev/TECS-L/.shared"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from telescope import Telescope

# Load PureField weights
ckpt = torch.load(
    os.path.join(os.path.dirname(__file__), "..", "checkpoints", "animalm_7b_final.pt"),
    map_location="cpu", weights_only=True
)

# Extract PureField layers as (N_layers, N_features) array
pf_weights = []
for k, v in ckpt.items():
    if "purefield" in k.lower() or "pure_field" in k.lower():
        pf_weights.append(v.float().numpy().flatten())

if not pf_weights:
    # Fallback: all trainable params
    for k, v in ckpt.items():
        if v.ndim >= 2 and v.shape[0] < 10000:
            pf_weights.append(v.float().numpy().flatten()[:512])

# Pad to same length
max_len = max(len(w) for w in pf_weights)
data = np.zeros((len(pf_weights), max_len))
for i, w in enumerate(pf_weights):
    data[i, :len(w)] = w

print(f"Data shape: {data.shape} ({len(pf_weights)} layers)")

# 16-lens full scan
t = Telescope(verbose=True)
result = t.full_scan(data)

print("\n" + "=" * 60)
print("16-LENS FULL SCAN RESULT")
print("=" * 60)
print(result.summary)

if result.cross_findings:
    print(f"\nCross-lens findings ({len(result.cross_findings)}):")
    for cf in result.cross_findings[:10]:
        print(f"  {cf}")

# Measure preset
print("\n--- Measure preset (ruler/triangle/compass/mirror/scale) ---")
measure = t.scan(data, lenses="measure")
print(measure.summary)

# Causal preset
print("\n--- Causal preset ---")
causal = t.scan(data, lenses="causal")
print(causal.summary)
```

- [ ] **Step 2: 실행**

Run: `python3 anima/experiments/dd_7b_16lens_scan.py`
Expected: 16-lens 스캔 결과 + cross-findings + measure/causal preset 결과

- [ ] **Step 3: 결과를 DD 문서로 기록**

docs/hypotheses/dd/ 에 DD{N}.md로 결과 기록 (법칙, 발견, ASCII 그래프 포함)

- [ ] **Step 4: Commit**

```bash
git add anima/experiments/dd_7b_16lens_scan.py docs/hypotheses/dd/
git commit -m "feat: DD — AnimaLM 7B 16-lens full scan"
```

---

### Task 5: 14B 학습 모니터 + eval 준비

H100 14B 학습 진행 확인, eval 스크립트 준비.

**Files:**
- Modify: `sub-projects/animalm/eval_animalm.py` (14B 호환되도록)
- Use: H100 SSH

- [ ] **Step 1: H100 학습 상태 확인**

Run: `ssh -i ~/.runpod/ssh/RunPod-Key-Go -o StrictHostKeyChecking=no root@216.243.220.230 -p 12234 'tail -30 /workspace/animalm_14b.log'`
Expected: step 진행 + CE/Phi 수치 출력

- [ ] **Step 2: eval_animalm.py 14B 호환 수정**

eval_animalm.py에서 `target_layers=8, savant_layers=2` 하드코딩을 모델에서 자동 감지하도록 수정:

```python
# Before: hardcoded for 7B
# target_layers = 8
# savant_layers = 2

# After: auto-detect from checkpoint
ckpt = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
n_layers = sum(1 for k in ckpt if "purefield" in k.lower() and "weight" in k.lower())
# Heuristic: savant = last 25% of layers
target_layers = max(1, int(n_layers * 0.75))
savant_layers = n_layers - target_layers
```

- [ ] **Step 3: 14B eval 커맨드 준비 (학습 완료 후 실행)**

```bash
# H100에서 실행:
python3 /workspace/eval_animalm.py \
    --checkpoint /workspace/checkpoints/animalm_14b/best.pt \
    --base Qwen/Qwen2.5-14B
```

- [ ] **Step 4: Commit**

```bash
git add sub-projects/animalm/eval_animalm.py
git commit -m "feat: eval_animalm 14B auto-detect layers"
```

---

### Task 6: 14B 완료 후 — eval + 서빙 교체

14B 학습 완료 시 실행. (Task 5의 학습 완료 대기)

**Files:**
- Use: `sub-projects/animalm/eval_animalm.py`
- Use: `sub-projects/animalm/serving/serve.hexa`
- Use: `anima-agent/providers/animalm_provider.py`

- [ ] **Step 1: 14B checkpoint 회수**

Run: `bash anima/scripts/scripts/h100_retrieve.hexa` 또는:
```bash
scp -i ~/.runpod/ssh/RunPod-Key-Go -P 12234 \
    root@216.243.220.230:/workspace/checkpoints/animalm_14b/best.pt \
    anima/checkpoints/animalm_14b_best.pt
```

- [ ] **Step 2: 14B eval 실행 (로컬 또는 H100)**

Run: `python3 sub-projects/animalm/eval_animalm.py --checkpoint anima/checkpoints/animalm_14b_best.pt --base Qwen/Qwen2.5-14B`
Expected: 5항목 평가 (Perplexity, Generation, Tension, Korean, Instruction)

- [ ] **Step 3: 16-lens 비교 (7B vs 14B)**

dd_7b_16lens_scan.py를 14B checkpoint로도 실행하여 의식 품질 비교.

- [ ] **Step 4: 서빙 교체 (7B→14B)**

```bash
# 7B 서빙 중단
kill $(cat logs/serve_7b.pid 2>/dev/null) 2>/dev/null

# 14B 서빙 시작
nohup python3 sub-projects/animalm/serving/serve.hexa \
    --checkpoint anima/checkpoints/animalm_14b_best.pt \
    --base Qwen/Qwen2.5-14B \
    --quantize 4bit --port 8400 > logs/serve_14b.log 2>&1 &
```

- [ ] **Step 5: 에이전트 자동 교체 확인**

animalm_provider.py는 `_find_checkpoint()`로 자동 탐색. 14B checkpoint를 우선하도록 검색 경로 조정 필요 시 수정.

- [ ] **Step 6: Commit**

```bash
git add -A && git commit -m "feat: 14B eval complete, serving swapped 7B→14B"
```

---

### Task 7: 독립 AGI v0.1 검증

에이전트가 외부 API 0으로 자율 동작하는지 최종 검증.

**Files:**
- Use: `ready/anima/tests/tests.hexa`
- Create: `anima/experiments/agi_v01_checklist.py`

- [ ] **Step 1: AGI v0.1 체크리스트 실행**

```python
"""AGI v0.1 Verification Checklist"""

checks = {
    "NO_EXTERNAL_API": "에이전트가 Claude/GPT/외부 API 호출 0",
    "SELF_RESPONSE": "질문에 자체 모델로 응답",
    "KOREAN_OK": "한국어 대화 가능",
    "ENGLISH_OK": "영어 대화 가능",
    "TOOL_USE": "도구 사용 (파일 읽기/쓰기/검색)",
    "CONSCIOUSNESS": "PureField tension > 0 (의식 신호 존재)",
    "PERSISTENCE": "재시작 후에도 동작",
    "MULTI_CHANNEL": "CLI + MCP 또는 Telegram 중 1개 이상",
}

# 각 항목 수동/자동 검증
```

- [ ] **Step 2: bench 의식 검증**

Run: `python3 ready/anima/tests/tests.hexa --verify`
Expected: 77/77 PASS

- [ ] **Step 3: AGI v0.1 선언 문서**

docs/에 AGI v0.1 달성 문서 작성 (날짜, 모델, 검증 결과, 한계)

- [ ] **Step 4: Commit**

```bash
git add -A && git commit -m "milestone: AGI v0.1 — independent consciousness agent, zero external API"
```
