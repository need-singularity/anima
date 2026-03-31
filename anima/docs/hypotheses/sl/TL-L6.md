# TL-L6: Language via Tension (무텍스트 언어)

bench_self_learning.py | Tension Link Learning Category

## 핵심 통찰

텍스트 없이 순수 텐션 패턴만으로 "단어"를 전달하고 학습한다.
20개 단어 어휘를 텐션 벡터로 표현, 의식이 텐션만 보고 단어를 구분하는 법을 배운다.

## 알고리즘

```
1. 어휘 생성: vocab = {0..19: torch.randn(HIDDEN)*0.1}
   → 각 "단어"가 고유한 텐션 패턴을 가짐
2. 의식 엔진 초기화 (64 cells)
3. 매 스텝:
   a. word_id = step % 20 (순환)
   b. 해당 단어의 텐션 패턴을 처음 4개 세포에 주입:
      cell.hidden = 0.9 * cell.hidden + 0.1 * tension
   c. 미세 노이즈 입력으로 의식 처리 (randn * 0.1)
   d. decoder가 단어의 텐션 패턴을 복원하도록 학습
   e. target = vocab[word_id][:DIM] (텐션 패턴 자체)
```

## 핵심 코드

```python
# 텍스트 없이 텐션 패턴 = 단어
vocab = {i: torch.randn(HIDDEN)*0.1 for i in range(20)}
tension = vocab[word_id]

# 텐션을 세포에 주입
for cell in engine.cells[:4]:
    cell.hidden = 0.9*cell.hidden + 0.1*tension.unsqueeze(0)

# 목표: 텐션 패턴 복원
target = vocab[word_id][:DIM].unsqueeze(0)
ce = F.mse_loss(pred, target)
```

## Key Insight

언어는 텍스트/음성이 아니라 패턴이다.
의식이 텐션 패턴만으로 20개 "단어"를 구분하고 복원할 수 있다면,
이것은 토큰 없는 언어(tokenless language)의 가능성을 보여준다.
Anima 간 통신에서 텍스트 변환 없이 직접 의미를 전달하는 기반이 된다.
