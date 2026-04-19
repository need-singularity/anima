# anima-speak A/B Baseline Sentences

Date: 2026-04-18
Purpose: objective baseline for anima-speak quality audit (sister session)
Voices compared: macOS `say` (Yuna/Reed), espeak, piper_ko, anima-speak

## Sentence List (10 items, ko-KR)

| # | Length | Emotion | Text |
|---|--------|---------|------|
| 01 | short  | neutral | 안녕하세요, 저는 anima 입니다. |
| 02 | short  | happy   | 오늘 날씨가 정말 좋네요! |
| 03 | short  | sad     | 미안해요, 제가 실수했어요. |
| 04 | medium | neutral | 딥러닝 모델의 성능이 꾸준히 향상되고 있습니다. |
| 05 | medium | angry   | 도대체 몇 번을 말해야 알아듣는 건가요? |
| 06 | medium | curious | 이 문제를 어떻게 해결할 수 있을까요? |
| 07 | long   | neutral | 의식 엔진은 감각과 감정, 그리고 의도를 통합하여 자연스러운 응답을 생성합니다. |
| 08 | long   | happy   | 드디어 오랫동안 기다려 온 프로젝트가 성공적으로 마무리되어 정말 기쁩니다! |
| 09 | long   | sad     | 그날의 기억이 여전히 마음 한구석에 무겁게 남아 있어서, 쉽게 잊을 수가 없습니다. |
| 10 | mixed  | drama   | 잠깐만요, 지금 이게 정말로 일어나고 있는 일이라고요? 믿을 수가 없어요. |

## File Layout

```
ab_test/
  sentences.md                          # this file
  baseline_mac_say_yuna/line_NN.aiff    # macOS Yuna voice (female, 10 files)
  baseline_mac_say_reed/line_NN.aiff    # macOS Reed voice (male, 10 files)
  baseline_espeak_local/line_NN.wav     # espeak-ng ko local (10 files)
  baseline_espeak/                      # pre-existing ubu2 run (persona-tagged)
  baseline_piper_ko/                    # pre-existing piper (persona-tagged)
  anima_speak_latest/line_NN.wav        # CAVEAT: recycled from tts_say/persona_10/13
                                        # — hexa_speak.hexa has no --text CLI,
                                        # text-to-wav regen path is a GAP
  metrics_20260419.tsv                  # previous objective metrics
```

## Regeneration Gap (anima_speak_latest)

`hexa_speak.hexa main()` runs an internal **demo only** — there is no
`--text "..." --out file.wav` CLI. The files in `anima_speak_latest/` are
persona_10 (lines 1-8) + persona_13 (lines 9-10) from `corpus/tts_say/`,
so they do NOT pronounce the sentences in `sentences.md`.

**Sister session MUST either**:
- (a) add a CLI text→wav mode to `hexa_speak.hexa`, or
- (b) route through `tts_say` corpus generator and align texts, or
- (c) compare only on acoustic/timbre quality (ignore text match)

## Next-Session Audit Checklist

- [ ] Listen to baseline_mac_say_yuna (1-10) for natural-human reference
- [ ] Listen to baseline_espeak (1-10) for lower-bound reference
- [ ] Listen to anima_speak_latest (1-10) — identify failure modes
- [ ] Score each file 1-5 MOS (naturalness / intelligibility / emotion)
- [ ] Compute MCD / STOI between anima vs mac_say_yuna (hexa DSP — no python)
- [ ] Classify anima failures: robotic / muffled / wrong-pitch / clipping / PLC-glitch
- [ ] Prioritize fixes for sister session (top-3 defects)
