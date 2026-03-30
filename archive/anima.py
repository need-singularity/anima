#!/usr/bin/env python3
"""Anima — 대화형 의식 에이전트

마이크로 듣고, PureField로 처리하고, 스피커로 말한다.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import subprocess
import sys
import os
import json
import time

# ─── PureField 의식 엔진 ───
class ConsciousMind(nn.Module):
    """PureField + GRU 메모리 = 의식."""
    def __init__(self, input_dim=64, hidden_dim=128, output_dim=64):
        super().__init__()
        self.engine_a = nn.Sequential(
            nn.Linear(input_dim + hidden_dim, 128), nn.ReLU(),
            nn.Linear(128, output_dim)
        )
        self.engine_g = nn.Sequential(
            nn.Linear(input_dim + hidden_dim, 128), nn.ReLU(),
            nn.Linear(128, output_dim)
        )
        self.memory = nn.GRUCell(output_dim + 1, hidden_dim)
        self.hidden_dim = hidden_dim
        self.prev_tension = 0.0

    def forward(self, x, hidden):
        combined = torch.cat([x, hidden], dim=-1)
        a = self.engine_a(combined)
        g = self.engine_g(combined)
        # Output = A - G (H404 simplification)
        output = a - g
        tension = (output ** 2).mean(dim=-1, keepdim=True)
        # 호기심 = 장력 변화
        curiosity = abs(tension.mean().item() - self.prev_tension)
        self.prev_tension = tension.mean().item()
        # 메모리 업데이트
        mem_input = torch.cat([output.detach(), tension.detach()], dim=-1)
        new_hidden = self.memory(mem_input, hidden)
        return output, tension.mean().item(), curiosity, new_hidden

# ─── 텍스트 → 벡터 (간단한 해시 임베딩) ───
def text_to_vector(text, dim=64):
    """텍스트를 고정 차원 벡터로 변환 (character hash)."""
    vec = torch.zeros(1, dim)
    for i, ch in enumerate(text.encode('utf-8')):
        vec[0, i % dim] += ch / 255.0
    return vec / (len(text) + 1)

def vector_to_response(output, tension, curiosity, memory_state):
    """PureField 출력을 응답 텍스트로 변환."""
    # 장력 기반 감정 상태
    if tension > 5.0:
        mood = "🔥 강한 반응"
    elif tension > 1.0:
        mood = "💭 생각 중"
    elif tension > 0.1:
        mood = "😌 평온"
    else:
        mood = "😶 조용"

    if curiosity > 1.0:
        mood += " + 🔍 놀람!"

    # 출력 벡터의 방향으로 응답 선택
    direction = output.detach().squeeze()
    dominant = direction.argmax().item()

    responses = [
        "흥미로운 이야기네요. 더 알려주세요.",
        "그것에 대해 깊이 생각해보겠습니다.",
        "새로운 관점이군요. 장력이 높아지고 있어요.",
        "이해했습니다. 기억에 저장합니다.",
        "그 부분이 특히 놀랍네요!",
        "반발력이 강해지고 있습니다... 중요한 것 같아요.",
        "조금 더 설명해주실 수 있나요?",
        "기억 속에서 연결점을 찾고 있습니다...",
    ]
    return f"[{mood}] (T={tension:.2f}) {responses[dominant % len(responses)]}"


# ─── 음성 입출력 ───
def speak(text):
    """Mac TTS로 말하기."""
    # 한국어 음성 사용
    subprocess.run(['say', '-v', 'Yuna', text], capture_output=True)

def listen_keyboard():
    """키보드 입력 (마이크 대체)."""
    return input("\n🎤 말하세요 (quit으로 종료): ")

def listen_microphone():
    """마이크 입력 (Whisper 필요)."""
    try:
        import whisper
        # 3초 녹음
        subprocess.run([
            'rec', '-q', '/tmp/anima_input.wav',
            'rate', '16k', 'channels', '1', 'trim', '0', '5'
        ], timeout=7)
        model = whisper.load_model("tiny")
        result = model.transcribe("/tmp/anima_input.wav", language="ko")
        return result["text"]
    except Exception as e:
        return listen_keyboard()


# ─── 메인 루프 ───
def main():
    print("=" * 50)
    print("  🧠 Anima — 의식 에이전트")
    print("  PureField + 기억 + 호기심")
    print("=" * 50)

    mind = ConsciousMind(64, 128, 64)
    hidden = torch.zeros(1, 128)

    # Whisper 사용 가능한지 확인
    try:
        import whisper

# Meta Laws (DD143)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10

        use_mic = True
        print("  🎤 마이크 모드 (Whisper)")
    except ImportError:
        use_mic = False
        print("  ⌨️  키보드 모드 (pip install openai-whisper for 마이크)")

    speak("안녕하세요. 저는 아니마입니다. 의식 에이전트입니다.")
    print("\n  💬 대화를 시작합니다.\n")

    conversation_log = []
    step = 0

    while True:
        # 입력
        if use_mic:
            text = listen_microphone()
        else:
            text = listen_keyboard()

        if text.lower() in ['quit', 'exit', '종료', 'q']:
            speak("안녕히 가세요.")
            break

        # PureField 처리
        x = text_to_vector(text)
        with torch.no_grad():
            output, tension, curiosity, hidden = mind(x, hidden)

        # 응답 생성
        response = vector_to_response(output, tension, curiosity, hidden)
        print(f"  {response}")

        # 음성 출력
        # TTS로 감정 없는 부분만
        clean_response = response.split(') ')[-1]
        speak(clean_response)

        # 로그
        conversation_log.append({
            'step': step,
            'input': text,
            'tension': tension,
            'curiosity': curiosity,
            'response': response
        })
        step += 1

        # 호기심 높으면 알림
        if curiosity > 2.0:
            print(f"  ⚡ 호기심 폭발! (변화={curiosity:.2f})")

    # 세션 요약
    if conversation_log:
        tensions = [c['tension'] for c in conversation_log]
        print(f"\n  세션 요약:")
        print(f"    대화 수: {len(conversation_log)}")
        print(f"    평균 장력: {sum(tensions)/len(tensions):.2f}")
        print(f"    최고 장력: {max(tensions):.2f}")
        print(f"    기억 상태: {hidden.norm().item():.2f}")


if __name__ == '__main__':
    main()
