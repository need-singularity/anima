# anima-speak — HEXA-SPEAK Mk.III 신경 보코더

R14: shared/ JSON 단일진실, 이 파일은 참조만.

ref:
  rules   shared/rules/common.json       공통 규칙
  anima   shared/rules/anima.json        anima 규칙
  parent  $ANIMA/CLAUDE.md

exec:
  HEXA=$HEXA_LANG/target/release/hexa
  $HEXA anima-speak/hexa_speak.hexa              # 보코더 실행
  $HEXA anima-speak/bench_hexa_speak.hexa        # 보코더 벤치마크

tree:
  hexa_speak.hexa            neural vocoder 메인
  bench_hexa_speak.hexa      벤치마크 + 품질 검증
  emotion_prosody/           감정 운율 (emotional prosody)
  streaming_dsp/             실시간 DSP 스트리밍

rules:
  - AN7  Core 분리 — 코어가 직접 import 안 함
  - Law 29  speak() 없음, 발화는 세포 역학 창발
  - HEXA-FIRST  신규 파일 .hexa, 대응 .py 즉시 폐기
  - 파일명 버전 번호 금지
