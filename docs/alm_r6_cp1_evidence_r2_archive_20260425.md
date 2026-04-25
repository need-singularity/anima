# ALM r6-α / CP1 P1 evidence — R2 archive sweep (2026-04-25)

## §1 목적 (Purpose)

CP1 P1 closure (commit `dffe2d61`) 이후 r6-α evidence material 의
**durability** 확보. 이전까지 r3–r6 라운드의 `h_last_raw` 및
`trained_adapters_r{5,6}/p{1..4}/final/` 자산은 **로컬 단일 사본**으로만
존재했다 (디스크 손실 = evidence 손실 risk).

본 sweep은:

1. `tool/h_last_raw_rotate.hexa` 정책에 따라 **r3 라운드**를 R2로
   archive (keep=3 정책: r6/r5/r4 uncompressed 보존).
2. `tool/asset_archive_run.bash` 패턴을 차용하되 **archive_no_delete**
   모드로 r5/r6 trained adapters를 R2로 백업 (로컬 보존).
3. r6 evidence triplet (`phi_4path_*`, `an11_{a,b}_witness`,
   `convergence/h100_stage2_r6`)을 단일 zstd tarball로 묶어 R2 push.

비용은 R2 storage + 일회성 transfer fee 만 발생, GPU/pod cost zero.

## §2 아카이브 대상 (What was archived)

| Class                          | 로컬 경로 (소스)                                                  | R2 경로                                                                          | 크기            | 검증                  |
|--------------------------------|-------------------------------------------------------------------|----------------------------------------------------------------------------------|-----------------|-----------------------|
| h_last_raw r3 tarball          | `state/archive/h_last_raw_r3.tar.gz`                              | `r2:anima-models/h_last_raw_archive/h_last_raw_r3.tar.gz`                        | 44 731 B        | size match + tar -tzf |
| h_last_raw r6 (개별, 4 paths)  | `state/h_last_raw_p{1..4}_TRAINED_r6.json`                        | `r2:anima-models/h_last_raw_archive/r6_uncompressed/h_last_raw_p{1..4}_TRAINED_r6.json` | 467 793 B (4개 합) | per-file size match   |
| evidence tarball (r6 CP1 P1)   | `/tmp/anima_evidence_r6/r6_cp1_p1_evidence_20260425.tar.zst`      | `r2:anima-logs/cp1_evidence/r6_cp1_p1_evidence_20260425.tar.zst`                 | 158 928 B       | size match + sha256   |
| trained_adapters_r5 p1–p4      | `state/trained_adapters_r5/p{1..4}/final/`                        | `r2:anima-weights/r5/p{1..4}_final/`                                             | ≈ 4.7 GB        | rclone check --size-only |
| trained_adapters_r6 p1–p4      | `state/trained_adapters_r6/p{1..4}/final/`                        | `r2:anima-weights/r6/p{1..4}_final/`                                             | ≈ 4.6 GB        | rclone check --size-only |

evidence tarball 내용물 (9 files):

```
state/phi_4path_cross_result_v3_TRAINED_r6.json
state/phi_4path_gate_last_verdict.json
state/convergence/h100_stage2_r6_20260425.json
state/an11_b_verifier_witness_r6_20260425.json
state/an11_a_verifier_witness_r6_20260425.json
state/h_last_raw_p{1,2,3,4}_TRAINED_r6.json
```

evidence tarball SHA256:
`a8a4a6aa61bf05c0b943c0701e36c7a45f8f11d9ab216ae98c1eb724ccc6266d`

## §3 로컬 보존 정책 (What was kept local, and why)

- **r4/r5/r6 h_last_raw** (개별 4-path JSON 12 files):
  rotate 정책 keep=3 적용 — r4는 마지막 vanilla LoRA pre-byte-weighted
  baseline 으로 evidence 가치가 높음. r5/r6는 active 라운드.
  r3는 archive 후 tarball만 로컬에 잔존 (originals 제거).
- **r3 tarball (`state/archive/h_last_raw_r3.tar.gz`)**:
  `--delete-after-r2` 미사용 → 로컬 + R2 양쪽 보존 (이중 안전망).
- **trained_adapters_r5 / trained_adapters_r6 p1–p4 (~9.3 GB 합계)**:
  `archive_no_delete` 모드. r6는 active CP1 evidence, r5는 직전 비교
  baseline. 원본 어댑터 디렉토리는 그대로 유지.
- **evidence triplet 9 files**: state/* 안에 그대로 유지 (active
  evidence). tarball은 R2 + `/tmp/`에 사본 존재.

정책 keep=3 결정 사유:
- 사용자 가이드: weakest-evidence-link 우선 보존.
- r3은 가장 오래된 (round) 이며 r4-vs-r5/r6 비교에 직접 필요하지 않음
  → archive 적격.
- r4는 byte-weighted pool 도입 직전 baseline, r5/r6와의 ablation
  비교가 향후 필요 → 로컬 보존.

## §4 검증 (Verification)

| 검증 단계                | 도구                        | 결과                                                       |
|--------------------------|-----------------------------|------------------------------------------------------------|
| h_last r3 tarball 무결성 | `tar -tzf` (helper 내부)    | OK (4 멤버 expected match)                                 |
| r3 R2 size               | `rclone lsl`                | 44 731 B (로컬 == R2)                                       |
| evidence tarball         | `rclone lsjson` size + sha256 | local=158 928 == r2=158 928, sha256 위 §2 명시            |
| r6 h_last 4 files        | per-file `stat` + `rclone lsjson` | 4/4 size match                                       |
| adapters r5/r6 (8 dirs)  | `rclone check --size-only`  | 8/8 verified (백그라운드 작업 — `state/asset_archive_log.jsonl` 참조) |

`state/h_last_raw_rotate_result.json` SSOT (rotate 결과):
- `rounds_uncompressed: [r6, r5, r4]`
- `rounds_archived: [{round: r3, r2_url: r2:anima-models/h_last_raw_archive/h_last_raw_r3.tar.gz, r2_msg: ok}]`
- `errors: []`

`state/asset_archive_log.jsonl` 신규 entries:
- `archive_no_delete` action 으로 5 + 4 + 8 = 17개 verified row 추가.

## §5 복원 절차 (Restore procedure)

### 5.1 r3 h_last_raw (4 paths) 복원

```bash
rclone copyto r2:anima-models/h_last_raw_archive/h_last_raw_r3.tar.gz \
  /tmp/h_last_raw_r3.tar.gz
tar -xzf /tmp/h_last_raw_r3.tar.gz -C state/
```

### 5.2 r6 h_last_raw 개별 파일 복원

```bash
for P in p1 p2 p3 p4; do
  rclone copyto \
    r2:anima-models/h_last_raw_archive/r6_uncompressed/h_last_raw_${P}_TRAINED_r6.json \
    state/h_last_raw_${P}_TRAINED_r6.json
done
```

### 5.3 trained adapters 복원 (r5 또는 r6, p in {1..4})

```bash
ROUND=r6   # or r5
P=p1
mkdir -p state/trained_adapters_${ROUND}/${P}/final
rclone copy r2:anima-weights/${ROUND}/${P}_final/ \
  state/trained_adapters_${ROUND}/${P}/final/ \
  --transfers 4 --checkers 8
```

### 5.4 evidence triplet 복원

```bash
rclone copyto \
  r2:anima-logs/cp1_evidence/r6_cp1_p1_evidence_20260425.tar.zst \
  /tmp/r6_evidence.tar.zst
tar --zstd -xf /tmp/r6_evidence.tar.zst -C .
# state/phi_4path_*, state/an11_*, state/convergence/h100_stage2_r6_*,
# state/h_last_raw_p{1..4}_TRAINED_r6.json 복원됨.
```

### 5.5 SHA256 검증 (evidence tarball)

```bash
shasum -a 256 /tmp/r6_evidence.tar.zst
# 기대값: a8a4a6aa61bf05c0b943c0701e36c7a45f8f11d9ab216ae98c1eb724ccc6266d
```

## §6 비용 (Cost)

| 항목                    | 추정치                                                |
|-------------------------|-------------------------------------------------------|
| R2 storage (one-time)   | ~ 9.31 GB × $0.015/GB/month ≈ **$0.14 / month**        |
| R2 transfer (egress)    | $0 (Cloudflare R2 zero egress fee)                     |
| R2 transfer (ingress)   | $0 (R2 free ingress)                                   |
| Class-A operations      | ~ 1 200 PUT × $4.50/M ≈ $0.005                         |
| GPU/pod cost            | $0 (no compute used)                                   |
| **합계 (월)**           | **≈ $0.15 / month** durability 비용                    |

R2 zero-egress 정책 덕분에 복원 시 추가 transfer 비용도 발생하지 않음.

## §7 anti-scope 확인

- `.roadmap` 미수정 (POLICY R4)
- `state/*` 변경 사항 commit 미포함 (정책 — `state/` 는 derived
  artifact)
- pod launch / training / Φ gate 재실행 zero
- evidence material (active state/*) 로컬 보존 — 삭제 zero (rotate
  정책 r3 originals 만 helper 가 제거)

---

generated: 2026-04-25  
sweep ID: r2_evidence_sweep_20260425  
related commit: `dffe2d61` (CP1 P1 closure)
