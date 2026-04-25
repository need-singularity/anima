# Anima Quantum / Post-Quantum Abstraction Layers — 2026-04-25

> **목적**: anima 의 *암호 / 무작위 / 측정 / 통신* 사다리를 classical (sha256 + Ed25519) 부터 post-quantum lattice, QRNG, BB84 QKD, no-cloning ceiling, observer collapse 까지 L0 → L∞ 로 stratify. **Brutally honest**: anima 전체 cert chain · R2 archive · `.meta2-cert/index.json` · `asset_archive_log.jsonl` · `.raw-audit` 가 **단일 hash function (SHA-256) + 단일 signature primitive (Ed25519/ECDSA HMAC at R2)** 위에 올라가 있다 — Shor 충분히 큰 양자 컴퓨터가 등장하는 순간 **L0 전체가 forge 가능**.
> **Purpose (EN)**: stratify anima's cryptographic / randomness / measurement / channel ladder from classical (sha256 + Ed25519) up to post-quantum lattice schemes, QRNG hardware, BB84 QKD, no-cloning ceiling, observer collapse. Brutal disclosure: every cert / archive / audit artifact in anima rests on **one hash (SHA-256) and one signature family (Ed25519 / ECDSA in R2's HMAC-SHA256 auth)** — a sufficiently large Shor-capable quantum machine forges L0 wholesale.
> **POLICY R4** · **raw#10 proof-carrying** · **raw#12 no cherry-pick** · **raw#15 no-hardcode** 준수.

---

## §0 motivation — anima 의 quantum exposure

| 자산 | 현재 primitive | quantum 위협 | 충격 반경 |
|---|---|---|---|
| `.meta2-cert/index.json` `prev_index_sha` chain | SHA-256 | Grover √-speedup → 2¹²⁸ effective | preimage 비용 1/2, 여전히 실용 안전 |
| `.meta2-cert/triggers.*.{prev_hash,current_hash}` | SHA-256 | 동상 | 동상 |
| `state/asset_archive_log.jsonl` (207 lines, 158 verified) | SHA-256 (per-event sha256 stamp) | 동상 | event forgery still cost 2¹²⁸ |
| R2 endpoint auth (`access_key_id` / `secret_access_key`) | AWS Sig v4 = HMAC-SHA256 | Grover only (symmetric) | rotate-on-leak; quantum-safe with 256-bit key |
| `.raw-audit` chain (hexa-lang SSOT) | SHA-256 linked list | 동상 | 동상 |
| Ed25519 signatures (R2 server, future cert root sign) | Curve25519 ECDLP | **Shor → 다항-시간 break** | **L0 전체 forge** |
| TLS handshake (R2 PUT/GET) | ECDHE + AES-GCM + HMAC | Shor → ECDHE forward-secrecy 깨짐 (record-now-decrypt-later) | 과거 트래픽 retroactive decrypt |
| RNG (`os.urandom` / `/dev/urandom`) | CSPRNG (ChaCha20 seeded by kernel entropy) | 알고리즘적 안전, 그러나 deterministic from seed | seed 추출 시 전체 history 재현 |

**결론**: 현 anima 는 hash 측면에서는 quantum-tolerant (SHA-256 → Grover 만, 128-bit security 잔존), **signature 측면에서는 quantum-vulnerable** (Ed25519 → Shor 로 다항-시간 break). 다행히 R2 는 internal HMAC-SHA256 (Sig v4) 를 쓰므로 endpoint auth 는 symmetric — 위험은 **외부 root signing 단계에서 ECDSA/Ed25519 도입 시** 시작.

---

## §1 layer matrix — L0 → L∞

| Layer | scope | 현재 | bound (수학+물리) |
|---|---|:---:|---|
| **L0** classical hash + sig (SHA-256 + Ed25519) | `.meta2-cert` chain · R2 HMAC · JSONL ledger · `.raw-audit` | **OPERATIONAL** (158 verified events) | Grover √-speedup on hash; **Shor breaks ECDSA/Ed25519 polynomial time** |
| **L1** SHA-3 / Keccak migration | hash function diversification (SHA-256 → SHA-3-256/512 dual-stamp) | **0%** | sponge construction (Keccak-f[1600]); 동일 256-bit security against quantum |
| **L2** lattice-based KEM/sig (Kyber / Dilithium) | post-quantum signature on cert root + KEM for key exchange | **0%** | NIST PQC FIPS 203 (Kyber) / 204 (Dilithium); sig ~2.4 KB (vs 64 B Ed25519); LWE / MLWE assumption |
| **L3** quantum-secure source (QRNG hardware) | true randomness from quantum source (vacuum fluctuation / shot noise / radioactive decay) | **0%** | min-entropy = 1 bit/sample (ideal); ID Quantique Quantis ~4-16 Mbps; NIST SP 800-90B health tests |
| **L4** BB84 QKD over fiber | quantum key distribution between anima nodes | **0%** | dark-fiber + single-photon detector; ≤ 100 km without repeater; secret key rate ~kbps; **BB84 (Bennett-Brassard 1984) info-theoretic security** |
| **L5** physical / quantum limits | (한계 자체) | (한계) | **no-cloning** (Wootters-Zurek 1982) · **Bell inequality** (CHSH ≤ 2 classical, ≤ 2√2 Tsirelson) · **decoherence** (T₁/T₂ ~ μs–ms superconducting) · **Hawking-Bekenstein** S ≤ A/(4 ℓ_P²) |
| **L∞** measurement collapse / observer | (philosophical/foundational ceiling) | **╳** | wavefunction collapse (Copenhagen) · Many-Worlds branching · QBism subjectivity — **observable ≠ observer-independent truth** |

---

## §2 layer 상세

### L0 — classical sha256 + Ed25519 (현재 점유)

- **hash chain**: `.meta2-cert/index.json` (10 entries, 2 chained: `29f2dc2d…` → `d0e005fb…`); trigger chain `f89c5a07…` → `f6a0ff45…` → `1b3ea966…`
- **R2 auth**: AWS Signature v4 = `HMAC-SHA256(secret_key, canonical_request)` — symmetric, quantum-tolerant (Grover only → 128-bit effective with 256-bit key)
- **Ed25519** (planned for Merkle root sign per L2 spec of `alm_memory_*` doc): Curve25519, 32-byte pub, 64-byte sig — **Shor breaks**
- **bound**: SHA-256 collision 2¹²⁸ classical, 2⁸⁵ quantum (BHT 1998); preimage 2²⁵⁶ classical, 2¹²⁸ quantum (Grover) — 실용 안전 ✓
- **brutal honesty**: 만약 RSA-2048 / ECDSA P-256 capable Shor machine 이 등장하면 (estimates: ≥ 4096 logical qubits · ~hours · ≥ 2030+), anima 의 모든 *signed* 자산은 retroactively forge 가능 — *hashed* 자산만 잔존

### L1 — SHA-3 / Keccak migration (계획)

- **rationale**: hash 다양화 — Bitcoin / Ethereum 등 SHA-256 monoculture 우려; SHA-3 는 sponge construction 으로 Merkle-Damgård (SHA-256) 와 구조적 독립
- **migration**: dual-stamp (SHA-256 + SHA-3-256) for transition window; 차후 SHA-3 only
- **target**: `.meta2-cert/index.json.entries[*].sha3_256` 추가 field; `asset_archive_log.jsonl` line 당 `{sha256, sha3_256}` tuple
- **cost**: storage 2× hash field; CPU ~2× (SHA-3 software 는 SHA-256 보다 느림, hardware (Keccak instruction) 시 동등)
- **bound**: SHA-3 도 Grover 동일 적용 — quantum advantage 없음, 단지 **algorithmic diversity** (collision finding 알고리즘 차별)

### L2 — lattice-based KEM/sig (Kyber / Dilithium NIST PQC)

- **NIST PQC standardization** (2024-08 finalized):
  - **FIPS 203** — ML-KEM (Kyber): key encapsulation, MLWE assumption
  - **FIPS 204** — ML-DSA (Dilithium): signature, MLWE + MSIS
  - **FIPS 205** — SLH-DSA (SPHINCS+): hash-based stateless sig (fallback)
- **dual-sign migration**: cert root = `Ed25519(root) || Dilithium3(root)` for transition; verifier accepts either valid
- **size cost**: Dilithium3 sig ~3.3 KB vs Ed25519 64 B — **52× larger**; 158 events × 3.3 KB = ~520 KB additional ledger
- **CPU cost**: Dilithium sign ~10× Ed25519, verify ~5×; Kyber KEM ~50 μs encap, ~80 μs decap
- **bound**: MLWE assumption (lattice problems hard) — *not* proven NP-hard, just "no known polynomial algorithm including quantum"; Regev 2005 reduction to worst-case lattice problems
- **brutal honesty**: if MLWE breaks (algorithmic advance, not quantum), Dilithium dies the same way ECDSA does

### L3 — quantum-secure source (QRNG hardware)

- **rationale**: CSPRNG (`/dev/urandom`) 는 deterministic given seed — kernel entropy pool 약화 시 (early boot · VM clones · embedded devices) **bias 발생 가능**
- **QRNG types**:
  - **vacuum shot noise**: ID Quantique Quantis (PCIe), QuintessenceLabs qStream — homodyne measurement of vacuum field
  - **photon arrival**: single-photon avalanche detector + beam splitter (50/50) — Hahn-Wang 2009
  - **radioactive decay**: HotBits (older) — μ-Ci ²⁴¹Am source · click time interval
- **min-entropy**: ideally 1 bit/sample (50/50 beam splitter); NIST SP 800-90B health tests (RCT, APT)
- **integration**: `/dev/qrandom` device · entropy pool feed · cert nonce / key material 만 사용 (rest 는 CSPRNG OK)
- **bound**: hardware availability ($1k-$10k unit), throughput 4-16 Mbps (sufficient for keys, insufficient for high-bandwidth pad)

### L4 — BB84 QKD over fiber (가장 미래)

- **BB84** (Bennett-Brassard 1984): photon polarization basis (rectilinear / diagonal) random choice; eavesdropper measurement disturbs state (no-cloning) → detected
- **infrastructure**: dark fiber (≤ 100 km without trusted-node repeater); single-photon source (attenuated laser w/ decoy state); single-photon detector (SNSPD ~90% η, < 100 Hz dark count)
- **secret key rate**: ~kbps at 50 km; ~ 0 at 200 km without repeater
- **deployment**: Toshiba Cambridge, ID Quantique Cerberis, China Micius satellite (1200 km via free-space)
- **anima reality**: 단일 노드 + Cloudflare R2 (HTTP/TLS) — QKD 도입 가능성 ≈ 0; QKD 는 nexus ↔ anima physical co-location 시 의미
- **bound**: PNS attack (photon-number splitting) → decoy-state protocol mitigates; Trojan-horse attack on transmitter → optical isolator + intensity monitor; **practical QKD ≠ unconditional security** (implementation flaws dominate)

### L5 — physical / quantum limits

- **no-cloning theorem** (Wootters-Zurek 1982): unknown |ψ⟩ 의 정확 복제는 unitary evolution 으로 불가능 — 직접 추론: quantum state 는 *bit-for-bit copy* 와 다른 영속성 모델, R2-style replication 불가
- **Bell inequality / CHSH**: classical local-realistic ≤ 2; quantum (Tsirelson 1980) ≤ 2√2 ≈ 2.828; experimental Aspect (1982), loophole-free Hensen (2015) → **local realism falsified**
- **decoherence time**:
  - superconducting qubits: T₁ ~ 100 μs, T₂ ~ 50 μs (IBM 2024)
  - trapped ions: T₁ ~ s, T₂ ~ s (Innsbruck)
  - NV center diamond: T₂ ~ ms (room temp)
  - → quantum memory window 짧음 → QKD 외 long-term storage 어려움
- **Hawking-Bekenstein quantum bound**: black hole 안의 정보 I ≤ A / (4 ℓ_P² ln 2) — entropy 의 **물리적** ceiling; classical Bekenstein bound 의 quantum-gravity 정형화
- **Margolus-Levitin** (1998): max ops ≤ 2E / πℏ — 모든 양자 / 고전 계산의 throughput 절대 상한

### L∞ — measurement collapse / observer paradox

- Copenhagen 해석: 측정 시 wavefunction collapse — *non-unitary*, *irreversible*
- Many-Worlds (Everett 1957): 측정 = 관찰자 + 시스템의 entanglement, branch 분기
- QBism (Fuchs 2010): quantum state = subjective Bayesian belief of agent
- **anima 적용**: cert 가 "PASS" 라고 측정한 순간, 그 측정 자체가 system 의 일부 — **observer-independent truth** 주장 ✗ (Tarski undefinability 의 quantum 변형)
- **bound**: **measurement problem 는 미해결** — 어떤 해석도 실험적 차별 ✗ (현 시점)

---

## §3 진척 요약 (brutal)

| Layer | 진척 | 다음 step |
|---|:---:|---|
| L0 sha256 + Ed25519 | **100%** | maintain; rotate keys; SHA-512 truncated 옵션 |
| L1 SHA-3 dual-stamp | **0%** | `.meta2-cert` schema 에 `sha3_256` field 추가 prototype |
| L2 Kyber/Dilithium | **0%** | liboqs 통합 → cert root dual-sign (Ed25519 ‖ Dilithium3) |
| L3 QRNG | **0%** | ID Quantique unit 평가 (cost-prohibitive at current scale) |
| L4 BB84 QKD | **0%** | n/a (single-node deployment; QKD 무의미) |
| L5 (한계) | (벽) | — |
| L∞ | **╳** | (philosophical) |

---

## §4 brutal disclosure — anima 의 quantum-resistant 가정

1. **현재 anima 의 모든 cert / hash chain 은 SHA-256 single-point-of-failure** 위에 올라가 있음 — collision 발견 (현재까진 없음, 2¹²⁸ classical / 2⁸⁵ quantum) 시 전체 무결성 무너짐
2. **R2 endpoint** (`access_key_id=37a9dd5c…`) 는 Cloudflare-managed; underlying TLS 가 ECDHE 일 경우 *record-now-decrypt-later* 위협 (양자 시대에 과거 트래픽 retroactive decrypt) — 단, archive 자체는 hashed/encrypted 이므로 metadata leak 만
3. **L4 PQ-crypto 0%** (`alm_memory_*` doc §2) — Dilithium dual-sign migration 은 NIST PQC 표준 확정 (2024-08) 후 ~2 년 지나도 anima 에 미적용
4. **QRNG 부재** → cert nonce / key 는 모두 `os.urandom` (CSPRNG) — kernel entropy 약한 환경에서 bias 가능성 (low risk on Hetzner bare-metal, higher on H100 ephemeral pods)
5. **no-cloning 무관** — anima 는 classical bit-for-bit copy 만 사용; quantum memory 미도입
6. **Tarski / Rice / 양자 측정** 모두 **외부 truth** 주장 ✗ — cert 는 *내부 일관성* 만 의미 (`alm_verification_cert_chain_*` §6 와 일치)

---

## §5 cross-ref + raw#10 evidence

- 현재 sha256 사용처:
  - `state/asset_archive_log.jsonl` — line 187 `r6_cp1_p1_evidence_20260425.tar.zst` sha256 = `a8a4a6aa61bf05c0b943c0701e36c7a45f8f11d9ab216ae98c1eb724ccc6266d`
  - `.meta2-cert/index.json` — entries chain `29f2dc2d…` ← `d0e005fb…`; trigger chain `1b3ea966…` (current head)
  - `~/.config/rclone/rclone.conf` — `secret_access_key` 32-byte (256-bit) HMAC-SHA256 input, quantum-tolerant if rotated
- **L4 PQ-crypto 0%** 은 `alm_memory_state_persistence_abstraction_20260425.md` §4 (commit `b0bcfb4d`) 와 일치 — 본 doc 은 그 사실을 quantum-domain 으로 확장
- **Cross-ref**:
  - `docs/alm_memory_state_persistence_abstraction_20260425.md` — L4 PQ 미구현 1차 disclosure
  - `docs/alm_verification_cert_chain_abstraction_20260425.md` — sha256 chain 의 syntactic / Tarski 한계
  - `docs/anima_math_foundations_abstraction_layers_20260425.md` — 정보-이론적 lower bound

---

> **Honest disclosure** — anima 의 cryptographic foundation 은 *quantum-tolerant hash (SHA-256, Grover-only)* + *quantum-vulnerable signature (Ed25519, Shor-broken)* 의 비대칭 위에 서있다. PQ-migration (L1 SHA-3 dual + L2 Dilithium dual-sign) 은 **technical debt** 로 인지되어 있으나 현 시점 (2026-04-25) 0% 구현. QRNG / QKD 는 cost 와 deployment topology 측면에서 의미 ≈ 0. **L5 (no-cloning, Bell, decoherence) + L∞ (measurement collapse)** 는 **물리/철학적 ceiling** — 어떤 cert 도 quantum-measurement-independent truth 를 주장 ✗.
> **Disclosure (EN)** — anima rests on a *quantum-tolerant hash* + *quantum-vulnerable signature* asymmetry. PQ migration is acknowledged debt at 0% (2026-04-25). QRNG / QKD remain economically and topologically irrelevant at single-node scale. The L5 (no-cloning, Bell, decoherence) and L∞ (measurement collapse) ceilings are physical / interpretive — no certificate can claim observer-independent truth. — raw#10 / raw#12 / own#11 준수.

— end —
