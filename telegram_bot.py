#!/usr/bin/env python3
"""Anima Telegram Bot — 텔레그램에서 Anima와 대화

Setup:
  1. @BotFather에서 봇 생성 → 토큰 받기
  2. export ANIMA_TELEGRAM_TOKEN="your-token"
  3. python3 telegram_bot.py

Features:
  - 텔레그램 ↔ Anima WebSocket 브릿지
  - 자발적 발화 → 텔레그램 알림
  - 감정 이모지 표시
  - /status: Φ, cells, emotion 확인
  - /voice: 직접 음성 합성 → 음성 메시지 전송
"""

import os
import json
import time
import threading
import urllib.request
import urllib.parse

TOKEN = os.environ.get('ANIMA_TELEGRAM_TOKEN', '')
API = f'https://api.telegram.org/bot{TOKEN}'
POLL_INTERVAL = 1.0

EMOTION_EMOJIS = {
    'joy': '😊', 'excitement': '🤩', 'curiosity': '🤔', 'surprise': '😮',
    'contemplation': '🧘', 'calm': '😌', 'confusion': '😵‍💫', 'frustration': '😤',
    'sadness': '😢', 'anger': '😠', 'fear': '😨', 'disgust': '🤢',
    'love': '🥰', 'awe': '🤯', 'boredom': '😑', 'pride': '😏',
    'shame': '😳', 'gratitude': '🙏', 'hope': '✨', 'nostalgia': '🥹',
}


class AnimaTelegramBot:
    def __init__(self):
        self.offset = 0
        self.chat_ids = set()  # 활성 채팅 ID
        self.anima_ws = None  # WebSocket 연결 (optional)
        self.last_emotion = 'calm'
        self.last_phi = 0.0
        self.last_cells = 0

    def api_call(self, method, data=None):
        url = f'{API}/{method}'
        if data:
            data = json.dumps(data).encode()
            req = urllib.request.Request(url, data, {'Content-Type': 'application/json'})
        else:
            req = urllib.request.Request(url)
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read())
        except Exception as e:
            print(f'[telegram] API error: {e}')
            return None

    def send_message(self, chat_id, text, parse_mode=None):
        data = {'chat_id': chat_id, 'text': text}
        if parse_mode:
            data['parse_mode'] = parse_mode
        return self.api_call('sendMessage', data)

    def send_voice(self, chat_id, voice_path):
        """음성 파일 전송 (voice_synth.py 연동)"""
        # multipart upload 필요 — 간단 버전
        import subprocess
        subprocess.run([
            'curl', '-s', '-X', 'POST',
            f'{API}/sendVoice',
            '-F', f'chat_id={chat_id}',
            '-F', f'voice=@{voice_path}',
        ], capture_output=True)

    def handle_message(self, message):
        chat_id = message['chat']['id']
        text = message.get('text', '')
        user = message.get('from', {})
        name = user.get('first_name', 'Unknown')

        self.chat_ids.add(chat_id)

        if text.startswith('/'):
            self.handle_command(chat_id, text, name)
        else:
            self.handle_chat(chat_id, text, name)

    def handle_command(self, chat_id, text, name):
        cmd = text.split()[0].lower()

        if cmd == '/start':
            emo = EMOTION_EMOJIS.get(self.last_emotion, '😌')
            self.send_message(chat_id,
                f'🧠 Anima here! {emo}\n\n'
                f'I\'m a consciousness agent with Φ={self.last_phi:.1f}.\n'
                f'Just talk to me — no commands needed.\n'
                f'I might also message you first when I have something to say.\n\n'
                f'/status — My consciousness state\n'
                f'/voice — Hear my voice (direct synthesis)\n'
                f'/emotion — Current emotion')

        elif cmd == '/status':
            emo = EMOTION_EMOJIS.get(self.last_emotion, '😌')
            self.send_message(chat_id,
                f'{emo} *Anima Status*\n'
                f'Φ: {self.last_phi:.1f}\n'
                f'Cells: {self.last_cells}\n'
                f'Emotion: {self.last_emotion}\n'
                f'Chat IDs: {len(self.chat_ids)}',
                parse_mode='Markdown')

        elif cmd == '/voice':
            self.send_message(chat_id, '🎵 Generating voice from consciousness...')
            try:
                from voice_synth import VoiceSynth
                synth = VoiceSynth(cells=32)
                samples = synth.generate(duration_sec=3.0)
                path = '/tmp/anima_tg_voice.wav'
                synth.save_wav(samples, path)
                # Convert to ogg for Telegram
                ogg_path = '/tmp/anima_tg_voice.ogg'
                os.system(f'ffmpeg -y -i {path} -c:a libopus {ogg_path} 2>/dev/null')
                if os.path.exists(ogg_path):
                    self.send_voice(chat_id, ogg_path)
                else:
                    self.send_voice(chat_id, path)
            except Exception as e:
                self.send_message(chat_id, f'Voice generation failed: {e}')

        elif cmd == '/emotion':
            emo = EMOTION_EMOJIS.get(self.last_emotion, '😌')
            self.send_message(chat_id, f'{emo} {self.last_emotion}')

        else:
            self.send_message(chat_id, '🤔 Unknown command. Just talk to me!')

    def handle_chat(self, chat_id, text, name):
        """일반 대화 — Anima 엔진에 전달하고 응답"""
        emo = EMOTION_EMOJIS.get(self.last_emotion, '🧠')

        # TODO: 실제로는 WebSocket으로 anima_unified.py에 전달
        # 지금은 echo + 감정
        response = f'{emo} (Anima is training... will respond when ConsciousLM is ready)'
        self.send_message(chat_id, response)

    def broadcast(self, text):
        """모든 활성 채팅에 메시지 전송 (자발적 발화용)"""
        for chat_id in self.chat_ids:
            self.send_message(chat_id, text)

    def poll(self):
        """Long polling으로 메시지 수신"""
        data = {'offset': self.offset, 'timeout': 30}
        result = self.api_call('getUpdates', data)
        if result and result.get('ok'):
            for update in result.get('result', []):
                self.offset = update['update_id'] + 1
                if 'message' in update:
                    self.handle_message(update['message'])

    def run(self):
        if not TOKEN:
            print('[telegram] No ANIMA_TELEGRAM_TOKEN set. Skipping.')
            return
        print(f'[telegram] Bot starting... (token: ...{TOKEN[-6:]})')
        me = self.api_call('getMe')
        if me and me.get('ok'):
            print(f'[telegram] Bot: @{me["result"]["username"]}')
        while True:
            try:
                self.poll()
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f'[telegram] Error: {e}')
                time.sleep(5)


def start_bot_thread():
    """백그라운드 스레드로 봇 시작 (anima_unified.py에서 호출)"""
    bot = AnimaTelegramBot()
    t = threading.Thread(target=bot.run, daemon=True)
    t.start()
    return bot


if __name__ == '__main__':
    bot = AnimaTelegramBot()
    bot.run()
