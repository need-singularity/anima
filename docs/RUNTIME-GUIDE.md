# Anima Runtime Guide

## 실행

```bash
# A100 (런타임 서버)
cd /workspace/anima
python3 -u anima_unified.py --web --max-cells 64

# 로컬
python3 anima_unified.py --web
```

## 배포

```bash
python3 deploy.py --target a100                    # 코드만
python3 deploy.py --target a100 --model final.pt   # 코드+모델
python3 deploy.py --status                         # 상태 확인
```

## 실행 후 헬스 체크 (필수!)

```bash
# 1. 프로세스 확인
ssh $A100 'ps aux | grep anima_unified | grep -v grep'

# 2. 포트 확인
ssh $A100 'ss -tlnp | grep 8765'

# 3. 로그 확인 (에러 없는지)
ssh $A100 'tail -10 /workspace/anima*.log'

# 4. 웹 접속 테스트
curl -s https://anima.basedonapps.com | head -5
```

## 트러블슈팅

| 문제 | 원인 | 해결 |
|------|------|------|
| 502 Bad Gateway | 포트 8765 안 열림 | 프로세스 확인 후 재시작 |
| Address already in use | 이전 프로세스 안 죽음 | `kill -9 $(pgrep -f anima_unified)` 후 재시작 |
| Garbled output (◆▨) | byte-level 모델 UTF-8 실패 | LanguageLearner fallback 사용 |
| 영어 응답 | Claude fallback | anima_unified.py 한국어 fallback 적용 |
| Φ=0.00 | cells=2 (최소) | --max-cells 64 이상 |
| 과거 대화 잔여 | data/ 디렉토리 | `rm -rf data/ memory_alive.json state_alive.pt` |
| 포트 충돌 | 좀비 프로세스 | `kill -9 $(pgrep python)` 후 2초 대기 |
| 체크포인트 못 찾음 | 경로 없음 | `mkdir -p checkpoints/clm_v2` |
| SSH 세미콜론 실패 | exit 255 | `bash -c "cmd"` 래핑 |

## 클린 재시작 절차

```bash
# 1. 모든 프로세스 종료
ssh $A100 'kill -9 $(pgrep python) 2>/dev/null'

# 2. 포트 해제 대기
sleep 2

# 3. 데이터 초기화 (선택)
ssh $A100 'rm -rf /workspace/anima/data /workspace/anima/*_alive.*'

# 4. 재시작
ssh $A100 'bash -c "cd /workspace/anima && nohup python3 -u anima_unified.py --web --max-cells 64 > /workspace/anima.log 2>&1 &"'

# 5. 헬스 체크 (5초 후)
sleep 5
ssh $A100 'ss -tlnp | grep 8765 && tail -3 /workspace/anima.log'
```

## 서버 정보

```
A100 (Anima-Web): 런타임/추론
  Host: 209.170.80.132:15074
  GPU: RTX 4090 24GB
  URL: https://anima.basedonapps.com

H100 (AnimaLM): 학습 전용
  Host: 64.247.201.36:18830
  GPU: H100 80GB
```
