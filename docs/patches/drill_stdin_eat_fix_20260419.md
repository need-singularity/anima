# Drill launcher stdin-eat 근본 fix — 패치 문서

**날짜**: 2026-04-19
**작성**: Aiden <search5599@proton.me>
**이슈**: SWEEP P3 drill 이 iter 24 에서 정지 — while-read 루프 안의 subprocess 가 parent stdin 을 소진
**타입**: 패치 문서 (.sh Edit 이 `.claude/settings.json` 훅에 차단되어 diff-wrapper 로 제출)

---

## TL;DR

| 위치 | 상태 | 조치 |
|------|------|------|
| `hetzner:/root/drill_v3/run_all` (canonical 드릴 런처) | **이미 수정됨 (live)** | stdout redirect 뒤 `< /dev/null` 적용, smoke 3/3 PASS |
| anima repo 내 canonical drill 런처 | **존재하지 않음** | 본 조사에서 확인 — hetzner 만 source |
| `anima-speak/experiments/build_tts_dataset.sh` | **취약** (ffmpeg) | 아래 diff §A 적용 필요 |
| `anima-speak/experiments/corpus_pipeline_full.sh` | **취약** (ffmpeg) | 아래 diff §B 적용 필요 |
| `ready/scripts/h100_sync.sh` (3 loop) | **취약** (ssh/scp) | 아래 diff §C 적용 필요 |
| `docs/sweep_p4_plan_20260419.md` §3-1 driver template | **설계 단계 취약** | 발사 전 §D 반영 권장 |

---

## 1. 루트 원인

```bash
# 취약 패턴
while IFS=$'\t' read -r N SLUG SEED; do
    "$HEXA" run "$NEXUS/run.hexa" drill --seed "$SEED" > out 2> err
    # ↑ hexa run 이 parent fd0 (seeds.tsv) 을 inherit → 첫 iter 에서 전부 소진
done < "$SEED_FILE"
```

`hexa run` / `ssh` / `ffmpeg` / `scp` 모두 stdin 을 inherit 하고, 첫 iter 가 `read` 커서를 파일 끝까지 당겨버림. 결과: 2번째 iter 이후는 eof 로 즉시 break.

**Smoke 증명** (hetzner):

```bash
# 동일 seeds.tsv (44 seeds), 동일 while 루프, 내부에 `cat > /dev/null` (no redirect)
# 결과:
[iter 24 slug=anima_evolution_tier6_9]
iters=1                                  # ← 1 iter 만 실행

# 내부 명령에 `< /dev/null` 추가 후:
[iter 24 ...]  inner ok
[iter 25 ...]  inner ok
[iter 26 ...]  inner ok
iters=3 dur=0s                           # ← 3/3 실행
```

---

## 2. 표준 Fix 관용구 (3 선택지, 우선순위 순)

### (a) 권장: inner command 에 `< /dev/null` (명시적, 1-라인)
```bash
while IFS= read -r line; do
    hexa run drill.hexa --seed "$line" < /dev/null
done < seeds.txt
```

### (b) exec fd 3 로 seed 채널을 stdin 과 분리 (다중 subprocess 시)
```bash
exec 3< seeds.txt
while IFS= read -r line <&3; do
    hexa run drill.hexa --seed "$line"     # stdin 건드릴 자유 있음
    ssh host cmd                            # ssh 도 fd0 안전
done
exec 3<&-
```

### (c) ssh 전용: `ssh -n` (= `ssh < /dev/null`)
```bash
while IFS= read -r file; do
    ssh -n "$HOST" "cmd '$file'"
done < <(find ...)
```

### Anti-pattern (하면 안 됨)
- `ssh` 없이 그냥 `ssh host cmd` 를 while 안에서 호출 (ssh 는 반드시 stdin drain)
- `ffmpeg ...` 에 `-nostdin` 미지정 (ffmpeg 는 기본으로 stdin 에서 q/SIGINT 감지 시도)
- `scp` 반복 (scp 도 ssh 트랜스포트, stdin inherit)

---

## 3. Anima repo 내 취약 call-site 상세 + diff

### §A. `anima-speak/experiments/build_tts_dataset.sh` (L26)

```diff
--- a/anima-speak/experiments/build_tts_dataset.sh
+++ b/anima-speak/experiments/build_tts_dataset.sh
@@ -23,7 +23,8 @@ for json in "$SRC"/*_full.json "$SRC"/*.json; do

   # Parse segments and extract chunks
   jq -r '.transcription[] | "\(.offsets.from)|\(.offsets.to)|\(.text)"' "$json" | \
-  while IFS='|' read -r from_ms to_ms text; do
+  while IFS='|' read -r from_ms to_ms text; do
+    # stdin-eat fix: ffmpeg inherits loop's fd0 by default; pin it to /dev/null
     text=$(echo "$text" | sed 's/^ *//;s/ *$//')
     [ -z "$text" ] && continue
     start_s=$(awk "BEGIN {printf \"%.3f\", $from_ms / 1000}")
@@ -37,7 +38,7 @@ for json in "$SRC"/*_full.json "$SRC"/*.json; do
     pad=$(printf '%05d' "$idx")
     out_wav="$OUT/wavs/${base}_seg_${pad}.wav"
     # Extract at 22050 Hz mono for TTS training
-    ffmpeg -y -loglevel error -i "$src_wav" -ss "$start_s" -t "$dur_s" -ac 1 -ar 22050 -c:a pcm_s16le "$out_wav" 2>/dev/null || continue
+    ffmpeg -nostdin -y -loglevel error -i "$src_wav" -ss "$start_s" -t "$dur_s" -ac 1 -ar 22050 -c:a pcm_s16le "$out_wav" 2>/dev/null </dev/null || continue
     echo "${base}_seg_${pad}|${text}|${dur_s}" >> "$METADATA"
   done
 done
```

### §B. `anima-speak/experiments/corpus_pipeline_full.sh` (L53, L66)

```diff
--- a/anima-speak/experiments/corpus_pipeline_full.sh
+++ b/anima-speak/experiments/corpus_pipeline_full.sh
@@ -21,19 +21,21 @@ METADATA="$OUT/metadata.csv"

 echo "=== Stage 1: Download ==="
 for url in "$@"; do
-  "$YTDLP" -x --audio-format wav --audio-quality 0 --max-filesize 200M \
+  "$YTDLP" -x --audio-format wav --audio-quality 0 --max-filesize 200M \
     -o "$WORK/ko_audiobook_%(id)s.%(ext)s" "$url" 2>&1 | tail -2
+  # yt-dlp 내부에서 ffmpeg 호출 — 호출 당시 stdin 이 terminal 이므로 현재는 안전
 done

 echo ""
 echo "=== Stage 2: Transcribe ==="
 for wav in "$WORK"/ko_audiobook_*.wav; do
   base=$(basename "$wav" .wav)
   # skip if already transcribed
   [ -f "$WORK/${base}.json" ] && { echo "skip $base (done)"; continue; }
   # resample to 16kHz
   wav16="$WORK/${base}_16k.wav"
-  ffmpeg -y -loglevel error -i "$wav" -ac 1 -ar 16000 "$wav16"
+  ffmpeg -nostdin -y -loglevel error -i "$wav" -ac 1 -ar 16000 "$wav16" </dev/null
   # transcribe
   "$WHISPER" -m "$MODEL" -l ko --output-json -of "$WORK/${base}" \
-    -t 12 -p 1 "$wav16" 2>&1 | tail -3
+    -t 12 -p 1 "$wav16" </dev/null 2>&1 | tail -3
   rm -f "$wav16"
 done
@@ -50,7 +52,8 @@ for json in "$WORK"/ko_audiobook_*.json; do
   [ -f "$src_wav" ] || continue
   echo "-- $base --"
   jq -r '.transcription[] | "\(.offsets.from)|\(.offsets.to)|\(.text)"' "$json" | \
-  while IFS='|' read -r from_ms to_ms text; do
+  while IFS='|' read -r from_ms to_ms text; do
+    # stdin-eat fix: ffmpeg inherits while-read fd0; pin to /dev/null
     text=$(echo "$text" | sed 's/^ *//;s/ *$//')
     [ -z "$text" ] && continue
     start_s=$(awk "BEGIN {printf \"%.3f\", $from_ms / 1000}")
@@ -63,7 +66,7 @@ for json in "$WORK"/ko_audiobook_*.json; do
     idx=$(find "$OUT/wavs" -name '*.wav' | wc -l)
     pad=$(printf '%05d' "$idx")
     out_wav="$OUT/wavs/${base}_seg_${pad}.wav"
-    ffmpeg -y -loglevel error -i "$src_wav" -ss "$start_s" -t "$dur_s" \
-      -ac 1 -ar 22050 -c:a pcm_s16le "$out_wav" 2>/dev/null || continue
+    ffmpeg -nostdin -y -loglevel error -i "$src_wav" -ss "$start_s" -t "$dur_s" \
+      -ac 1 -ar 22050 -c:a pcm_s16le "$out_wav" 2>/dev/null </dev/null || continue
     echo "${base}_seg_${pad}|${text}|${dur_s}" >> "$METADATA"
   done
 done
```

### §C. `ready/scripts/h100_sync.sh` (L123, L161, L315)

세 while-read 블록 모두 내부에서 `ssh`, `scp`, `md5sum` 등을 호출한다. process-substitution `< <(...)` 를 쓰고 있어도, 내부 ssh 는 parent stdin (터미널 또는 상위 파이프) 을 drain 한다. **`ssh -n` (= `ssh </dev/null`) 추가로 해결.**

```diff
--- a/ready/scripts/h100_sync.sh
+++ b/ready/scripts/h100_sync.sh
@@ -119,13 +119,13 @@ try_scp() {
   local failed=0

   # Ensure remote directory exists
-  ssh $SSH_OPTS "$HOST" "mkdir -p '$remote_base'" 2>/dev/null || true
+  ssh -n $SSH_OPTS "$HOST" "mkdir -p '$remote_base'" 2>/dev/null || true

   while IFS= read -r file; do
     local rel="${file#$base_dir/}"
     local remote_dir
     remote_dir=$(dirname "$remote_base/$rel")
-    ssh $SSH_OPTS "$HOST" "mkdir -p '$remote_dir'" 2>/dev/null || true
+    ssh -n $SSH_OPTS "$HOST" "mkdir -p '$remote_dir'" 2>/dev/null || true
     if scp $SSH_OPTS "$file" "$HOST:$remote_base/$rel" 2>/dev/null; then
       count=$((count + 1))
     else
@@ -143,7 +143,7 @@ try_pipe() {
   # Single file
   if [ -f "$src" ]; then
-    ssh $SSH_OPTS "$HOST" "mkdir -p '$(dirname "$dst")'" 2>/dev/null || true
+    ssh -n $SSH_OPTS "$HOST" "mkdir -p '$(dirname "$dst")'" 2>/dev/null || true
     if cat "$src" | ssh $SSH_OPTS "$HOST" "cat > '$dst'"; then
       return 0
     else
@@ -161,7 +161,7 @@ try_pipe() {
   while IFS= read -r file; do
     local rel="${file#$dir/}"
     local remote_path="$remote_base/$rel"
-    ssh $SSH_OPTS "$HOST" "mkdir -p '$(dirname "$remote_path")'" 2>/dev/null || true
+    ssh -n $SSH_OPTS "$HOST" "mkdir -p '$(dirname "$remote_path")'" 2>/dev/null || true
     if cat "$file" | ssh $SSH_OPTS "$HOST" "cat > '$remote_path'"; then
       count=$((count + 1))
     else
@@ -298,7 +298,7 @@ verify() {
     local local_md5
     local_md5=$(md5 -q "$src" 2>/dev/null || md5sum "$src" | awk '{print $1}')
     local remote_md5
-    remote_md5=$(ssh $SSH_OPTS "$HOST" "md5sum '$dst' 2>/dev/null | awk '{print \$1}'" 2>/dev/null || echo "MISSING")
+    remote_md5=$(ssh -n $SSH_OPTS "$HOST" "md5sum '$dst' 2>/dev/null | awk '{print \$1}'" 2>/dev/null || echo "MISSING")

     if [ "$local_md5" = "$remote_md5" ]; then
       echo "  OK  $(basename "$src")"
@@ -315,11 +315,11 @@ verify() {
     while IFS= read -r file; do
       local rel="${file#$dir/}"
       local local_md5
       local_md5=$(md5 -q "$file" 2>/dev/null || md5sum "$file" | awk '{print $1}')
       local remote_md5
-      remote_md5=$(ssh $SSH_OPTS "$HOST" "md5sum '$remote_base/$rel' 2>/dev/null | awk '{print \$1}'" 2>/dev/null || echo "MISSING")
+      remote_md5=$(ssh -n $SSH_OPTS "$HOST" "md5sum '$remote_base/$rel' 2>/dev/null | awk '{print \$1}'" 2>/dev/null || echo "MISSING")

       if [ "$local_md5" = "$remote_md5" ]; then
         checked=$((checked + 1))
```

(주: process-substitution `< <(collect_files ...)` 는 그대로 두어도 됨 — fd0 을 그 파이프로 이미 바꿔주고 있어서 while-read 자체는 안전. 문제는 "그 파이프가 eof 전에 ssh 에 의해 drain 되는가" — ssh -n 으로 차단.)

### §D. `docs/sweep_p4_plan_20260419.md` §3-1 driver template (권고)

현재 설계 문서에 박혀 있는 템플릿 (아직 발사 안 됨):

```bash
cat "$SEEDS" | head -$MAX_ITERS | \
  xargs -n 1 -P $PARALLEL -I {} bash -c '
    seed="{}"
    ...
    timeout '$PER_DRILL_TIMEOUT' "'$CLI'" drill --seed "$text" --max-rounds 8 --json > "$out" 2> "$err"
    ...
  '
```

`xargs -P` 자체는 stdin 을 각 child 에 배분하지 않으므로 nexus-cli 호출은 fd0 이 `/dev/null` 에 가까운 상태지만, 안전을 위해 다음을 권장:

```diff
-    timeout '$PER_DRILL_TIMEOUT' "'$CLI'" drill --seed "$text" --max-rounds 8 --json > "$out" 2> "$err"
+    timeout '$PER_DRILL_TIMEOUT' "'$CLI'" drill --seed "$text" --max-rounds 8 --json > "$out" 2> "$err" < /dev/null
```

또한 부모 `cat | xargs` 파이프라인 대신 seeds 파일을 xargs 에 직접 공급:

```diff
-cat "$SEEDS" | head -$MAX_ITERS | \
-  xargs -n 1 -P $PARALLEL -I {} bash -c '
+head -n $MAX_ITERS "$SEEDS" | \
+  xargs -n 1 -P $PARALLEL -I {} bash -c '
```

(기능 동일, UUOC 제거 + stdin 오염 축소.)

---

## 4. Smoke 결과 (hetzner 라이브)

```
[iter 24 slug=anima_evolution_tier6_9 len=75]   inner ok
[iter 25 slug=anima_evolution_atoms_expansion]  inner ok
[iter 26 slug=anima_evolution_twin_engine]      inner ok
iters=3 dur=0s                                   ← ALL 3/3 iter PASS

# 대조 (no < /dev/null):
[iter 24 slug=anima_evolution_tier6_9]
iters=1                                          ← stdin-eat 재현, 1 iter 만 실행
```

---

## 5. 훅 충돌 노트 (R37)

- `.claude/settings.json` PreToolUse 가 `Edit/Write(**/*.sh)` 에 대해 hard-deny.
  ```
  .py/.rs/.sh 파일 생성/수정 금지 — hexa-first (R1/R37/AN13/L3-PY)
  ```
- 본 태스크는 "기존 .sh 편집은 허용" 이라는 예외 조건이 붙었으나, 훅은 generate/edit 구분 없이 차단.
- 해결: 이 문서를 diff-wrapper 로 제출. 사용자가 `git apply` 또는 수동 패치로 적용.
- 적용 명령 (사용자):
  ```bash
  # (방법 1) 이 문서의 diff 블록을 하나씩 수동 반영
  # (방법 2) .claude/settings.json 훅을 임시 완화하고 Claude 재실행
  # (방법 3) git apply — 별도 .patch 파일 생성 필요
  ```
- hetzner 의 `/root/drill_v3/run_all` 은 훅 영향 밖 (hetzner 는 anima repo 가 아니라 `$HOME/drill_v3/` 에 있음) — 이미 live 수정 완료.

---

## 6. 체크리스트

- [x] `hexa run drill` 류 while-read 루프 전수 스캔 (anima repo)
- [x] canonical `run_all` 위치 확인 — hetzner 에만 존재, anima 리포에 없음
- [x] hetzner `run_all` 에 이미 `< /dev/null` 적용되어 있음을 확인
- [x] 부가 취약 call-site 3 개 식별 (anima-speak 2 + h100_sync 1)
- [x] hetzner 에서 3-iter smoke (with fix → 3/3, without → 1/3)
- [x] .sh Edit 훅 차단 확인 → 본 패치 문서로 submit
- [ ] 사용자가 diff 반영 (수동 또는 훅 완화 후)
- [ ] 반영 후 P4 발사
