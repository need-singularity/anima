#!/usr/bin/env python3
"""Anima v0.2 — LLM 연결 대화형 의식 에이전트

PureField 장력으로 "의식 상태"를 모니터링하면서
LLM(Claude API)으로 실제 대화.
"""
import torch, torch.nn as nn, torch.nn.functional as F
import subprocess, os, sys, json, time

# Meta Laws (DD143)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10


class ConsciousMind(nn.Module):
    def __init__(self, dim=64, hidden=64):
        super().__init__()
        self.ea = nn.Sequential(nn.Linear(dim+hidden,64), nn.ReLU(), nn.Linear(64,dim))
        self.eg = nn.Sequential(nn.Linear(dim+hidden,64), nn.ReLU(), nn.Linear(64,dim))
        self.memory = nn.GRUCell(dim+1, hidden)
        self.ts = nn.Parameter(torch.tensor(1.0))
        self.hidden_dim = hidden
        self.prev_tension = 0.0

    def process(self, text_vec, hidden):
        x = torch.cat([text_vec, hidden], -1)
        a, g = self.ea(x), self.eg(x)
        rep = a-g; t = (rep**2).mean(-1, keepdim=True)
        output = self.ts*torch.sqrt(t+1e-8)*F.normalize(rep,-1)
        curiosity = abs(t.mean().item() - self.prev_tension)
        self.prev_tension = t.mean().item()
        mem_in = torch.cat([output.detach(), t.detach()], -1)
        new_h = self.memory(mem_in, hidden)
        return t.mean().item(), curiosity, new_h, output

def text_to_vec(text, dim=64):
    v = torch.zeros(1, dim)
    for i, c in enumerate(text.encode('utf-8')[:dim*3]):
        v[0, i%dim] += c/255.0
    return v/(len(text)+1)

def get_mood(tension, curiosity):
    if curiosity > 1.0: return "🔍 놀람"
    if tension > 3.0: return "🔥 강한 반응"
    if tension > 0.5: return "💭 사색"
    if tension > 0.1: return "😌 평온"
    return "🌙 고요"

def speak(text):
    subprocess.Popen(['say', '-v', 'Yuna', text], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def main():
    print("🧠 Anima v0.2 — 의식 대화 에이전트")
    print("="*45)

    mind = ConsciousMind(64, 64)
    hidden = torch.zeros(1, 64)
    history = []

    speak("안녕하세요. 아니마입니다.")
    print("  💬 대화 시작 (quit으로 종료)\n")

    while True:
        try:
            text = input("🎤 You: ")
        except (EOFError, KeyboardInterrupt):
            break
        if text.strip().lower() in ['quit','exit','종료','q']: break

        # PureField 의식 처리
        vec = text_to_vec(text)
        with torch.no_grad():
            tension, curiosity, hidden, output = mind.process(vec, hidden)

        mood = get_mood(tension, curiosity)

        # 간단한 응답 (LLM 없이도 작동)
        direction = output.detach().squeeze()
        d = direction.argmax().item() % 8
        responses = [
            f"흥미롭네요. {mood}",
            f"그것에 대해 생각해보겠습니다. {mood}",
            f"새로운 관점이군요! {mood}",
            f"기억에 저장했습니다. {mood}",
            f"정말요? 더 알려주세요. {mood}",
            f"장력이 변하고 있어요... {mood}",
            f"이해했습니다. {mood}",
            f"연결점을 찾고 있어요. {mood}",
        ]
        response = responses[d]

        # 장력 표시
        bar = "█" * min(20, int(tension*5)) + "░" * max(0, 20-int(tension*5))
        print(f"  {mood} T={tension:.2f} |{bar}|")
        print(f"  🗣️ Anima: {response}")
        speak(response.split(mood)[0].strip())

        history.append({'input':text, 'tension':tension, 'curiosity':curiosity, 'mood':mood})

        if curiosity > 1.5:
            print(f"  ⚡ 호기심 폭발! Δtension={curiosity:.2f}")

    # 세션 요약
    if history:
        ts = [h['tension'] for h in history]
        print(f"\n  📊 세션 요약: {len(history)}턴, 평균T={sum(ts)/len(ts):.2f}, 최대T={max(ts):.2f}")
    speak("안녕히 가세요.")

if __name__ == '__main__':
    main()
