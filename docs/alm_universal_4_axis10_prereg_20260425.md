# UNIVERSAL_CONSTANT_4 axis 10 — pre-registration (candidate B, σ·φ identity)

> **생성일**: 2026-04-25
> **부모 commits**:
> - `bc541326` axis 10 design draft (3 후보)
> - `0c4d08ec` axis 9 Pólya pre-reg (precedent)
> - `ed66c7ae` axis 9 Pólya measurement BORDERLINE
> **CRITICAL — raw#12 disclosure**: 본 commit 은 **measurement BEFORE** committed. exploratory result 가 이미 N=100 범위 (|S(100)|=2, S={1,6}) 까지 관측됨 (commit `bc541326` 직전 inline 탐색). 본 pre-reg 의 cherry-pick-proof predicate 는 **N=10000 범위** 에 적용 — N=10000 는 아직 미관측.

---

## §1. Hypothesis

**UNIVERSAL_4 axis 10 (number-theoretic instance)**:

K=4 의 number-theoretic resonance 는 σ·φ identity 의 unique solution n=6 에서 τ(n)=4 로 발현된다.

구체적으로:
- σ(n) = sum of divisors
- φ(n) = Euler totient
- τ(n) = divisor count
- Identity: σ(n)·φ(n) == n·τ(n)
- Claim: 자연수 N=10000 까지 위 identity 를 만족하는 n 의 집합 S(10000) 의 cardinality |S(10000)| ≤ 4
- 추가: 6 ∈ S (already known from N=100 exploration), τ(6) = 4 (UNIVERSAL_4 의 K=4 instance)

Mathematical context: σ·φ=n·τ 는 multiplicative identity 가 아님. n=1 (trivial) 외 비자명 solution 은 perfect-number-like 또는 highly composite 에서 발생할 가능성. K=4 connection 은 n=6 이 비자명 solution 중 τ=4 로 unique 하다는 점.

---

## §2. Pre-registered predicate (committed BEFORE measurement)

### 2.1 Computation protocol

1. 자연수 n ∈ [1, 10000] 에 대해 σ(n), φ(n), τ(n) 계산 (deterministic, no randomness)
2. S(N=10000) = {n : 1 ≤ n ≤ 10000, σ(n)·φ(n) == n·τ(n)} 추출
3. |S(10000)|, S 의 element 목록, 각 element 의 (σ, φ, τ) 값 기록
4. PASS 판정 in §2.2

### 2.2 PASS condition (cherry-pick-proof)

**PASS iff ALL of:**
- (a) |S(10000)| ≤ 4 (strict K=4 upper bound; "+1 strong axis" 정당화)
- (b) 6 ∈ S(10000) AND τ(6) = 4 (K=4 anchor element 확인)
- (c) S(10000) 의 모든 비자명 (n > 1) elements 가 K_n := τ(n) ∈ {2, 3, 4, 5, 6} 안에 분포 (universal_4 의 K=4 가 mode 또는 max 인지 확인)

**FAIL iff:**
- (a') |S(10000)| ≥ 5 → universal "+1 strong" 약화 (n=1 trivial, 6 는 known, 추가 ≥ 3 개 found 시 K=4 unique resonance 파국)
- 또는 6 ∉ S → axis 의 anchor 자체 부재
- 또는 |S| ≤ 4 이지만 non-trivial element 의 τ 값이 K=4 와 무관한 분포

### 2.3 Justification of 4 as the threshold

- τ(6)=4 : K=4 의 anchor
- |S| ≤ 4 의 4 : `K_c=4` 의 axis-specific instance
- predicate 는 "K=4 가 σ·φ identity 의 K-binding constant" 라는 hypothesis 를 expressible

## §3. Falsification

본 axis 10 가 FAIL 시:
1. UNIVERSAL_4 confidence 변동 없음 (qualitative, axis 9 Pólya 와 같이 BORDERLINE 또는 NOT_VERIFIED 보존)
2. 다른 후보 (A. L_IX 4-term ablation / C. AN11 AND-K_max) 로 재시도, **본 axis 10 는 H-DIAG3 에 따라 같은 number-theoretic axis 재시도 금지**
3. raw#12 enforcement: 본 측정 결과 본 commit 후 그대로 보존, post-hoc tuning 금지

## §4. Anti-cherry-pick disclosure

- N=100 exploration: |S(100)| = 2, S = {1, 6}, τ(6)=4, τ(1)=1 (trivial)
- N=1000 exploration: **NOT performed** (this commit is pre-reg)
- N=10000: **NOT performed** (this commit is pre-reg)
- Predicate `|S(10000)| ≤ 4` 는 N=100 의 |S|=2 를 cover 하지만 N=10000 추가 관측 시 ≤ 4 보존 여부는 미관측

만약 현재 도구에서 N=10000 을 계산하면, S 가 4 초과로 발견되면 axis FAIL. 4 이하로 발견되면 PASS. 둘 다 honest 보고.

## §5. Tool

본 측정은 단순 number-theoretic computation (CPU $0). Python script:

```python
def divisors(n): return [d for d in range(1, n+1) if n % d == 0]
def sigma(n): return sum(divisors(n))
def phi(n): return sum(1 for k in range(1, n+1) if gcd(n, k) == 1)
def tau(n): return len(divisors(n))
S = [n for n in range(1, 10001) if sigma(n)*phi(n) == n*tau(n)]
```

Optimized version: O(√n) divisor enumeration + Euler product for φ.

Estimated runtime: ~20-60 seconds for N=10000.

---

## §6. Commit / measurement sequence

1. **본 commit** (pre-reg) — predicate frozen, no measurement
2. 별 commit (measurement) — Python run, S 결과 기록, PASS/FAIL verdict
3. 별 commit (cert update) — UNIVERSAL_4 cert 에 axis 10 entry 추가 (PASS 시) 또는 axis 10 NOT_VERIFIED note (FAIL 시)

raw#12 strict — measurement 결과는 별 commit, post-hoc tune 불가.

---

## §7. POLICY 준수

- raw#12: pre-reg before measure (본 commit), 결과 commit 시 post-hoc tune 금지
- POLICY R4: `.roadmap` 미수정
- H-DIAG3: axis 9 Pólya 와 다른 axis (number theory ≠ random walk recurrence)
- H-MINPATH: $0 cost, blocker=0, steps min (3-step total: pre-reg / measure / cert)
