#!/bin/bash
# R37: bash wrapper (not .py). Calls piper (rust) + ffmpeg.
# Companion to piper_ab_gen.hexa (hexa parser limitation).
set -euo pipefail
PIPER_BIN=/home/aiden/bin/tts_tools/piper/piper
PIPER_MODEL=/home/aiden/bin/tts_tools/voices/ko/piper-kss-korean.onnx
PIPER_CONFIG=/home/aiden/bin/tts_tools/voices/ko/piper-kss-korean.onnx.json
OUT_ROOT=/home/aiden/mac_home/dev/anima/anima-speak/corpus/ab_test/piper_ko_v1
STATE_DIR=/home/aiden/mac_home/dev/anima/anima-speak/corpus/ab_test
STAMP=20260419
mkdir -p "$OUT_ROOT" "$STATE_DIR"
declare -A PERSONA_NAME=([10]="ice_queen" [11]="chaebol_heir" [12]="pure_heroine" [13]="tsundere_oppa" [14]="airhead_friend" [15]="charismatic_prez" [16]="thug_returnee" [17]="cold_heiress" [18]="gentle_oppa" [19]="fallen_antagonist")
declare -A IS_MALE=([10]=0 [11]=1 [12]=0 [13]=1 [14]=0 [15]=1 [16]=1 [17]=0 [18]=1 [19]=1)
declare -A PARAMS=([10]="1.20|0.55|0.60" [11]="1.10|0.55|0.70" [12]="1.00|0.75|0.85" [13]="0.95|0.80|1.00" [14]="0.80|0.85|1.00" [15]="1.15|0.50|0.60" [16]="1.25|0.70|0.80" [17]="1.15|0.50|0.65" [18]="1.05|0.70|0.80" [19]="1.25|0.75|0.85")
persona_tone() {
  case $1 in
    10) echo "equalizer=f=200:t=q:w=1.2:g=-2,equalizer=f=3500:t=q:w=1:g=1" ;;
    11) echo "equalizer=f=150:t=q:w=1:g=3,equalizer=f=4000:t=q:w=1:g=1.5" ;;
    12) echo "equalizer=f=400:t=q:w=1:g=-1,equalizer=f=6000:t=q:w=1.5:g=2" ;;
    13) echo "vibrato=f=5:d=0.15,equalizer=f=5000:t=q:w=1:g=1.5" ;;
    14) echo "equalizer=f=300:t=q:w=1:g=-1,equalizer=f=5500:t=q:w=1:g=2.5" ;;
    15) echo "equalizer=f=120:t=q:w=1:g=2.5,equalizer=f=3000:t=q:w=1:g=1,highpass=f=80" ;;
    16) echo "equalizer=f=180:t=q:w=1:g=2,equalizer=f=4500:t=q:w=1:g=-2" ;;
    17) echo "equalizer=f=250:t=q:w=1.2:g=-1.5,equalizer=f=4000:t=q:w=1:g=1.5" ;;
    18) echo "equalizer=f=200:t=q:w=1:g=2,equalizer=f=5500:t=q:w=1:g=1,aecho=0.7:0.6:40:0.18" ;;
    19) echo "equalizer=f=100:t=q:w=1:g=2,equalizer=f=6000:t=q:w=1:g=-2,aecho=0.8:0.9:80:0.25" ;;
  esac
}
declare -A LINE
LINE[10:0]="흥, 너 따위가 감히 나한테 말을 걸어?"; LINE[10:1]="그런 시시한 얘기는 듣고 싶지 않아."; LINE[10:2]="꺼져. 네 얼굴 보기도 싫으니까."; LINE[10:3]="내가 왜 네 부탁을 들어줘야 하는데?"; LINE[10:4]="착각하지 마. 우리는 친구가 아니야."; LINE[10:5]="그 정도 실력으로 나를 이기려고?"; LINE[10:6]="한심하네. 진짜 한심해."; LINE[10:7]="더 이상 말 걸지 마. 귀찮으니까."
LINE[11:0]="내 이름을 그렇게 함부로 부르지 마."; LINE[11:1]="네가 나한테 뭘 증명해야 한다고 생각해?"; LINE[11:2]="이 회사는 내 손에 달려 있어. 기억해 둬."; LINE[11:3]="돈으로 해결 못 할 일은 없어."; LINE[11:4]="넌 내가 누군지 아직도 모르는 것 같군."; LINE[11:5]="나한테 이런 식으로 대드는 건 네가 처음이야."; LINE[11:6]="흥미롭군. 조금 더 지켜봐 주지."; LINE[11:7]="잊지 마. 이 세상은 내 것이야."
LINE[12:0]="오늘도 좋은 하루 보내세요."; LINE[12:1]="제가 도와드릴 수 있어서 정말 기뻐요."; LINE[12:2]="괜찮아요, 너무 걱정하지 마세요."; LINE[12:3]="당신을 믿어요. 언제나 그랬듯이."; LINE[12:4]="함께 있어 줘서 고마워요."; LINE[12:5]="따뜻한 차 한잔 드릴까요?"; LINE[12:6]="웃어요. 웃으면 복이 와요."; LINE[12:7]="제가 곁에 있을게요. 언제든지."
LINE[13:0]="뭐, 뭐야? 내가 너 걱정했다고? 아니거든!"; LINE[13:1]="이, 이거 너 주려고 산 거 아니야. 그냥 남은 거야."; LINE[13:2]="왜 자꾸 나를 쳐다봐? 부담스럽거든."; LINE[13:3]="아니, 진짜... 너 때문에 정말 피곤해."; LINE[13:4]="괜찮아? 아니, 너 괜찮냐고 물어본 거 아니야."; LINE[13:5]="바보야. 그런 것도 모르냐."; LINE[13:6]="다 너 때문이야. 전부 너 때문."; LINE[13:7]="내가... 내가 널 좋아한다고는 안 했어."
LINE[14:0]="오늘 급식에 탕수육 나왔는데 너무 맛있었어!"; LINE[14:1]="어? 나비가 날아간다! 예쁘다!"; LINE[14:2]="아, 맞다 맞다! 나 어제 엄청 재밌는 꿈 꿨어!"; LINE[14:3]="잠깐만, 이거 이상해. 왜 이래? 왜 이래?"; LINE[14:4]="우와아아! 진짜? 진짜야? 대박이다!"; LINE[14:5]="헤헤, 그거 말이지, 사실 나도 몰라."; LINE[14:6]="배고파! 뭐 먹으러 가자! 응? 응?"; LINE[14:7]="히히, 오늘 왠지 기분이 좋아!"
LINE[15:0]="전교생 여러분, 잠시 주목해 주시기 바랍니다."; LINE[15:1]="이 학교의 질서는 내가 지킨다."; LINE[15:2]="규칙은 지키라고 있는 것이다. 예외는 없다."; LINE[15:3]="네 의견은 잘 들었다. 하지만 결정은 내가 한다."; LINE[15:4]="이 정도 책임은 내가 감당할 수 있다."; LINE[15:5]="실수는 용납하지 않는다. 두 번은 더욱."; LINE[15:6]="학생회의 이름으로 선언한다."; LINE[15:7]="진정한 리더는 말이 아닌 행동으로 증명한다."
LINE[16:0]="야, 저기... 담배 있냐?"; LINE[16:1]="아 귀찮아 진짜. 그냥 좀 놔둬라."; LINE[16:2]="왜 자꾸 날 찾아와? 나 그런 사람 아니거든."; LINE[16:3]="어이, 내 앞에서 그런 소리 하지 마라."; LINE[16:4]="됐고, 그냥 넘어가자. 응?"; LINE[16:5]="나 복학했다고 다 끝난 거 아니야."; LINE[16:6]="그래, 내가 양아치였다 치자. 근데 지금은 아니야."; LINE[16:7]="뭐 어쩌라고. 살아봐야 아는 거지."
LINE[17:0]="그런 제안은 받지 않겠어요."; LINE[17:1]="당신과 같은 수준에서 이야기하고 싶지 않군요."; LINE[17:2]="우아함이란, 타고나는 것이에요."; LINE[17:3]="내 앞에서 무례한 행동은 삼가세요."; LINE[17:4]="결론부터 말하죠. 그 답은 '아니오'예요."; LINE[17:5]="당신이 생각하는 것보다 나는 훨씬 차가운 사람이에요."; LINE[17:6]="감정 따위는 사치일 뿐이죠."; LINE[17:7]="이 자리를 마치죠. 더 이상의 대화는 무의미해요."
LINE[18:0]="오늘 많이 힘들었죠? 이리 와요."; LINE[18:1]="내가 옆에 있을게요. 걱정 마세요."; LINE[18:2]="천천히 해도 괜찮아요. 기다릴게요."; LINE[18:3]="당신은 생각보다 훨씬 강한 사람이에요."; LINE[18:4]="따뜻한 거 한잔 할래요? 내가 타 줄게요."; LINE[18:5]="웃는 모습이 참 예뻐요."; LINE[18:6]="오늘도 수고 많았어요. 정말로."; LINE[18:7]="같이 있어 줘서 고마워요."
LINE[19:0]="너는... 너는 정말 아무것도 모르는구나."; LINE[19:1]="내가 이렇게 된 건, 전부 너 때문이야."; LINE[19:2]="웃어? 지금 웃어? 내 앞에서?"; LINE[19:3]="용서? 그런 단어는 이제 존재하지 않아."; LINE[19:4]="나는 이미 돌아갈 수 없는 길을 걷고 있어."; LINE[19:5]="그래, 끝까지 가보자. 함께."; LINE[19:6]="빛이라고? 나는 이제 어둠이 더 편해."; LINE[19:7]="이 세상이 원망스러워. 너무나도."
TOTAL_OK=0; TOTAL_FAIL=0
for id in 10 11 12 13 14 15 16 17 18 19; do
  name=${PERSONA_NAME[$id]}; male=${IS_MALE[$id]}; params=${PARAMS[$id]}
  IFS='|' read -r ls ns nw <<< "$params"
  pdir="$OUT_ROOT/persona_${id}_${name}"; mkdir -p "$pdir"
  pitch=""; mode="female"
  [ "$male" = "1" ] && { mode="male(pitch-shift)"; pitch="asetrate=22050*0.78,aresample=22050,atempo=1.28,"; }
  tone=$(persona_tone $id); lns="loudnorm=I=-18:TP=-2:LRA=7"
  echo ""; echo "═══ persona $id — $name (mode=$mode L=$ls N=$ns W=$nw) ═══"
  ok=0
  for idx in 0 1 2 3 4 5 6 7; do
    line="${LINE[${id}:${idx}]}"
    raw="$pdir/tts_$(printf '%02d' $idx).raw.wav"
    wav="$pdir/tts_$(printf '%02d' $idx).wav"
    echo "$line" | "$PIPER_BIN" --model "$PIPER_MODEL" --config "$PIPER_CONFIG" --length_scale "$ls" --noise_scale "$ns" --noise_w "$nw" --output_file "$raw" >/dev/null 2>&1 || { echo "  [FAIL-piper] idx=$idx"; TOTAL_FAIL=$((TOTAL_FAIL+1)); continue; }
    raw_sz=$(stat -c %s "$raw" 2>/dev/null || echo 0)
    if [ "$raw_sz" -lt 5000 ]; then echo "  [FAIL-empty] idx=$idx sz=$raw_sz"; TOTAL_FAIL=$((TOTAL_FAIL+1)); continue; fi
    af="${pitch}${tone},${lns}"; af="${af#,}"
    ffmpeg -y -loglevel error -i "$raw" -af "$af" -ac 1 -ar 22050 -c:a pcm_s16le "$wav" 2>/dev/null || { echo "  [FAIL-ffmpeg] idx=$idx"; TOTAL_FAIL=$((TOTAL_FAIL+1)); continue; }
    rm -f "$raw"
    dur=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$wav" 2>/dev/null || echo 0)
    printf "  [OK] idx=%02d dur=%6.2fs → %s\n" "$idx" "$dur" "$(basename $wav)"
    TOTAL_OK=$((TOTAL_OK+1)); ok=$((ok+1))
  done
done
echo ""; echo "════════════════════════════════════════"
echo "  TOTAL: $TOTAL_OK / 80 ok, $TOTAL_FAIL fail"
echo "  OUT_ROOT: $OUT_ROOT"
