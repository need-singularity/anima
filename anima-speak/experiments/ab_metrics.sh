#!/bin/bash
# Objective A/B metrics — sox stats + duration + spectral stats per persona
set -u
BASE=/home/aiden/mac_home/dev/anima/anima-speak/corpus
OUT=$BASE/ab_test/metrics_${1:-20260419}.tsv
echo -e "persona\tidx\tengine\tsr\tdur_s\trms_dB\tpk_dB\tvol_adj\tfreq_band_p90" > "$OUT"
analyze() {
  local wav=$1 engine=$2 persona=$3 idx=$4
  local sr=$(soxi -r "$wav" 2>/dev/null || echo 0)
  local dur=$(soxi -D "$wav" 2>/dev/null || echo 0)
  local stats=$(sox "$wav" -n stats 2>&1)
  local rms=$(echo "$stats" | awk '/RMS lev dB/{print $4}')
  local pk=$(echo "$stats" | awk '/Pk lev dB/{print $4}')
  local vadj=$(echo "$stats" | awk '/Volume adjustment/{print $3}')
  # frequency analysis via sox stat (separate tool)
  local spec=$(sox "$wav" -n stat 2>&1 | grep 'Rough' | awk '{print $NF}')
  echo -e "${persona}\t${idx}\t${engine}\t${sr}\t${dur}\t${rms}\t${pk}\t${vadj}\t${spec}" >> "$OUT"
}
for id in 10 11 12 13 14 15 16 17 18 19; do
  pname=""
  case $id in
    10) pname="ice_queen" ;; 11) pname="chaebol_heir" ;; 12) pname="pure_heroine" ;;
    13) pname="tsundere_oppa" ;; 14) pname="airhead_friend" ;; 15) pname="charismatic_prez" ;;
    16) pname="thug_returnee" ;; 17) pname="cold_heiress" ;; 18) pname="gentle_oppa" ;;
    19) pname="fallen_antagonist" ;;
  esac
  for idx in 0 1 2 3 4 5 6 7; do
    pad=$(printf '%02d' $idx)
    old="$BASE/tts_say/persona_${id}_${pname}/tts_${pad}.wav"
    new="$BASE/ab_test/piper_ko_v1/persona_${id}_${pname}/tts_${pad}.wav"
    [ -f "$old" ] && analyze "$old" "say_yuna_16k" "$pname" "$idx"
    [ -f "$new" ] && analyze "$new" "piper_ko_22k" "$pname" "$idx"
  done
done
echo "done → $OUT"
wc -l "$OUT"
