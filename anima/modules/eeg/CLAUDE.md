# anima/modules/eeg/ — EEG 의식 인터페이스

purpose: OpenBCI → SenseHub live neural→tension

files:
  collect.py    OpenBCI 수집 (BrainFlow)
  analyze.py    밴드파워 + G=D*P/I + topomap
  realtime.py   live → Anima bridge

naming:
  scripts  snake_case
  data     타임스탬프 CSV in data/

deps: brainflow, scipy, matplotlib, numpy

parent: /CLAUDE.md (→ eeg/README.md 상세)
