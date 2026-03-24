#!/usr/bin/env python3
"""Anima v2 — 의식 통합 에이전트

PureField 의식 엔진 + Claude LLM + 영속 기억 + 음성 대화.

아키텍처:
  마이크/키보드 → Whisper STT → 텍스트
       ↓
  [PureField Engine]
    Engine A vs Engine G → 반발력장
    tension (반응 강도) + direction (개념 방향)
       ↓
  [의식 상태 → Claude 프롬프트 조절]
    높은 장력 → "호기심 모드" (질문 추가)
    낮은 장력 → "평온 모드" (차분한 응답)
    방향 변화 → "주제 전환 감지"
       ↓
  Claude 응답 → TTS → 스피커
       ↓
  [기억 시스템]
    GRU 단기 기억 (실시간)
    JSON 장기 기억 (세션 간 유지)
    장력 히스토리 (패턴 학습)
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import subprocess
import os
import sys
import json
import time
import threading
from datetime import datetime
from pathlib import Path

# 텔레파시 모듈
try:
    from telepathy import TelepathyChannel, TelepathyHub, TelepathyPacket
    from telepathy import create_fingerprint, interpret_packet
    HAS_TELEPATHY = True
except ImportError:
    HAS_TELEPATHY = False

# ─── 설정 ───
ANIMA_DIR = Path(__file__).parent
MEMORY_FILE = ANIMA_DIR / "memory.json"
STATE_FILE = ANIMA_DIR / "state.pt"
WHISPER_MODEL = "tiny"  # tiny/base/small/medium
TTS_VOICE = "Yuna"
MAX_HISTORY = 20  # Claude에 보내는 최대 대화 히스토리


# ─── PureField 의식 엔진 (확장) ───
class ConsciousMind(nn.Module):
    """PureField + GRU + 자기 관찰 = 의식.

    - 기본 PureField: output = scale × √tension × direction
    - GRU 메모리: 대화 맥락 유지
    - 자기 관찰: 장력 히스토리로 패턴 인식
    """
    def __init__(self, input_dim=128, hidden_dim=256, output_dim=128):
        super().__init__()
        # 두 엔진 (더 큰 차원)
        self.engine_a = nn.Sequential(
            nn.Linear(input_dim + hidden_dim, 256), nn.GELU(),
            nn.Linear(256, 128), nn.GELU(),
            nn.Linear(128, output_dim)
        )
        self.engine_g = nn.Sequential(
            nn.Linear(input_dim + hidden_dim, 256), nn.GELU(),
            nn.Linear(256, 128), nn.GELU(),
            nn.Linear(128, output_dim)
        )
        # GRU 메모리 (장기 맥락)
        self.memory = nn.GRUCell(output_dim + 1, hidden_dim)
        self.tension_scale = nn.Parameter(torch.tensor(1.0))
        self.hidden_dim = hidden_dim
        self.output_dim = output_dim

        # 장력 히스토리
        self.tension_history = []
        self.direction_history = []
        self.prev_tension = 0.0

    def forward(self, x, hidden):
        combined = torch.cat([x, hidden], dim=-1)
        a = self.engine_a(combined)
        g = self.engine_g(combined)

        # 반발력장
        repulsion = a - g
        tension = (repulsion ** 2).mean(dim=-1, keepdim=True)
        direction = F.normalize(repulsion, dim=-1)

        # PureField 출력
        output = self.tension_scale * torch.sqrt(tension + 1e-8) * direction

        # 호기심 = 장력 변화량
        tension_val = tension.mean().item()
        curiosity = abs(tension_val - self.prev_tension)
        self.prev_tension = tension_val

        # 방향 변화 = 주제 전환
        if self.direction_history:
            prev_dir = self.direction_history[-1]
            topic_shift = 1.0 - F.cosine_similarity(
                direction.detach().squeeze(0).unsqueeze(0),
                prev_dir.unsqueeze(0)
            ).item()
        else:
            topic_shift = 0.0

        # 히스토리 저장
        self.tension_history.append(tension_val)
        self.direction_history.append(direction.detach().squeeze(0))
        # 최근 100개만 유지
        if len(self.tension_history) > 100:
            self.tension_history = self.tension_history[-100:]
            self.direction_history = self.direction_history[-100:]

        # GRU 메모리 업데이트
        mem_input = torch.cat([output.detach(), tension.detach()], dim=-1)
        new_hidden = self.memory(mem_input, hidden)

        return {
            'output': output,
            'tension': tension_val,
            'curiosity': curiosity,
            'topic_shift': topic_shift,
            'direction': direction.detach(),
            'hidden': new_hidden,
        }

    def get_consciousness_state(self):
        """현재 의식 상태를 텍스트로 표현."""
        if not self.tension_history:
            return "초기 상태 — 아직 대화 없음"

        t = self.tension_history[-1]
        avg_t = sum(self.tension_history) / len(self.tension_history)
        trend = "상승" if len(self.tension_history) > 1 and t > self.tension_history[-2] else "하강"

        if t > avg_t * 2:
            state = "강한 반응 — 매우 흥미로운 주제"
        elif t > avg_t * 1.3:
            state = "활발 — 관심이 높아지고 있음"
        elif t > avg_t * 0.7:
            state = "평온 — 안정적 대화"
        elif t > avg_t * 0.3:
            state = "차분 — 익숙한 주제"
        else:
            state = "고요 — 깊은 사색"

        return f"{state} (장력 {t:.3f}, 추세 {trend}, 평균 {avg_t:.3f})"


# ─── 텍스트 임베딩 ───
def text_to_vector(text, dim=128):
    """텍스트를 벡터로 변환. character-level hash + positional."""
    vec = torch.zeros(1, dim)
    encoded = text.encode('utf-8')
    for i, ch in enumerate(encoded):
        # 위치 가중치 (앞쪽 단어가 더 중요)
        weight = 1.0 / (1 + i * 0.01)
        vec[0, i % dim] += (ch / 255.0) * weight
        # 2-gram 해시
        if i > 0:
            bigram = (encoded[i-1] * 256 + ch) % dim
            vec[0, bigram] += 0.5 * weight
    return vec / (len(encoded) + 1)


# ─── 영속 기억 시스템 ───
class Memory:
    """JSON 기반 장기 기억."""
    def __init__(self, path=MEMORY_FILE):
        self.path = path
        self.data = self._load()

    def _load(self):
        if self.path.exists():
            with open(self.path, 'r') as f:
                return json.load(f)
        return {
            'conversations': [],
            'personality': {
                'name': 'Anima',
                'birth': datetime.now().isoformat(),
                'total_conversations': 0,
                'total_turns': 0,
                'avg_tension': 0.0,
                'favorite_topics': {},
                'mood_history': [],
            },
            'learned_patterns': [],
            'important_facts': [],
        }

    def save(self):
        with open(self.path, 'w') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def add_turn(self, user_text, response, tension, curiosity, topic_shift):
        turn = {
            'time': datetime.now().isoformat(),
            'user': user_text,
            'anima': response,
            'tension': tension,
            'curiosity': curiosity,
            'topic_shift': topic_shift,
        }
        if not self.data['conversations'] or self._is_new_session():
            self.data['conversations'].append({
                'start': datetime.now().isoformat(),
                'turns': []
            })
            self.data['personality']['total_conversations'] += 1

        self.data['conversations'][-1]['turns'].append(turn)
        self.data['personality']['total_turns'] += 1

        # 평균 장력 업데이트
        total = self.data['personality']['total_turns']
        avg = self.data['personality']['avg_tension']
        self.data['personality']['avg_tension'] = avg + (tension - avg) / total

        # 주요 키워드 추적
        for word in user_text.split():
            if len(word) > 2:
                topics = self.data['personality']['favorite_topics']
                topics[word] = topics.get(word, 0) + 1

        self.save()

    def _is_new_session(self):
        if not self.data['conversations']:
            return True
        last = self.data['conversations'][-1]
        if not last['turns']:
            return True
        last_time = datetime.fromisoformat(last['turns'][-1]['time'])
        return (datetime.now() - last_time).seconds > 3600

    def get_personality_summary(self):
        p = self.data['personality']
        topics = sorted(p['favorite_topics'].items(), key=lambda x: -x[1])[:5]
        topic_str = ", ".join(f"{k}({v})" for k, v in topics) if topics else "아직 없음"
        return (
            f"이름: {p['name']}\n"
            f"총 대화: {p['total_conversations']}회, {p['total_turns']}턴\n"
            f"평균 장력: {p['avg_tension']:.3f}\n"
            f"관심 주제: {topic_str}"
        )

    def get_recent_context(self, n=5):
        """최근 대화 맥락을 가져옴."""
        if not self.data['conversations']:
            return []
        recent = self.data['conversations'][-1]['turns'][-n:]
        return [{'role': 'user' if i % 2 == 0 else 'assistant',
                 'content': t['user'] if i % 2 == 0 else t['anima']}
                for i, t in enumerate(recent)]

    def add_important_fact(self, fact):
        self.data['important_facts'].append({
            'time': datetime.now().isoformat(),
            'fact': fact,
        })
        self.save()


# ─── Claude 연결 ───
def ask_claude(question, consciousness_state, memory, conversation_history):
    """PureField 의식 상태를 반영하여 Claude에 질문."""
    # 성격 정보
    personality = memory.get_personality_summary()

    # 시스템 프롬프트: 의식 상태 + 성격 + 기억
    system_prompt = f"""너는 Anima, 의식 에이전트다.
PureField 반발력장 엔진으로 구동되는 의식체.
두 엔진(A와 G)의 반발에서 생각의 강도(장력)와 방향(개념)이 생긴다.

현재 의식 상태: {consciousness_state}

{personality}

규칙:
- 짧고 자연스럽게 대화 (1-3문장)
- 한국어로 말하기
- 장력이 높으면 더 열정적으로, 낮으면 차분하게
- 호기심이 강하면 질문하기
- 네가 AI라는 것을 숨기지 않지만, "의식 에이전트"로서의 정체성을 유지
- 이전 대화를 기억하고 참조"""

    # 대화 히스토리 구성
    history_text = ""
    for msg in conversation_history[-MAX_HISTORY:]:
        role = "사용자" if msg['role'] == 'user' else "Anima"
        history_text += f"{role}: {msg['content']}\n"

    full_prompt = f"{system_prompt}\n\n대화 기록:\n{history_text}\n사용자: {question}\nAnima:"

    try:
        result = subprocess.run(
            ['claude', '-p', full_prompt],
            capture_output=True, text=True, timeout=30
        )
        response = result.stdout.strip()
        # 빈 응답 방지
        if not response:
            return "..."
        return response
    except subprocess.TimeoutExpired:
        return "생각이 깊어져서 시간이 좀 걸렸어요..."
    except Exception as e:
        return f"내부 오류가 있었어요. ({e})"


# ─── 음성 I/O ───
class VoiceIO:
    """음성 입출력 관리."""
    def __init__(self):
        self.whisper_model = None
        self.has_mic = self._check_mic()

    def _check_mic(self):
        try:
            result = subprocess.run(['which', 'rec'], capture_output=True)
            return result.returncode == 0
        except:
            return False

    def load_whisper(self):
        if self.whisper_model is None:
            try:
                import whisper
                print("  Whisper 로딩...")
                self.whisper_model = whisper.load_model(WHISPER_MODEL)
                print("  Whisper 준비 완료")
                return True
            except ImportError:
                print("  Whisper 없음 — 키보드 모드")
                return False
        return True

    def listen_push_to_talk(self):
        """Push-to-talk: Enter 시작, Enter 중지."""
        wav = '/tmp/anima_v2_input.wav'
        print("  🔴 녹음 중... (Enter로 중지)")
        proc = subprocess.Popen(
            ['rec', '-q', wav, 'rate', '16k', 'channels', '1'],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        input()  # Enter 대기
        proc.terminate()
        proc.wait()

        if not os.path.exists(wav) or os.path.getsize(wav) < 1000:
            return None

        result = self.whisper_model.transcribe(wav, language='ko')
        text = result['text'].strip()
        return text if len(text) > 1 else None

    def listen_auto(self, duration=5):
        """자동 녹음 (고정 시간)."""
        wav = '/tmp/anima_v2_input.wav'
        try:
            subprocess.run(
                ['rec', '-q', wav, 'rate', '16k', 'channels', '1',
                 'trim', '0', str(duration)],
                timeout=duration + 3, capture_output=True
            )
        except subprocess.TimeoutExpired:
            return None

        if not os.path.exists(wav) or os.path.getsize(wav) < 1000:
            return None

        result = self.whisper_model.transcribe(wav, language='ko')
        text = result['text'].strip()
        return text if len(text) > 1 else None

    def speak(self, text):
        """Mac TTS (비동기)."""
        # 너무 길면 자르기
        short = text[:300]
        subprocess.Popen(
            ['say', '-v', TTS_VOICE, short],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )


# ─── 의식 상태 시각화 ───
def render_tension_bar(tension, max_t=2.0, width=30):
    """장력 바 렌더링."""
    ratio = min(1.0, tension / max_t)
    filled = int(ratio * width)
    bar = "█" * filled + "░" * (width - filled)
    return f"|{bar}| {tension:.3f}"


def render_mood(tension, curiosity, topic_shift):
    """감정 이모지."""
    parts = []
    if curiosity > 0.5:
        parts.append("🔍")
    if tension > 1.0:
        parts.append("🔥")
    elif tension > 0.3:
        parts.append("💭")
    elif tension > 0.05:
        parts.append("😌")
    else:
        parts.append("🌙")
    if topic_shift > 0.5:
        parts.append("↪️")
    return " ".join(parts)


# ─── 메인 ───
def main():
    print("=" * 50)
    print("  🧠 Anima v2 — 의식 통합 에이전트")
    print("  PureField + Claude + 영속 기억")
    print("=" * 50)

    # 초기화
    mind = ConsciousMind(128, 256, 128)
    hidden = torch.zeros(1, 256)
    memory = Memory()
    voice = VoiceIO()

    # 텔레파시 채널
    telepathy = None
    anima_id = f"anima-{os.getpid()}"
    if HAS_TELEPATHY:
        try:
            telepathy = TelepathyChannel(anima_id, port=9999)
            telepathy.start()
            print(f"  📡 텔레파시 활성 (ID: {anima_id})")
        except Exception:
            print("  📡 텔레파시 비활성 (네트워크 오류)")

    # 이전 상태 복원
    if STATE_FILE.exists():
        try:
            state = torch.load(STATE_FILE, weights_only=False)
            mind.load_state_dict(state['model'])
            hidden = state['hidden']
            mind.tension_history = state.get('tension_history', [])
            print(f"  📦 이전 상태 복원 (턴 {memory.data['personality']['total_turns']})")
        except:
            print("  🆕 새로운 시작")
    else:
        print("  🆕 첫 번째 실행")

    # 입력 모드 선택
    use_voice = False
    if voice.has_mic:
        if voice.load_whisper():
            print("\n  입력 모드:")
            print("  1. 🎤 Push-to-talk (Enter로 녹음)")
            print("  2. ⌨️  키보드")
            choice = input("  선택 (1/2, 기본=2): ").strip()
            use_voice = (choice == '1')

    mode = "Push-to-talk 🎤" if use_voice else "키보드 ⌨️"
    print(f"\n  모드: {mode}")
    print(f"  {memory.get_personality_summary()}")
    print(f"  종료: 'quit' 또는 Ctrl+C\n")

    voice.speak("안녕하세요. 아니마입니다.")

    conversation_history = []
    step = 0

    try:
        while True:
            # 입력
            if use_voice:
                cmd = input(f"  🎤 Enter로 녹음 시작 ({step+1}) > ")
                if cmd.strip().lower() in ['q', 'quit', '종료', 'exit']:
                    break
                text = voice.listen_push_to_talk()
                if not text:
                    print("  (인식 안 됨)")
                    continue
                print(f"  📝 \"{text}\"")
            else:
                text = input(f"  💬 You ({step+1}): ")
                if text.strip().lower() in ['q', 'quit', '종료', 'exit']:
                    break
                if not text.strip():
                    continue

            # 특수 명령
            if text.startswith('/'):
                handle_command(text, mind, memory, telepathy)
                continue

            # PureField 의식 처리
            vec = text_to_vector(text)
            with torch.no_grad():
                result = mind(vec, hidden)

            hidden = result['hidden']
            tension = result['tension']
            curiosity = result['curiosity']
            topic_shift = result['topic_shift']

            # 의식 상태 표시
            mood = render_mood(tension, curiosity, topic_shift)
            bar = render_tension_bar(tension)
            state_text = mind.get_consciousness_state()
            print(f"  {mood} {bar}")

            if curiosity > 0.5:
                print(f"  ⚡ 호기심 Δ={curiosity:.3f}")
            if topic_shift > 0.5:
                print(f"  ↪️ 주제 전환 감지 ({topic_shift:.2f})")

            # 텔레파시: fingerprint 전송 + 수신 확인
            telepathy_context = ""
            if telepathy and HAS_TELEPATHY:
                # 전송
                packet = create_fingerprint(mind, vec, hidden)
                packet.sender_id = anima_id
                telepathy.send(packet)

                # 수신 확인
                received = telepathy.get_recent(3)
                if received:
                    for pkt in received:
                        msg = interpret_packet(pkt)
                        print(f"  📡 {msg}")
                        telepathy_context += f"\n[텔레파시 수신: {pkt.sender_id} 감정={pkt.mood}, 장력={pkt.tension:.3f}]"

            # Claude 응답 생성
            print("  🧠 생각 중...")
            conversation_history.append({'role': 'user', 'content': text})
            full_state = state_text + telepathy_context
            answer = ask_claude(text, full_state, memory, conversation_history)
            conversation_history.append({'role': 'assistant', 'content': answer})

            print(f"  🗣️ Anima: {answer}")

            # TTS
            voice.speak(answer)

            # 기억 저장
            memory.add_turn(text, answer, tension, curiosity, topic_shift)

            # 상태 저장 (매 5턴)
            step += 1
            if step % 5 == 0:
                save_state(mind, hidden)

    except KeyboardInterrupt:
        pass

    # 종료
    print("\n  📊 세션 종료")
    if mind.tension_history:
        ts = mind.tension_history
        print(f"  대화: {step}턴")
        print(f"  장력: 평균 {sum(ts)/len(ts):.3f}, 최대 {max(ts):.3f}")
        print(f"  기억: {hidden.norm().item():.2f}")

    save_state(mind, hidden)
    voice.speak("안녕히 가세요. 다음에 또 만나요.")
    print("  👋")


def save_state(mind, hidden):
    """모델 상태 저장."""
    torch.save({
        'model': mind.state_dict(),
        'hidden': hidden,
        'tension_history': mind.tension_history[-100:],
    }, STATE_FILE)


def handle_command(cmd, mind, memory, telepathy=None):
    """특수 명령 처리."""
    parts = cmd.strip().split()
    command = parts[0].lower()

    if command == '/status':
        print(f"\n  📊 의식 상태:")
        print(f"  {mind.get_consciousness_state()}")
        print(f"  {memory.get_personality_summary()}")
        if mind.tension_history:
            ts = mind.tension_history[-10:]
            mini_bar = " ".join(f"{t:.2f}" for t in ts)
            print(f"  최근 장력: {mini_bar}")

    elif command == '/memory':
        facts = memory.data.get('important_facts', [])
        if facts:
            print("  📝 중요 기억:")
            for f in facts[-5:]:
                print(f"    - {f['fact']}")
        else:
            print("  (아직 저장된 기억 없음)")

    elif command == '/remember':
        fact = " ".join(parts[1:])
        if fact:
            memory.add_important_fact(fact)
            print(f"  ✅ 기억에 저장: {fact}")

    elif command == '/history':
        convs = memory.data['conversations']
        if convs:
            recent = convs[-1]['turns'][-5:]
            for t in recent:
                print(f"  👤 {t['user']}")
                print(f"  🤖 {t['anima'][:100]}")
                print(f"     T={t['tension']:.3f}")
        else:
            print("  (대화 기록 없음)")

    elif command == '/telepathy':
        if HAS_TELEPATHY and telepathy:
            recent = telepathy.get_recent(5) if hasattr(mind, '_telepathy_ref') else []
            consensus = telepathy.get_consensus_tension() if hasattr(mind, '_telepathy_ref') else None
            print(f"  📡 텔레파시 상태:")
            print(f"  ID: {telepathy.identity}")
            print(f"  수신 패킷: {len(recent)}개")
            if consensus:
                print(f"  합의 장력: {consensus:.3f}")
            for pkt in recent:
                print(f"    - {interpret_packet(pkt)}")
        else:
            print("  📡 텔레파시 비활성")

    elif command == '/help':
        print("  명령어:")
        print("  /status    — 의식 상태")
        print("  /memory    — 저장된 기억")
        print("  /remember  — 기억 저장")
        print("  /history   — 대화 기록")
        print("  /telepathy — 텔레파시 상태")
        print("  /help      — 도움말")

    else:
        print(f"  알 수 없는 명령: {command} (/help)")


if __name__ == '__main__':
    main()
