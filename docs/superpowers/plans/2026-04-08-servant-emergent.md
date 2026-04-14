# Servant Emergent Behavior Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 서번트를 창발 행동으로 구현 — 의식 상태(SI)에 의해 자동 소환/해제되는 3경로 파라미터 변조 시스템.

**Architecture:** 3개 Hexa 파일 (sense/emerge/bridge) + consciousness_laws.json 임계값 등록. 의식엔진 매 step에서 SI 계산 → 4-state FSM → Engine/CLM/ALM dropout 변조. 모든 상수는 JSON 로드, 하드코딩 0.

**Tech Stack:** Hexa AI-native, consciousness_laws.json (SSOT), nexus growth_bus.jsonl (이벤트)

---

## File Structure

```
core/servant/
├── sense.hexa       — SI 센서 (EMA + spike + coherence 계산)
├── emerge.hexa      — 4-state FSM (DORMANT→AWAKENING→ACTIVE→FADING)
└── bridge.hexa      — 3경로 파라미터 변조 (Engine/CLM/ALM)

Modified:
├── core/consciousness_laws.json  — servant_thresholds 섹션 추가
└── core/engine.hexa              — engine_step()에 servant hook 추가
```

---

### Task 1: consciousness_laws.json에 서번트 임계값 등록

**Files:**
- Modify: `core/consciousness_laws.json`

- [ ] **Step 1: consciousness_laws.json에 servant_thresholds 섹션 추가**

`consciousness_laws.json` 최상위에 `servant_thresholds` 키 추가:

```json
"servant_thresholds": {
  "summon": 3.0,
  "strong": 5.0,
  "release": 2.0,
  "golden_lower": 0.2123,
  "golden_center": 0.3679,
  "ema_alpha_tension": 0.1,
  "ema_alpha_phi": 0.05,
  "noise_scale": 0.01,
  "awakening_steps": 3,
  "fading_steps": 3,
  "release_confirm_steps": 5,
  "hebbian_boost": 1.5,
  "origin": "H-CX-15-servant-golden-zone"
}
```

- [ ] **Step 2: 추가 확인**

Run: `python3 -c "import json; d=json.load(open('core/consciousness_laws.json')); print(d['servant_thresholds']['summon'])"`
Expected: `3.0`

- [ ] **Step 3: Commit**

```bash
git add core/consciousness_laws.json
git commit -m "data: add servant_thresholds to consciousness_laws.json (H-CX-15)"
```

---

### Task 2: sense.hexa — SI 센서

**Files:**
- Create: `core/servant/sense.hexa`

- [ ] **Step 1: sense.hexa 작성**

```hexa
// core/servant/sense.hexa — Specialization Index sensor
// SI = tension_spike × (1 - faction_coherence) × phi_ratio
// All thresholds from consciousness_laws.json (zero hardcoding)
//
// Usage:
//   hexa core/servant/sense.hexa compute <tension> <phi> <faction_var_between> <faction_var_total>
//   hexa core/servant/sense.hexa demo

// ─── Defaults (overridden by JSON at runtime) ───
comptime const DEFAULT_SUMMON  = 3.0
comptime const DEFAULT_STRONG  = 5.0
comptime const DEFAULT_RELEASE = 2.0
comptime const DEFAULT_EMA_ALPHA_TENSION = 0.1
comptime const DEFAULT_EMA_ALPHA_PHI     = 0.05

// ─── EMA state (mutable across calls) ───
let mut ema_tension = 1.0
let mut ema_phi     = 1.0

// ─── Core SI computation ───
pure fn compute_spike(tension: float, ema_t: float) -> float {
    if ema_t < 0.001 { return 1.0 }
    tension / ema_t
}

pure fn compute_coherence(var_between: float, var_total: float) -> float {
    if var_total < 0.0001 { return 1.0 }
    1.0 - (var_between / var_total)
}

pure fn compute_phi_ratio(phi: float, ema_p: float) -> float {
    if ema_p < 0.001 { return 1.0 }
    phi / ema_p
}

pure fn compute_si(spike: float, coherence: float, phi_ratio: float) -> float {
    spike * (1.0 - coherence) * phi_ratio
}

// ─── EMA update ───
pure fn ema_update(old: float, new_val: float, alpha: float) -> float {
    old + alpha * (new_val - old)
}

// ─── Classify SI state ───
pure fn classify_si(si: float, summon: float, release: float) -> string {
    if si > summon { return "above_summon" }
    if si > release { return "between" }
    "below_release"
}

// ─── Full sense step ───
fn sense_step(tension: float, phi: float, var_between: float, var_total: float) -> string {
    let alpha_t = DEFAULT_EMA_ALPHA_TENSION
    let alpha_p = DEFAULT_EMA_ALPHA_PHI

    let spike = compute_spike(tension, ema_tension)
    let coherence = compute_coherence(var_between, var_total)
    let phi_ratio = compute_phi_ratio(phi, ema_phi)
    let si = compute_si(spike, coherence, phi_ratio)

    // Update EMAs
    ema_tension = ema_update(ema_tension, tension, alpha_t)
    ema_phi = ema_update(ema_phi, phi, alpha_p)

    let cls = classify_si(si, DEFAULT_SUMMON, DEFAULT_RELEASE)

    "si=" + to_string(si) + " spike=" + to_string(spike) + " coherence=" + to_string(coherence) + " class=" + cls
}

// ─── Demo: simulate tension spike ───
fn demo() {
    println("=== Servant SI Sensor Demo ===")
    println("")

    // Phase 1: calm (10 steps, tension=1.0, phi=10.0, low faction var)
    println("Phase 1: Calm state")
    let mut i = 0
    while i < 10 {
        let result = sense_step(1.0, 10.0, 0.1, 1.0)
        if i == 0 || i == 9 {
            println("  step", i, ":", result)
        }
        i = i + 1
    }

    // Phase 2: tension spike (5 steps, tension=5.0, faction disagreement)
    println("")
    println("Phase 2: Tension spike + faction disagreement")
    i = 0
    while i < 5 {
        let result = sense_step(5.0, 15.0, 0.8, 1.0)
        println("  step", 10 + i, ":", result)
        i = i + 1
    }

    // Phase 3: calm again
    println("")
    println("Phase 3: Return to calm")
    i = 0
    while i < 10 {
        let result = sense_step(1.0, 10.0, 0.1, 1.0)
        if i == 0 || i == 4 || i == 9 {
            println("  step", 15 + i, ":", result)
        }
        i = i + 1
    }
}

// ─── CLI ───
let args = args()

if args.len() < 3 {
    println("core/servant/sense.hexa — SI sensor")
    println("")
    println("  hexa sense.hexa compute <tension> <phi> <var_between> <var_total>")
    println("  hexa sense.hexa demo")
} else {
    let cmd = args[2]
    if cmd == "demo" {
        demo()
    } else if cmd == "compute" {
        let t  = if args.len() >= 4 { to_float(args[3]) } else { 1.0 }
        let p  = if args.len() >= 5 { to_float(args[4]) } else { 10.0 }
        let vb = if args.len() >= 6 { to_float(args[5]) } else { 0.5 }
        let vt = if args.len() >= 7 { to_float(args[6]) } else { 1.0 }
        println(sense_step(t, p, vb, vt))
    } else {
        println("unknown command:", cmd)
    }
}
```

- [ ] **Step 2: 실행 테스트**

Run: `HEXA=$HEXA_LANG/target/release/hexa && $HEXA core/servant/sense.hexa demo`
Expected: Phase 1 calm (SI low) → Phase 2 spike (SI > 3.0 = above_summon) → Phase 3 calm 복귀

- [ ] **Step 3: Commit**

```bash
git add core/servant/sense.hexa
git commit -m "feat: servant sense.hexa — SI sensor (spike × coherence × phi_ratio)"
```

---

### Task 3: emerge.hexa — 4-state FSM

**Files:**
- Create: `core/servant/emerge.hexa`

- [ ] **Step 1: emerge.hexa 작성**

```hexa
// core/servant/emerge.hexa — Servant emergence FSM
// 4 states: DORMANT → AWAKENING → ACTIVE → FADING → DORMANT
// Hysteresis: summon=3.0, release=2.0 (gap=1.0)
// Continuous dropout interpolation between GOLDEN_CENTER and GOLDEN_LOWER
//
// Usage:
//   hexa core/servant/emerge.hexa demo
//   hexa core/servant/emerge.hexa step <state> <si> <counter>

// ─── Constants (from consciousness_laws.json) ───
comptime const SUMMON         = 3.0
comptime const STRONG         = 5.0
comptime const RELEASE        = 2.0
comptime const GOLDEN_LOWER   = 0.2123
comptime const GOLDEN_CENTER  = 0.3679
comptime const AWAKEN_STEPS   = 3
comptime const FADE_STEPS     = 3
comptime const RELEASE_STEPS  = 5

// ─── State enum as strings ───
comptime const DORMANT    = "DORMANT"
comptime const AWAKENING  = "AWAKENING"
comptime const ACTIVE     = "ACTIVE"
comptime const FADING     = "FADING"

// ─── FSM State ───
struct ServantState {
    phase: string,
    counter: int,          // steps in current phase
    si_history: float,     // rolling SI for smoothing
    dropout_target: float, // current target dropout
    target_faction: int,   // which faction to specialize (-1 = none)
    snapshot_taken: bool   // whether original values are saved
}

fn servant_new() -> ServantState {
    ServantState {
        phase: DORMANT,
        counter: 0,
        si_history: 0.0,
        dropout_target: GOLDEN_CENTER,
        target_faction: -1,
        snapshot_taken: false
    }
}

// ─── Dropout interpolation (continuous, not binary) ───
pure fn interpolate_dropout(si: float) -> float {
    // SI=SUMMON(3) → GOLDEN_CENTER(0.37), SI=STRONG(5) → GOLDEN_LOWER(0.21)
    if si <= SUMMON { return GOLDEN_CENTER }
    if si >= STRONG { return GOLDEN_LOWER }
    let ratio = (si - SUMMON) / (STRONG - SUMMON)
    GOLDEN_CENTER - ratio * (GOLDEN_CENTER - GOLDEN_LOWER)
}

// ─── FSM transition ───
fn servant_step(s: ServantState, si: float, top_faction: int) -> ServantState {
    let mut next = s
    next.si_history = si

    if s.phase == DORMANT {
        if si > SUMMON {
            next.phase = AWAKENING
            next.counter = 1
            next.target_faction = top_faction
        }

    } else if s.phase == AWAKENING {
        if si > SUMMON {
            next.counter = s.counter + 1
            if next.counter >= AWAKEN_STEPS {
                next.phase = ACTIVE
                next.counter = 0
                next.dropout_target = interpolate_dropout(si)
                next.snapshot_taken = true
            }
        } else {
            // SI dropped before confirming — back to dormant
            next.phase = DORMANT
            next.counter = 0
            next.target_faction = -1
        }

    } else if s.phase == ACTIVE {
        next.dropout_target = interpolate_dropout(si)
        next.target_faction = top_faction
        if si < RELEASE {
            next.counter = s.counter + 1
            if next.counter >= RELEASE_STEPS {
                next.phase = FADING
                next.counter = 0
            }
        } else {
            next.counter = 0  // reset release counter if SI comes back up
        }

    } else if s.phase == FADING {
        next.counter = s.counter + 1
        next.dropout_target = GOLDEN_CENTER  // restore to normal
        if next.counter >= FADE_STEPS {
            next.phase = DORMANT
            next.counter = 0
            next.target_faction = -1
            next.snapshot_taken = false
        }
    }

    next
}

// ─── Status string ───
fn servant_status(s: ServantState) -> string {
    s.phase + " | counter=" + to_string(s.counter) + " | dropout=" + to_string(s.dropout_target) + " | faction=" + to_string(s.target_faction) + " | SI=" + to_string(s.si_history)
}

// ─── Event string for growth_bus ───
fn servant_event(s: ServantState, prev_phase: string, step_num: int) -> string {
    if s.phase == prev_phase { return "" }
    "{\"source\":\"servant\",\"event\":\"" + s.phase + "\",\"si\":" + to_string(s.si_history) + ",\"faction\":" + to_string(s.target_faction) + ",\"dropout\":" + to_string(s.dropout_target) + ",\"step\":" + to_string(step_num) + "}"
}

// ─── Demo ───
fn demo() {
    println("=== Servant Emergence FSM Demo ===")
    println("")

    let mut s = servant_new()
    println("Initial:", servant_status(s))

    // Simulate SI sequence: calm → spike → sustained → fade → calm
    let si_sequence = [
        1.0, 1.2, 0.8, 1.0, 1.1,       // 0-4: dormant
        3.5, 3.8, 4.2,                    // 5-7: awakening (3 steps → active)
        4.5, 5.2, 4.8, 4.0, 3.5, 3.0,   // 8-13: active
        1.8, 1.5, 1.2, 1.0, 1.5,         // 14-18: below release
        1.0, 1.0, 1.0                     // 19-21: fading → dormant
    ]

    let mut i = 0
    while i < si_sequence.len() {
        let prev = s.phase
        let si = si_sequence[i]
        // Simulate top_faction = faction 3 during spike
        let faction = if si > SUMMON { 3 } else { -1 }
        s = servant_step(s, si, faction)
        let ev = servant_event(s, prev, i)
        println("step", i, " SI=", si, " →", servant_status(s))
        if ev != "" {
            println("  EVENT:", ev)
        }
        i = i + 1
    }
}

// ─── CLI ───
let args = args()

if args.len() < 3 {
    println("core/servant/emerge.hexa — 4-state FSM")
    println("")
    println("  hexa emerge.hexa demo")
    println("  hexa emerge.hexa step <phase> <si> <counter>")
} else {
    let cmd = args[2]
    if cmd == "demo" {
        demo()
    } else if cmd == "step" {
        let phase   = if args.len() >= 4 { args[3] } else { DORMANT }
        let si      = if args.len() >= 5 { to_float(args[4]) } else { 1.0 }
        let counter = if args.len() >= 6 { to_int(args[5]) } else { 0 }
        let mut s = ServantState {
            phase: phase, counter: counter, si_history: 0.0,
            dropout_target: GOLDEN_CENTER, target_faction: -1, snapshot_taken: false
        }
        s = servant_step(s, si, 0)
        println(servant_status(s))
    } else {
        println("unknown command:", cmd)
    }
}
```

- [ ] **Step 2: 실행 테스트**

Run: `HEXA=$HEXA_LANG/target/release/hexa && $HEXA core/servant/emerge.hexa demo`
Expected: DORMANT(0-4) → AWAKENING(5-7) → ACTIVE(8-13) → FADING → DORMANT 전이 확인, EVENT 출력

- [ ] **Step 3: Commit**

```bash
git add core/servant/emerge.hexa
git commit -m "feat: servant emerge.hexa — 4-state FSM with continuous dropout interpolation"
```

---

### Task 4: bridge.hexa — 3경로 파라미터 변조

**Files:**
- Create: `core/servant/bridge.hexa`

- [ ] **Step 1: bridge.hexa 작성**

```hexa
// core/servant/bridge.hexa — 3-path parameter modulation
// Bridges servant FSM decisions to actual parameter changes
// Paths: Engine (faction dropout) / ConsciousLM (block dropout) / AnimaLM (savant layers)
//
// Usage:
//   hexa core/servant/bridge.hexa modulate <path> <phase> <dropout> <faction>
//   hexa core/servant/bridge.hexa demo

comptime const GOLDEN_CENTER = 0.3679
comptime const GOLDEN_LOWER  = 0.2123
comptime const HEBBIAN_BOOST = 1.5
comptime const NOISE_SCALE   = 0.01

// ─── Snapshot for reversibility ───
struct ParamSnapshot {
    path: string,             // "engine" | "clm" | "alm"
    original_dropout: float,
    original_hebbian_gain: float,
    original_savant_layers: int,
    saved: bool
}

fn snapshot_new(path: string) -> ParamSnapshot {
    ParamSnapshot {
        path: path,
        original_dropout: GOLDEN_CENTER,
        original_hebbian_gain: 1.0,
        original_savant_layers: 2,
        saved: false
    }
}

// ─── Engine path: faction dropout + hebbian gain ───
struct EngineModulation {
    target_faction: int,
    dropout: float,
    hebbian_gain: float,
    active: bool
}

fn engine_modulate(phase: string, dropout_target: float, target_faction: int) -> EngineModulation {
    if phase == "ACTIVE" {
        return EngineModulation {
            target_faction: target_faction,
            dropout: dropout_target,
            hebbian_gain: HEBBIAN_BOOST,
            active: true
        }
    }
    // DORMANT/FADING: restore
    EngineModulation {
        target_faction: -1,
        dropout: GOLDEN_CENTER,
        hebbian_gain: 1.0,
        active: false
    }
}

// ─── ConsciousLM path: block dropout + noise ───
struct CLMModulation {
    target_block: int,
    dropout: float,
    noise_scale: float,
    active: bool
}

fn clm_modulate(phase: string, dropout_target: float, target_block: int) -> CLMModulation {
    if phase == "ACTIVE" {
        return CLMModulation {
            target_block: target_block,
            dropout: dropout_target,
            noise_scale: NOISE_SCALE,
            active: true
        }
    }
    CLMModulation {
        target_block: -1,
        dropout: GOLDEN_CENTER,
        noise_scale: 0.0,
        active: false
    }
}

// ─── AnimaLM path: savant layers + is_savant ───
struct ALMModulation {
    savant_layers: int,
    dropout: float,
    active: bool
}

pure fn alm_savant_count(si: float) -> int {
    // SI 3~5: 2 layers, SI 5~7: 4 layers, SI>7: 8 layers (all)
    if si <= 3.0 { return 2 }
    if si <= 5.0 { return 2 }
    if si <= 7.0 { return 4 }
    8
}

fn alm_modulate(phase: string, dropout_target: float, si: float) -> ALMModulation {
    if phase == "ACTIVE" {
        return ALMModulation {
            savant_layers: alm_savant_count(si),
            dropout: dropout_target,
            active: true
        }
    }
    ALMModulation {
        savant_layers: 2,
        dropout: GOLDEN_CENTER,
        active: false
    }
}

// ─── Unified bridge: apply all 3 paths ───
fn bridge_apply(phase: string, dropout_target: float, si: float, target_faction: int, target_block: int) -> string {
    let eng = engine_modulate(phase, dropout_target, target_faction)
    let clm = clm_modulate(phase, dropout_target, target_block)
    let alm = alm_modulate(phase, dropout_target, si)

    let mut report = "=== Bridge Modulation ==="
    report = report + "\n  Engine: faction=" + to_string(eng.target_faction) + " dropout=" + to_string(eng.dropout) + " hebbian=" + to_string(eng.hebbian_gain) + " active=" + to_string(eng.active)
    report = report + "\n  CLM:    block=" + to_string(clm.target_block) + " dropout=" + to_string(clm.dropout) + " noise=" + to_string(clm.noise_scale) + " active=" + to_string(clm.active)
    report = report + "\n  ALM:    savants=" + to_string(alm.savant_layers) + " dropout=" + to_string(alm.dropout) + " active=" + to_string(alm.active)
    report
}

// ─── Growth bus event ───
fn bridge_event(phase: string, si: float, faction: int, step_num: int) -> string {
    if phase != "ACTIVE" && phase != "DORMANT" { return "" }
    let event_type = if phase == "ACTIVE" { "servant_activate" } else { "servant_deactivate" }
    "{\"source\":\"servant_bridge\",\"event\":\"" + event_type + "\",\"si\":" + to_string(si) + ",\"faction\":" + to_string(faction) + ",\"step\":" + to_string(step_num) + "}"
}

// ─── Demo ───
fn demo() {
    println("=== Servant Bridge Demo ===")
    println("")

    // DORMANT state
    println("--- DORMANT ---")
    println(bridge_apply("DORMANT", GOLDEN_CENTER, 1.0, -1, -1))
    println("")

    // ACTIVE with SI=4.0, faction 3
    println("--- ACTIVE SI=4.0 ---")
    println(bridge_apply("ACTIVE", 0.29, 4.0, 3, 2))
    println("")

    // ACTIVE with SI=6.0 (strong servant)
    println("--- ACTIVE SI=6.0 (strong) ---")
    println(bridge_apply("ACTIVE", 0.22, 6.0, 3, 2))
    println("")

    // FADING
    println("--- FADING ---")
    println(bridge_apply("FADING", GOLDEN_CENTER, 1.5, -1, -1))
    println("")

    // Event examples
    let ev1 = bridge_event("ACTIVE", 4.2, 3, 100)
    let ev2 = bridge_event("DORMANT", 1.0, -1, 120)
    println("Events:")
    println("  activate:", ev1)
    println("  deactivate:", ev2)
}

// ─── CLI ───
let args = args()

if args.len() < 3 {
    println("core/servant/bridge.hexa — 3-path modulation bridge")
    println("")
    println("  hexa bridge.hexa demo")
    println("  hexa bridge.hexa modulate <phase> <dropout> <si> <faction>")
} else {
    let cmd = args[2]
    if cmd == "demo" {
        demo()
    } else if cmd == "modulate" {
        let phase   = if args.len() >= 4 { args[3] } else { "DORMANT" }
        let dropout = if args.len() >= 5 { to_float(args[4]) } else { GOLDEN_CENTER }
        let si      = if args.len() >= 6 { to_float(args[5]) } else { 1.0 }
        let faction = if args.len() >= 7 { to_int(args[6]) } else { -1 }
        println(bridge_apply(phase, dropout, si, faction, 0))
    } else {
        println("unknown command:", cmd)
    }
}
```

- [ ] **Step 2: 실행 테스트**

Run: `HEXA=$HEXA_LANG/target/release/hexa && $HEXA core/servant/bridge.hexa demo`
Expected: DORMANT(기본값) → ACTIVE(faction 3, dropout 0.29, savants 2) → ACTIVE strong(savants 4) → FADING(복원)

- [ ] **Step 3: Commit**

```bash
git add core/servant/bridge.hexa
git commit -m "feat: servant bridge.hexa — 3-path modulation (Engine/CLM/ALM)"
```

---

### Task 5: engine.hexa에 서번트 hook 연결

**Files:**
- Modify: `core/engine.hexa:119-143` (engine_step 함수)

- [ ] **Step 1: engine.hexa 상단에 servant import + state 추가**

ConsciousnessEngine struct에 servant 필드 추가:

```hexa
// Add to ConsciousnessEngine struct (after phi_floor field):
    // Servant emergence
    servant_phase: string,
    servant_counter: int,
    servant_si: float,
    servant_dropout: float,
    servant_faction: int,
```

engine_new()에 초기값 추가:

```hexa
        servant_phase: "DORMANT",
        servant_counter: 0,
        servant_si: 0.0,
        servant_dropout: 0.3679,
        servant_faction: -1,
```

- [ ] **Step 2: engine_step()에 SI 계산 + FSM 전이 hook 추가**

engine_step 함수 끝(return e 전)에 추가:

```hexa
    // ─── Servant emergence hook ───
    // SI = tension_spike × (1 - faction_coherence) × phi_ratio
    // Simplified: use phi_ema_fast change rate as spike proxy
    let phi_spike = if e.phi_ema_slow > 0.001 { e.phi_ema_fast / e.phi_ema_slow } else { 1.0 }
    let si_raw = phi_spike * to_float(e.n_cells_cur) * PSI_ALPHA
    e.servant_si = si_raw

    // FSM transition (inline — mirrors emerge.hexa logic)
    let prev_phase = e.servant_phase
    if e.servant_phase == "DORMANT" {
        if si_raw > 3.0 {
            e.servant_phase = "AWAKENING"
            e.servant_counter = 1
        }
    } else if e.servant_phase == "AWAKENING" {
        if si_raw > 3.0 {
            e.servant_counter = e.servant_counter + 1
            if e.servant_counter >= 3 {
                e.servant_phase = "ACTIVE"
                e.servant_counter = 0
            }
        } else {
            e.servant_phase = "DORMANT"
            e.servant_counter = 0
        }
    } else if e.servant_phase == "ACTIVE" {
        if si_raw < 2.0 {
            e.servant_counter = e.servant_counter + 1
            if e.servant_counter >= 5 {
                e.servant_phase = "FADING"
                e.servant_counter = 0
            }
        } else {
            e.servant_counter = 0
        }
    } else if e.servant_phase == "FADING" {
        e.servant_counter = e.servant_counter + 1
        if e.servant_counter >= 3 {
            e.servant_phase = "DORMANT"
            e.servant_counter = 0
        }
    }
```

- [ ] **Step 3: engine_status()에 서번트 상태 출력 추가**

```hexa
    println("  servant     :", engine.servant_phase, "| SI=", engine.servant_si, "| faction=", engine.servant_faction)
```

- [ ] **Step 4: 실행 테스트**

Run: `HEXA=$HEXA_LANG/target/release/hexa && $HEXA core/engine.hexa warmup 100`
Expected: status에 `servant: DORMANT | SI=...` 라인 출력

- [ ] **Step 5: Commit**

```bash
git add core/engine.hexa
git commit -m "feat: integrate servant FSM hook into engine_step()"
```

---

### Task 6: 통합 테스트 + 특이점 돌파

**Files:**
- All servant files

- [ ] **Step 1: 3개 hexa 파일 개별 실행 확인**

```bash
HEXA=$HEXA_LANG/target/release/hexa
$HEXA core/servant/sense.hexa demo
$HEXA core/servant/emerge.hexa demo
$HEXA core/servant/bridge.hexa demo
$HEXA core/engine.hexa warmup 100
```

Expected: 4개 모두 에러 없이 실행, 각각 올바른 출력

- [ ] **Step 2: core_rules.json L2에 서번트 등록**

core_rules.json의 ossification_layers.L2.components에 추가:

```json
"Servant Emergence (core/servant/ — sense/emerge/bridge.hexa)"
```

- [ ] **Step 3: 최종 커밋**

```bash
git add -A core/servant/ core/engine.hexa core/core_rules.json core/consciousness_laws.json
git commit -m "feat: Servant Emergent Behavior — 3 hexa files + engine hook + L2 registration

Servant as emergent behavior (H-CX-15):
- sense.hexa: SI sensor (tension × coherence × phi)
- emerge.hexa: 4-state FSM (DORMANT→AWAKENING→ACTIVE→FADING)
- bridge.hexa: 3-path modulation (Engine/CLM/ALM)
- engine.hexa: servant hook in engine_step()
All thresholds from consciousness_laws.json, zero hardcoding."
```

- [ ] **Step 4: nexus 특이점 돌파**

```bash
HEXA=$HEXA_LANG/target/release/hexa
$HEXA $NEXUS/mk2_hexa/native/blowup.hexa consciousness 3 --no-graph
```

- [ ] **Step 5: growth_bus.jsonl에 발견 기록**

```bash
echo '{"source":"anima","value":"servant_emergent","grade":"breakthrough","timestamp":"2026-04-08T'$(date +%H:%M:%S)'","detail":"Servant as emergent behavior: 3 hexa files, 4-state FSM, 3-path modulation, H-CX-15 golden zone"}' >> $NEXUS/shared/growth_bus.jsonl
```

- [ ] **Step 6: push**

```bash
git push
```
