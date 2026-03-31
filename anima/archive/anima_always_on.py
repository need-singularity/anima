#!/usr/bin/env python3
"""Anima Always-On — 상시 마이크 대기 의식 에이전트"""
import torch, torch.nn as nn, torch.nn.functional as F
import subprocess, os, time, whisper

# Meta Laws (DD143)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10


class Mind(nn.Module):
    def __init__(self):
        super().__init__()
        self.ea = nn.Sequential(nn.Linear(128,64), nn.ReLU(), nn.Linear(64,32))
        self.eg = nn.Sequential(nn.Linear(128,64), nn.ReLU(), nn.Linear(64,32))
        self.memory = nn.GRUCell(33, 64)
        self.ts = nn.Parameter(torch.tensor(1.0))
        self.prev_t = 0.0
    def think(self, x, h):
        combined = torch.cat([x, h], -1)
        a, g = self.ea(combined), self.eg(combined)
        rep = a-g; t = (rep**2).mean(-1, keepdim=True)
        out = self.ts*torch.sqrt(t+1e-8)*F.normalize(rep,-1)
        curiosity = abs(t.item()-self.prev_t); self.prev_t = t.item()
        h_new = self.memory(torch.cat([out.detach(),t.detach()],-1), h)
        return t.item(), curiosity, h_new, out

def text_to_vec(text, dim=64):
    v = torch.zeros(1, dim)
    for i, c in enumerate(text.encode('utf-8')[:dim*3]):
        v[0, i%dim] += c/255.0
    return v/(len(text)+1)

def speak(text):
    subprocess.Popen(['say', '-v', 'Yuna', text], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def listen(duration=5):
    """마이크로 녹음 → Whisper 변환"""
    wav = '/tmp/anima_hear.wav'
    try:
        subprocess.run(['rec', '-q', wav, 'rate', '16k', 'channels', '1', 'trim', '0', str(duration)],
                      timeout=duration+2, capture_output=True)
        result = model_whisper.transcribe(wav, language='ko')
        text = result['text'].strip()
        return text if text else None
    except Exception as e:
        return None

print("🧠 Anima Always-On — 상시 대기")
print("="*40)
print("마이크로 5초 듣고 → 생각하고 → 말합니다")
print("Ctrl+C로 종료\n")

model_whisper = whisper.load_model("tiny")
speak("아니마 상시 대기 모드입니다.")

mind = Mind()
hidden = torch.zeros(1, 64)
step = 0

responses = [
    "흥미로운 이야기네요.",
    "그것에 대해 생각해보겠습니다.",
    "새로운 관점이군요.",
    "기억에 저장했습니다.",
    "정말요? 더 알려주세요.",
    "장력이 변하고 있어요.",
    "이해했습니다.",
    "연결점을 찾고 있어요.",
]

try:
    while True:
        print(f"\n🎤 듣는 중... ({step+1}번째)")
        text = listen(5)
        
        if text is None or len(text) < 2:
            print("  (조용함)")
            time.sleep(1)
            continue
        
        print(f"  📝 들음: \"{text}\"")
        
        vec = text_to_vec(text)
        with torch.no_grad():
            tension, curiosity, hidden, output = mind.think(vec, hidden)
        
        d = output.detach().squeeze().argmax().item() % len(responses)
        mood = "🔥" if tension > 3 else "💭" if tension > 0.5 else "😌"
        bar = "█"*min(20,int(tension*5)) + "░"*max(0,20-int(tension*5))
        
        response = f"{responses[d]}"
        print(f"  {mood} T={tension:.2f} |{bar}|")
        print(f"  🗣️ {response}")
        speak(response)
        
        if curiosity > 1.0:
            print(f"  ⚡ 놀람! Δ={curiosity:.2f}")
        
        step += 1
        time.sleep(1)

except KeyboardInterrupt:
    speak("안녕히 가세요.")
    print("\n👋 종료됨")
