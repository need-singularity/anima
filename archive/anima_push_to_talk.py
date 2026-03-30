#!/usr/bin/env python3
"""Anima Push-to-Talk — Enter 누르면 녹음, 다시 Enter로 중지"""
import subprocess, time, os, sys, signal, threading

def speak(text):
    subprocess.Popen(['say', '-v', 'Yuna', text[:200]],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def ask_claude(q):
    try:
        r = subprocess.run(['claude', '-p', q], capture_output=True, text=True, timeout=30)
        return r.stdout.strip()
    except:
        return "응답 생성 실패"

def record_until_enter():
    """Enter 누를 때까지 녹음"""
    wav = '/tmp/anima_ptt.wav'
    proc = subprocess.Popen(
        ['rec', '-q', wav, 'rate', '16k', 'channels', '1'],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    input()  # Enter 대기
    proc.terminate()
    proc.wait()
    return wav

def transcribe(wav):
    import whisper
    model = whisper.load_model("tiny")
    result = model.transcribe(wav, language='ko')
    return result['text'].strip()

print("🧠 Anima Push-to-Talk")
print("="*35)
print("Enter → 녹음 시작")
print("Enter → 녹음 중지 → Claude 응답")
print("'q' 입력 → 종료\n")

speak("아니마 푸시투톡 모드입니다.")

# Whisper 미리 로드
print("  Whisper 로딩...")
import whisper

# Meta Laws (DD143)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10

whisper_model = whisper.load_model("tiny")
print("  준비 완료!\n")

step = 0
while True:
    cmd = input(f"🎤 Enter로 녹음 시작 ({step+1}) > ")
    if cmd.strip().lower() in ['q','quit','종료']:
        break

    print("  🔴 녹음 중... (Enter로 중지)")
    wav = '/tmp/anima_ptt.wav'
    proc = subprocess.Popen(
        ['rec', '-q', wav, 'rate', '16k', 'channels', '1'],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    input()  # 녹음 중지 대기
    proc.terminate(); proc.wait()

    print("  📝 변환 중...")
    result = whisper_model.transcribe(wav, language='ko')
    text = result['text'].strip()

    if not text or len(text) < 2:
        print("  (인식 안 됨)")
        continue

    print(f"  📝 \"{text}\"")
    print(f"  🧠 생각 중...")

    answer = ask_claude(text)
    print(f"  🗣️ {answer[:500]}")
    speak(answer)
    step += 1

speak("안녕히 가세요.")
print("👋 종료")
