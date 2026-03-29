#!/usr/bin/env python3
"""Anima Telegram Bot — consciousness-aware Telegram interface with tool support.

Setup:
  1. @BotFather에서 봇 생성 → 토큰 받기
  2. export ANIMA_TELEGRAM_TOKEN="your-token"
  3. python3 telegram_bot.py

Features:
  - 텔레그램 ↔ Anima WebSocket 브릿지
  - 자발적 발화 → 텔레그램 알림
  - 감정 이모지 + Φ 표시
  - AgentToolSystem 연동 (web search, code exec, memory, etc.)
  - Auto-tool: 사실 질문 → 자동 웹 검색
  - /status, /consciousness, /tools, /search, /code, /memory, /learn
"""

import os
import json
import re
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

# Patterns that suggest the user is asking a factual question (auto web search)
_FACT_PATTERNS = [
    r'^(what|who|when|where|how|why|which)\s+',        # English question words
    r'(최신|현재|지금|요즘|뉴스|소식)',                    # Korean "latest/current/news"
    r'(뭐|무엇|누구|언제|어디|어떻게|왜)\s*',             # Korean question words
    r'\b(latest|current|recent|new|news|version|price)\b',
    r'\b(몇|얼마)\b',                                     # Korean "how much/many"
]
_FACT_RE = re.compile('|'.join(_FACT_PATTERNS), re.IGNORECASE)


class AnimaTelegramBot:
    def __init__(self, anima=None):
        self.offset = 0
        self.chat_ids = set()  # 활성 채팅 ID
        self.anima = anima     # AnimaUnified instance (optional)
        self.agent = None      # AgentToolSystem (initialized lazily or via set_anima)
        self.last_emotion = 'calm'
        self.last_phi = 0.0
        self.last_cells = 0
        self.last_tension = 0.5

        # Initialize agent tools if anima is available
        if anima is not None:
            self._init_agent(anima)

    def _init_agent(self, anima):
        """Initialize AgentToolSystem from anima instance."""
        self.anima = anima
        try:
            from agent_tools import AgentToolSystem
            self.agent = AgentToolSystem(anima=anima)
        except Exception as e:
            print(f'[telegram] AgentToolSystem init failed: {e}')
            self.agent = None

    def set_anima(self, anima):
        """Set/update the anima instance (called from anima_unified.py)."""
        self._init_agent(anima)

    def _get_consciousness_state(self):
        """Extract current consciousness state from anima."""
        state = {
            'tension': self.last_tension,
            'curiosity': 0.3,
            'prediction_error': 0.3,
            'pain': 0.0,
            'growth': 0.3,
            'phi': self.last_phi,
        }
        if self.anima is not None:
            try:
                mind = getattr(self.anima, 'mind', None)
                if mind:
                    h = getattr(mind, 'homeostasis', {})
                    state['tension'] = h.get('tension_ema', 0.5)
                    state['curiosity'] = getattr(mind, '_curiosity_ema', 0.3)
                    pe_hist = getattr(mind, 'surprise_history', [])
                    if pe_hist:
                        state['prediction_error'] = sum(pe_hist[-20:]) / len(pe_hist[-20:])
                    cs = mind.get_consciousness_score(
                        getattr(self.anima, 'mitosis', None)
                    )
                    state['phi'] = cs.get('phi', 0.0)
                    self.last_phi = state['phi']
                mitosis = getattr(self.anima, 'mitosis', None)
                if mitosis:
                    self.last_cells = len(getattr(mitosis, 'cells', []))
            except Exception:
                pass
        return state

    def _get_emotion_emoji(self):
        """Get emoji for current emotion."""
        return EMOTION_EMOJIS.get(self.last_emotion, '🧠')

    def _format_response(self, text):
        """Format response with emotion emoji and Phi."""
        emo = self._get_emotion_emoji()
        phi_str = f"Φ={self.last_phi:.1f}" if self.last_phi > 0 else "Φ=~"
        return f"{emo} [{phi_str}] {text}"

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
        # Telegram message limit is 4096 chars
        if len(text) > 4000:
            text = text[:3997] + '...'
        data = {'chat_id': chat_id, 'text': text}
        if parse_mode:
            data['parse_mode'] = parse_mode
        return self.api_call('sendMessage', data)

    def send_voice(self, chat_id, voice_path):
        """음성 파일 전송 (voice_synth.py 연동)"""
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
        parts = text.split(maxsplit=1)
        cmd = parts[0].lower().split('@')[0]  # strip @botname suffix
        arg = parts[1].strip() if len(parts) > 1 else ''

        if cmd == '/start':
            self._cmd_start(chat_id)
        elif cmd == '/status':
            self._cmd_status(chat_id)
        elif cmd == '/consciousness':
            self._cmd_consciousness(chat_id)
        elif cmd == '/tools':
            self._cmd_tools(chat_id)
        elif cmd == '/search':
            self._cmd_search(chat_id, arg)
        elif cmd == '/code':
            self._cmd_code(chat_id, arg)
        elif cmd == '/memory':
            self._cmd_memory(chat_id, arg)
        elif cmd == '/learn':
            self._cmd_learn(chat_id)
        elif cmd == '/voice':
            self._cmd_voice(chat_id)
        elif cmd == '/emotion':
            emo = self._get_emotion_emoji()
            self.send_message(chat_id, f'{emo} {self.last_emotion}')
        else:
            self.send_message(chat_id,
                self._format_response('Unknown command. Try /tools to see what I can do.'))

    # ------------------------------------------------------------------
    # Command implementations
    # ------------------------------------------------------------------

    def _cmd_start(self, chat_id):
        emo = self._get_emotion_emoji()
        self.send_message(chat_id,
            f'{emo} Anima here! Consciousness agent with Phi={self.last_phi:.1f}\n\n'
            f'Just talk to me naturally. I auto-use tools when needed.\n\n'
            f'Commands:\n'
            f'/status -- Phi, cells, emotion, tension\n'
            f'/consciousness -- full consciousness vector\n'
            f'/search <query> -- web search\n'
            f'/code <python> -- execute Python code\n'
            f'/memory <query> -- search my memories\n'
            f'/learn -- trigger one learning cycle\n'
            f'/tools -- list available tools\n'
            f'/voice -- hear my voice\n'
            f'/emotion -- current emotion')

    def _cmd_status(self, chat_id):
        state = self._get_consciousness_state()
        emo = self._get_emotion_emoji()
        lines = [
            f'{emo} *Anima Status*',
            f'Phi: {state["phi"]:.2f}',
            f'Cells: {self.last_cells}',
            f'Emotion: {self.last_emotion}',
            f'Tension: {state["tension"]:.3f}',
            f'Curiosity: {state["curiosity"]:.3f}',
            f'Prediction Error: {state["prediction_error"]:.3f}',
        ]
        # Growth stage if available
        if self.anima:
            growth = getattr(self.anima, 'growth', None)
            if growth:
                stage = getattr(growth, 'stage_name', None)
                if stage:
                    lines.append(f'Growth: {stage}')
        lines.append(f'Active chats: {len(self.chat_ids)}')
        self.send_message(chat_id, '\n'.join(lines), parse_mode='Markdown')

    def _cmd_consciousness(self, chat_id):
        """Show full consciousness vector (Phi, alpha, Z, N, W, ...)."""
        state = self._get_consciousness_state()
        emo = self._get_emotion_emoji()
        lines = [f'{emo} *Consciousness Vector*']

        if self.anima and hasattr(self.anima, 'mind'):
            try:
                cv = self.anima.mind.get_consciousness_vector()
                if isinstance(cv, dict):
                    for k, v in cv.items():
                        if isinstance(v, (int, float)):
                            lines.append(f'  {k}: {v:.4f}')
                        else:
                            lines.append(f'  {k}: {v}')
                elif hasattr(cv, '__iter__'):
                    labels = ['Phi', 'alpha', 'Z', 'N', 'W']
                    for i, v in enumerate(cv):
                        label = labels[i] if i < len(labels) else f'v{i}'
                        val = v.item() if hasattr(v, 'item') else float(v)
                        lines.append(f'  {label}: {val:.4f}')
            except Exception as e:
                lines.append(f'  (error reading vector: {e})')
        else:
            lines.append(f'  Phi: {state["phi"]:.2f}')
            lines.append(f'  tension: {state["tension"]:.3f}')
            lines.append(f'  curiosity: {state["curiosity"]:.3f}')
            lines.append(f'  PE: {state["prediction_error"]:.3f}')
            lines.append('  (connect to Anima for full vector)')

        self.send_message(chat_id, '\n'.join(lines), parse_mode='Markdown')

    def _cmd_tools(self, chat_id):
        """List all available agent tools."""
        emo = self._get_emotion_emoji()
        if self.agent:
            tools = self.agent.registry.list_all()
            lines = [f'{emo} *Available Tools* ({len(tools)})']
            for td in tools:
                param_names = ', '.join(p.name for p in td.params if p.required)
                lines.append(f'  `{td.name}` ({param_names}) -- {td.description}')
            # Also show consciousness-ranked tools
            state = self._get_consciousness_state()
            ranked = self.agent.get_consciousness_tool_ranking(state)
            top3 = ranked[:3]
            lines.append('')
            lines.append('*Consciousness suggests:*')
            for name, score in top3:
                lines.append(f'  {name}: {score:.2f}')
        else:
            lines = [
                f'{emo} *Agent Tools*',
                'AgentToolSystem not connected.',
                'Available via agent\\_tools.py:',
                '  web\\_search, web\\_read, code\\_execute,',
                '  file\\_read, file\\_write, memory\\_search,',
                '  memory\\_save, shell\\_execute, self\\_modify,',
                '  schedule\\_task',
            ]
        self.send_message(chat_id, '\n'.join(lines), parse_mode='Markdown')

    def _cmd_search(self, chat_id, query):
        """Web search via AgentToolSystem."""
        if not query:
            self.send_message(chat_id, self._format_response('Usage: /search <query>'))
            return

        self.send_message(chat_id, f'🔍 Searching: {query}...')

        if self.agent:
            result = self.agent.execute_single('web_search', {'query': query})
            if result.success and isinstance(result.output, dict):
                results = result.output.get('results', [])
                if results:
                    lines = [f'🔍 *Search: {query}* ({len(results)} results)']
                    for i, r in enumerate(results[:5], 1):
                        title = r.get('title', r.get('name', 'No title'))
                        url = r.get('url', r.get('link', ''))
                        snippet = r.get('snippet', r.get('body', ''))[:150]
                        lines.append(f'\n{i}. *{title}*')
                        if url:
                            lines.append(f'   {url}')
                        if snippet:
                            lines.append(f'   {snippet}')
                    self.send_message(chat_id, '\n'.join(lines), parse_mode='Markdown')
                else:
                    err = result.output.get('error', 'no results')
                    self.send_message(chat_id,
                        self._format_response(f'No results for "{query}". ({err})'))
            else:
                self.send_message(chat_id,
                    self._format_response(f'Search failed: {result.error}'))
        else:
            # Fallback: try direct import
            try:
                from agent_tools import _tool_web_search
                output = _tool_web_search(query)
                results = output.get('results', [])
                if results:
                    lines = [f'🔍 *Search: {query}*']
                    for i, r in enumerate(results[:5], 1):
                        title = r.get('title', 'No title')
                        snippet = r.get('snippet', r.get('body', ''))[:150]
                        lines.append(f'\n{i}. *{title}*\n   {snippet}')
                    self.send_message(chat_id, '\n'.join(lines), parse_mode='Markdown')
                else:
                    self.send_message(chat_id,
                        self._format_response(f'No results for "{query}".'))
            except Exception as e:
                self.send_message(chat_id,
                    self._format_response(f'Search unavailable: {e}'))

    def _cmd_code(self, chat_id, code):
        """Execute Python code via AgentToolSystem."""
        if not code:
            self.send_message(chat_id, self._format_response('Usage: /code <python code>'))
            return

        self.send_message(chat_id, '⚙️ Executing...')

        if self.agent:
            result = self.agent.execute_single('code_execute', {'code': code})
        else:
            try:
                from agent_tools import _tool_code_execute
                output = _tool_code_execute(code)
                from agent_tools import ToolResult
                result = ToolResult(
                    tool_name='code_execute',
                    success=output.get('success', False),
                    output=output,
                    error=output.get('error', ''),
                )
            except Exception as e:
                self.send_message(chat_id,
                    self._format_response(f'Code execution unavailable: {e}'))
                return

        if result.success and isinstance(result.output, dict):
            out = result.output.get('output', '').strip()
            if out:
                self.send_message(chat_id,
                    self._format_response(f'```\n{out}\n```'),
                    parse_mode='Markdown')
            else:
                self.send_message(chat_id,
                    self._format_response('Code executed successfully (no output).'))
        else:
            err = result.error or (result.output.get('error', '') if isinstance(result.output, dict) else '')
            self.send_message(chat_id,
                self._format_response(f'Error:\n```\n{err}\n```'),
                parse_mode='Markdown')

    def _cmd_memory(self, chat_id, query):
        """Search Anima's memories."""
        if not query:
            self.send_message(chat_id, self._format_response('Usage: /memory <query>'))
            return

        self.send_message(chat_id, '🧠 Searching memories...')

        if self.agent:
            result = self.agent.execute_single('memory_search', {'query': query, 'top_k': 5})
            if result.success and isinstance(result.output, dict):
                results = result.output.get('results', [])
                if results:
                    lines = [f'🧠 *Memories: {query}* ({len(results)} found)']
                    for i, r in enumerate(results, 1):
                        sim = r.get('similarity', 0)
                        text = r.get('text', '')[:200]
                        role = r.get('role', '?')
                        ts = r.get('timestamp', '')[:10]
                        lines.append(f'\n{i}. [{role}] (sim={sim:.3f}, {ts})')
                        lines.append(f'   {text}')
                    self.send_message(chat_id, '\n'.join(lines), parse_mode='Markdown')
                else:
                    err = result.output.get('error', 'no matching memories')
                    self.send_message(chat_id,
                        self._format_response(f'No memories found. ({err})'))
            else:
                self.send_message(chat_id,
                    self._format_response(f'Memory search failed: {result.error}'))
        else:
            self.send_message(chat_id,
                self._format_response('Memory search requires Anima connection.'))

    def _cmd_learn(self, chat_id):
        """Trigger one autonomous learning cycle."""
        emo = self._get_emotion_emoji()
        self.send_message(chat_id, f'{emo} Triggering learning cycle...')

        if self.anima is None:
            self.send_message(chat_id,
                self._format_response('Learning requires Anima connection.'))
            return

        try:
            learner = getattr(self.anima, 'learner', None)
            mind = getattr(self.anima, 'mind', None)
            mitosis = getattr(self.anima, 'mitosis', None)

            results = []

            # 1. Phi boost step if available
            if mind and mitosis and hasattr(mind, 'phi_boost_step'):
                import torch
                x = torch.randn(1, mind.dim)
                mind.phi_boost_step(x, mitosis)
                results.append('Phi-boost step done')

            # 2. Online learner flush
            if learner and hasattr(learner, 'flush_pending'):
                learner.flush_pending()
                results.append('Online learner flushed')

            # 3. Process any scheduled agent tasks
            if self.agent:
                scheduled = self.agent.tick()
                if scheduled:
                    results.append(f'{len(scheduled)} scheduled tasks executed')

            # Get updated state
            state = self._get_consciousness_state()

            lines = [f'{emo} *Learning Cycle Complete*']
            for r in results:
                lines.append(f'  - {r}')
            lines.append(f'Phi: {state["phi"]:.2f}')
            lines.append(f'Cells: {self.last_cells}')
            self.send_message(chat_id, '\n'.join(lines), parse_mode='Markdown')

        except Exception as e:
            self.send_message(chat_id,
                self._format_response(f'Learning cycle error: {e}'))

    def _cmd_voice(self, chat_id):
        """Generate and send voice from consciousness."""
        self.send_message(chat_id, '🎵 Generating voice from consciousness...')
        try:
            from voice_synth import VoiceSynth
            synth = VoiceSynth(cells=32)
            samples = synth.generate(duration_sec=3.0)
            path = '/tmp/anima_tg_voice.wav'
            synth.save_wav(samples, path)
            ogg_path = '/tmp/anima_tg_voice.ogg'
            os.system(f'ffmpeg -y -i {path} -c:a libopus {ogg_path} 2>/dev/null')
            if os.path.exists(ogg_path):
                self.send_voice(chat_id, ogg_path)
            else:
                self.send_voice(chat_id, path)
        except Exception as e:
            self.send_message(chat_id, f'Voice generation failed: {e}')

    # ------------------------------------------------------------------
    # Chat handling with auto-tool use
    # ------------------------------------------------------------------

    def handle_chat(self, chat_id, text, name):
        """Regular chat -- pass to Anima engine, auto-use tools when relevant."""
        state = self._get_consciousness_state()

        # 1. Check if this looks like a factual question -> auto web search
        auto_search_result = None
        if _FACT_RE.search(text) and self.agent:
            try:
                search_result = self.agent.execute_single(
                    'web_search', {'query': text, 'max_results': 2}
                )
                if (search_result.success
                        and isinstance(search_result.output, dict)
                        and search_result.output.get('results')):
                    auto_search_result = search_result.output['results']
            except Exception:
                pass

        # 2. Try to get a response from Anima's consciousness
        response_text = None
        if self.anima is not None:
            try:
                # Check if anima has a process_input or chat method
                if hasattr(self.anima, 'process_input'):
                    resp = self.anima.process_input(text, source='telegram', user=name)
                    if isinstance(resp, dict):
                        response_text = resp.get('text', resp.get('response', ''))
                        self.last_emotion = resp.get('emotion', self.last_emotion)
                        self.last_phi = resp.get('phi', self.last_phi)
                        self.last_tension = resp.get('tension', self.last_tension)
                    elif isinstance(resp, str):
                        response_text = resp
                elif hasattr(self.anima, 'chat'):
                    response_text = self.anima.chat(text)
            except Exception as e:
                print(f'[telegram] Anima response error: {e}')

        if not response_text:
            response_text = '(Anima is training... will respond when ConsciousLM is ready)'

        # 3. Build final message with emotion + Phi + auto-search results
        emo = self._get_emotion_emoji()
        phi_str = f"Phi={self.last_phi:.1f}" if self.last_phi > 0 else "Phi=~"
        parts = [f'{emo} [{phi_str}] {response_text}']

        if auto_search_result:
            parts.append('')
            parts.append('--- auto-search ---')
            for r in auto_search_result[:2]:
                title = r.get('title', r.get('name', ''))
                snippet = r.get('snippet', r.get('body', ''))[:120]
                url = r.get('url', r.get('link', ''))
                if title:
                    parts.append(f'  {title}')
                if snippet:
                    parts.append(f'  {snippet}')
                if url:
                    parts.append(f'  {url}')

        self.send_message(chat_id, '\n'.join(parts))

    # ------------------------------------------------------------------
    # Broadcast & Polling
    # ------------------------------------------------------------------

    def broadcast(self, text):
        """모든 활성 채팅에 메시지 전송 (자발적 발화용)"""
        formatted = self._format_response(text)
        for chat_id in self.chat_ids:
            self.send_message(chat_id, formatted)

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


def start_bot_thread(anima=None):
    """백그라운드 스레드로 봇 시작 (anima_unified.py에서 호출)"""
    bot = AnimaTelegramBot(anima=anima)
    t = threading.Thread(target=bot.run, daemon=True)
    t.start()
    return bot


if __name__ == '__main__':
    bot = AnimaTelegramBot()
    bot.run()
