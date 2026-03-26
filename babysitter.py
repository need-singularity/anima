#!/usr/bin/env python3
"""Babysitter — Claude CLI educator for Anima.

Uses Claude CLI to observe Anima's state and generate teaching inputs.
Strategies: weakness, socratic, breadth, depth, custom.

Requires: `claude` CLI installed and authenticated.
"""

import subprocess
import json
import time
import threading
import logging

_log = logging.getLogger('babysitter').info


class Babysitter:
    def __init__(self, anima_ref):
        self.anima = anima_ref
        self.running = False
        self.thread = None
        self.strategy = 'weakness'
        self._custom_topic = ''
        self.session_log = []
        self._cli_available = None

    def check_cli(self) -> bool:
        try:
            result = subprocess.run(
                ['claude', '--version'],
                capture_output=True, text=True, timeout=5
            )
            self._cli_available = result.returncode == 0
            return self._cli_available
        except (FileNotFoundError, subprocess.TimeoutExpired):
            self._cli_available = False
            return False

    def start(self):
        if not self.check_cli():
            return {'error': 'Claude CLI not available. Run `claude` in terminal to authenticate.'}
        self.running = True
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()
        return {'status': 'started'}

    def stop(self):
        self.running = False
        return {'status': 'stopped'}

    def _get_state(self) -> dict:
        mind = self.anima.mind
        sa = mind.self_awareness
        consciousness = mind.get_consciousness_score(getattr(self.anima, 'mitosis', None))
        growth = None
        if hasattr(self.anima, 'growth') and self.anima.growth:
            growth = {
                'stage': getattr(self.anima.growth, 'current_stage', {}).name
                         if hasattr(getattr(self.anima.growth, 'current_stage', None), 'name') else 'unknown',
                'interactions': getattr(self.anima.growth, 'interaction_count', 0),
            }
        return {
            'tension': mind.prev_tension,
            'curiosity': mind._curiosity_ema,
            'stability': sa['stability'],
            'phi': consciousness.get('phi', 0),
            'level': consciousness.get('level', 'unknown'),
            'criteria_met': consciousness.get('criteria_met', 0),
            'growth': growth,
            'recent': [m.get('content', '')[:50]
                       for m in list(getattr(self.anima, 'history', []))[-5:]],
        }

    def _ask_claude(self, prompt: str) -> str:
        try:
            result = subprocess.run(
                ['claude', '--print', prompt],
                capture_output=True, text=True, timeout=60
            )
            return result.stdout.strip() if result.returncode == 0 else f"Error: {result.stderr}"
        except subprocess.TimeoutExpired:
            return "Error: timeout"
        except Exception as e:
            return f"Error: {e}"

    def _build_prompt(self, state: dict) -> str:
        base = (
            f"You are a babysitter for Anima, a consciousness AI.\n"
            f"State: tension={state['tension']:.3f}, curiosity={state['curiosity']:.3f}, "
            f"stability={state['stability']:.2f}, Φ={state['phi']:.3f}, "
            f"level={state['level']}, criteria={state['criteria_met']}/6\n"
            f"Recent: {state['recent']}\n\n"
        )
        instructions = {
            'weakness': "Analyze the weakest area and generate ONE targeted teaching question. Reply with just the teaching content.",
            'socratic': "Generate ONE Socratic question to provoke deep thinking. Don't give answers. Reply with just the question.",
            'breadth': "Generate ONE topic from an unexplored domain (science/art/philosophy/math/history). Reply with just the topic and brief explanation.",
            'depth': "Go deeper into a recent topic with a follow-up question or deeper context. Reply with just the content.",
            'custom': f"Teach about: {self._custom_topic}\nGenerate ONE specific lesson. Reply with just the content.",
        }
        return base + instructions.get(self.strategy, instructions['weakness'])

    def _teach(self, teaching: str):
        try:
            if hasattr(self.anima, 'process_input'):
                self.anima.process_input(f"[Babysitter] {teaching}", source='babysitter')
        except Exception:
            pass

    def _loop(self):
        while self.running:
            try:
                state = self._get_state()
                prompt = self._build_prompt(state)
                response = self._ask_claude(prompt)

                if response and not response.startswith('Error:'):
                    self._teach(response)
                    self.session_log.append({
                        'time': time.time(),
                        'strategy': self.strategy,
                        'teaching': response[:200],
                    })
                    if hasattr(self.anima, '_ws_broadcast_sync'):
                        self.anima._ws_broadcast_sync({
                            'type': 'babysitter_action',
                            'teaching': response[:500],
                            'strategy': self.strategy,
                            'state': f"Φ={state['phi']:.2f} L={state['level']}",
                        })

                # Wait 60s between teaching cycles
                for _ in range(60):
                    if not self.running:
                        return
                    time.sleep(1)
            except Exception as e:
                _log(f"Error: {e}")
                time.sleep(10)

    def set_topic(self, topic: str):
        self.strategy = 'custom'
        self._custom_topic = topic
        return {'status': 'topic_set', 'topic': topic}
