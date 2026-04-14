# data/ — 코퍼스 + 토크나이저 + seeds

R14: shared/ JSON 단일진실, 이 파일은 참조만.

ref:
  rules     shared/config/absolute_rules.json    R1~R21 + AN1~AN7
  corpus-reg  ../config/corpus_registry.json     코퍼스 메타 SSOT
  training-reg ../config/training_runs.json      런 → 데이터 바인딩
  r2        reference_r2_buckets.md              anima-memory bucket
  tokenizer tokenizer_64k_multilingual.model     64k SentencePiece

exec:
  HEXA=$HEXA_LANG/target/release/hexa
  $HEXA anima/modules/sync/cloud_sync.hexa --push data/
  $HEXA scripts/build_corpus_v11.hexa
  $HEXA scripts/merge_multilingual_corpus.hexa

tree:
  corpus.txt                    기본 코퍼스
  corpus_v11_multilingual.txt   v11 다국어 (한/영/중/일)
  corpus_multilingual/          분할 청크
  knowledge/knowledge.db        지식 흡수 파이프라인 SQLite
  tokenizer_64k_multilingual.*  SentencePiece 모델/보캡
  self_learning/                self-play 출력
  autonomous_learning/          루프 상태
  conscious-lm/                 CLM 학습 아티팩트
  conscious-lm_node-{0,1}/      노드 분산 출력
  conversation_log.jsonl        대화 로그
  evolution_state.json          진화 러너 상태
  {name}.json                   러너 상태 SSOT (ouroboros, roadmap, agi_progress)

rules:
  - 학습 데이터 SSOT, R2 백업 대상 (cloud_sync)
  - gitignored, 커밋 금지, 대용량 바이너리 금지
  - secrets/credentials/.env 절대 금지
  - 파일명에 버전 번호 금지, 과거는 git show {hash}
  - 데이터 변경 시 resume 금지 → step 0 재시작 (feedback_no_resume_data_change)
  - One-Shot Best: 최초부터 최선 조건으로만 투입
