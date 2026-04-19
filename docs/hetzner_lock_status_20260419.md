# hetzner stage0 lock audit — 2026-04-19

## Observation only (lock 변경 금지)

### Lock holder
- `/tmp/hexa_stage0.lock.d/` — **존재하지 않음** (`No such file or directory`)
- `/tmp/hexa_stage0.lock.d/pid` — **없음**
- `lsof | grep hexa.*lock` — **0건**
- `/var/lock`, `/var/run` 하에도 stage0 lock artifact 없음
- 유일한 stage0 artifact: `/tmp/hexa_stage0_linux.bin` (바이너리, lock 아님)

**결론: 현 시점 stage0 lock holder 없음. P3 drill은 lock 없이 순차 실행 중.**

### drill_v3 진행 (P3)
| 항목 | 값 |
|---|---|
| Bash PID | 498631 |
| Elapsed | 02:22 (relaunch 이후) |
| tmux session | `drill_v3` (PID 4169056) |
| 현재 iter | `iter_48_v3_training_mfu_corpus` ([run] 상태) |
| 완료 iter (이 relaunch) | 22건 ([done] 카운트) |
| 직전 완료 | iter_47_v3_training_alm_lora_ceiling (dur=117s, OK) |
| 평균 dur | 206.3s/iter |
| 시드 파일 | `/root/drill_v3/seeds.tsv` (44 lines) |
| 실행 트리 | bash → timeout → hexa → sh → hexa_stage0 → sh → exec_validated → hexa |
| 상태 | **정상 (22/22 OK, rc=0, replay=0)** |

### P4 발사 가능 시점 추정

**lock 기준으로는 즉시 가능** (lock 자체가 없음). 단, drill_v3는 stage0 바이너리를 단일 프로세스로 직렬 사용 중이므로 P4가 동일 stage0을 공유한다면 drill_v3 완료 대기가 안전.

잔여 iter 추정:
- 시드 파일 44줄, 현재 max iter 번호 48 → 시드 인덱스는 sparse (일부 skip). 실질 잔여는 `44 - 22 = 22 iter` 상한.
- 잔여 시간: `22 × 206s ≈ 4,540s ≈ 75분` 상한.
- 짧은 iter(101~117s)가 빈번하므로 실제는 **45~60분** 예상.

**P4 가능 시점**:
- **공격적 (lock-only)**: 즉시 (lock holder 없음)
- **안전 (drill_v3 완료 대기)**: 약 **45~75분 후** (2026-04-19 예상 완료 ~ +1h from 상태 수집 시각)

### 권고
- P4가 stage0 전용 자원 점유가 아니라면 **즉시 병렬 발사** 가능.
- stage0 이진 공유 필요 시 `tail -f /tmp/drill_v3_relaunch.log`로 iter_48 이후 종료 감지 후 발사.
