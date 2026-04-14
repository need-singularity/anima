# scripts/ — .hexa 인프라 스크립트

R14: shared/ JSON 단일진실, 이 파일은 참조만.

ref:
  rules     shared/config/absolute_rules.json    R1~R21 + AN1~AN7
  runpod    shared/config/runpod.json            SSH/포드 설정
  vastai    shared/config/vastai.json            multi-GPU
  hexa-py   feedback_hexa_replaces_py.md         hexa 완성 시 .py 즉시 폐기

exec:
  HEXA=$HEXA_LANG/target/release/hexa
  $HEXA scripts/h100_sync.hexa
  $HEXA scripts/backup_checkpoints.hexa
  $HEXA scripts/auto_restart.hexa
  $HEXA scripts/infinite_growth.hexa

tree:
  h100_{sync,retrieve,watchdog}.hexa  H100 포드 파이프라인
  backup_checkpoints.hexa     R2 백업
  auto_restart.hexa           OOM/crash 자동 재시작
  auto_retrieve_v3.hexa       체크포인트 회수
  infinite_growth.hexa        무한 성장 루프 러너
  build_corpus_v11.hexa       코퍼스 조립
  collect_multilingual*.hexa  다국어 수집
  expand_corpus.hexa          코퍼스 증강
  merge_*.hexa                코퍼스 병합
  compare_{tokenizers,training}.hexa  비교 유틸
  monitor_{experiments,and_test}.hexa  모니터링
  cleanup_old_runs.hexa       구 런 정리
  deploy/                     H100 디플로이 (구 .sh 아카이브)
  lib/growth_common.sh        공용 쉘 헬퍼 (deprecated)

rules:
  - 신규 스크립트는 .hexa 전용, .sh 는 archive 대상
  - .py 짝은 hexa 대체 완료 시 즉시 폐기 (동일 basename)
  - Long-running 은 run_in_background=true
  - 파일명에 버전 번호 금지, 과거는 git show {hash}
  - secrets/.env 금지, 설정은 shared/config/ 참조
  - Gradio 기반 런처 금지
