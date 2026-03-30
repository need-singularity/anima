#!/usr/bin/env python3
"""Anima + Claude Code — 마이크→Whisper→Claude→TTS 상시 루프"""
import subprocess, time, os, sys

def listen(duration=5):
    """마이크 녹음 → Whisper STT"""
    wav = '/tmp/anima_hear.wav'
    try:
        subprocess.run(['rec', '-q', wav, 'rate', '16k', 'channels', '1', 'trim', '0', str(duration)],
                      timeout=duration+3, capture_output=True)
        import whisper

# Meta Laws (DD143)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10

        model = whisper.load_model("tiny")
        result = model.transcribe(wav, language='ko')
        return result['text'].strip()
    except:
        return None

def ask_claude(question):
    """Claude CLI로 질문 → 답변"""
    try:
        result = subprocess.run(
            ['claude', '-p', question],
            capture_output=True, text=True, timeout=30
        )
        return result.stdout.strip()
    except:
        return "응답을 생성할 수 없었습니다."

def speak(text):
    """Mac TTS"""
    # 길면 자르기
    short = text[:200]
    subprocess.Popen(['say', '-v', 'Yuna', short],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

print("🧠 Anima + Claude — 상시 대화")
print("="*40)
print("마이크(5초) → Whisper → Claude → 스피커")
print("Ctrl+C 종료\n")

speak("아니마 클로드 모드입니다. 말씀하세요.")

step = 0
try:
    while True:
        print(f"\n🎤 듣는 중... ({step+1})")
        text = listen(5)

        if not text or len(text) < 2:
            print("  (조용함)")
            time.sleep(1)
            continue

        print(f"  📝 \"{text}\"")
        print(f"  🧠 Claude 생각 중...")

        answer = ask_claude(text)
        print(f"  🗣️ {answer[:300]}")
        speak(answer)

        # Claude TTS 끝날 때까지 대기
        time.sleep(max(3, len(answer)//20))
        step += 1

except KeyboardInterrupt:
    speak("안녕히 가세요.")
    print("\n👋 종료")
