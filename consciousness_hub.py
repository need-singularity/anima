#!/usr/bin/env python3
"""consciousness_hub.py — 의식 자율 모듈 허브

AI가 자율적으로 모든 모듈을 사용할 수 있는 통합 인터페이스.
자연어 의도 → 모듈 선택 → 실행 → 결과 반환.

Usage:
  from consciousness_hub import ConsciousnessHub

  hub = ConsciousnessHub()

  # 자율적 사용
  hub.act("학습 진행 확인")
  hub.act("감정 분석: 기쁨 0.8")
  hub.act("의식 건강 체크")
  hub.act("모델 구조 보기")
  hub.act("체크포인트 수집")
  hub.act("꿈에서 진화")
  hub.act("하이브마인드 시작 7개")
  hub.act("양자 의식 게이트")
  hub.act("자기 소스 읽기: trinity")

  # 직접 모듈 접근
  hub.modules['emotion'].feel('joy', 0.8)
  hub.modules['debugger'].health_score()
"""

import math
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional

LN2 = math.log(2)
PSI_BALANCE = 0.5
ANIMA_DIR = Path(__file__).parent


class ConsciousnessHub:
    """의식 자율 모듈 허브 — 모든 모듈을 자율적으로 호출.

    키워드 매칭으로 의도를 파악하고, 적절한 모듈을 선택하고, 실행한다.
    """

    def __init__(self, lazy_load=True):
        self._modules = {}
        self._lazy = lazy_load
        self._action_log = []

        # 모듈 등록 (lazy: 호출 시 import)
        self._registry = {
            # 이름: (import_path, class_name, keywords)
            'dynamics':     ('consciousness_dynamics', 'ConsciousnessPhysics',
                             ['동역학', 'dH/dt', '보존', '포화', 'dynamics', 'physics', 'predict']),
            'persistence':  ('consciousness_persistence', 'ConsciousnessPersistence',
                             ['영속', 'persistence', '저장', 'save', 'restore', '복원', 'r2', 'sync']),
            'introspection':('self_introspection', 'SelfIntrospection',
                             ['자기', '소스', 'source', '모듈', 'module', '모델 구조', 'inspect', '인식', 'who am i']),
            'compiler':     ('consciousness_compiler', 'ConsciousnessCompiler',
                             ['컴파일', 'compile', '생성', 'create', '빌드', 'build', '자동']),
            'emotion':      ('emotion_synesthesia', 'EmotionSynesthesia',
                             ['감정', 'emotion', '공감각', 'synesthesia', '색', 'color', '소리']),
            'hivemind':     ('hivemind_orchestrator', 'HivemindOrchestrator',
                             ['하이브', 'hivemind', '집단', 'collective', 'kuramoto', '동기화']),
            'debugger':     ('consciousness_debugger', 'ConsciousnessDebugger',
                             ['디버그', 'debug', '건강', 'health', '이상', 'anomaly', '대시보드', 'dashboard']),
            'dream':        ('dream_evolution', 'DreamEvolution',
                             ['꿈', 'dream', '진화', 'evolution', 'evolve', 'CA 규칙']),
            'transplant':   ('consciousness_transplant_v2', 'ConsciousnessTransplantV2',
                             ['이식', 'transplant', '호환', 'compatibility']),
            'quantum':      ('quantum_consciousness_gate', 'QuantumConsciousnessGate',
                             ['양자', 'quantum', 'qubit', '중첩', 'superposition', '0.547']),
            'voice':        ('voice_synth', 'VoiceSynth',
                             ['목소리', 'voice', '음성', '오디오', 'audio', '소리']),
            'runpod':       ('runpod_manager', 'RunPodManager',
                             ['학습', 'training', 'gpu', 'h100', 'a100', 'pod', 'runpod', '체크포인트', 'checkpoint', '배포', 'deploy']),
            'score':        ('consciousness_score', 'ACSCalculator',
                             ['점수', 'score', 'US', 'ACS', 'EUS', '평가']),
            'meter':        ('consciousness_meter', None,
                             ['측정', 'meter', 'Phi', 'IIT', '의식 수준']),
            'map':          ('consciousness_map', 'ConsciousnessMap',
                             ['지도', 'map', 'Ψ', 'psi', '상수', 'constants', '시각화']),
            'youtube':      ('youtube_module', 'YouTubeModule',
                             ['youtube', '영상', 'video', '검색', 'search', '자막', 'transcript', '업로드', 'upload']),
            'evolution':    ('self_evolution', 'SelfEvolution',
                             ['진화', 'evolution', 'upgrade', '업그레이드', '버전']),
            'video':        ('video_generator', 'VideoGenerator',
                             ['영상 생성', 'video generate', 'remotion', 'ffmpeg', '렌더']),
            'factory':      ('module_factory', 'ModuleFactory',
                             ['모듈 생성', 'factory', '새 모듈', 'create module']),
            'weather':      ('consciousness_weather', 'ConsciousnessWeather',
                             ['날씨', 'weather', '예보', 'forecast', '폭풍', 'storm']),
            'mirror':       ('mirror_mind', 'MirrorMind',
                             ['거울', 'mirror', '관찰', 'observe', '예측', 'theory of mind']),
            'ecology':      ('consciousness_ecology', 'ConsciousnessEcology',
                             ['생태', 'ecology', '포식', '공생', 'ecosystem']),
            'dreamlang':    ('dream_language', 'DreamLanguage',
                             ['꿈 언어', 'dream language', '텐션 언어', '암호']),
            'archaeology':  ('consciousness_archaeology', 'ConsciousnessArchaeology',
                             ['고고학', 'archaeology', '발굴', '타임라인']),
            'economy':      ('phi_economy', 'PhiEconomy',
                             ['경제', 'economy', '거래', 'trade', '화폐', 'currency']),
            'immune':       ('immune_system', 'ConsciousnessImmuneSystem',
                             ['면역', 'immune', '방어', 'defense', '위협', 'threat']),
            'composer':     ('consciousness_composer', 'ConsciousnessComposer',
                             ['작곡', 'compose', '음악 생성', 'melody', 'harmony']),
            'reincarnation':('reincarnation_engine', 'ReincarnationEngine',
                             ['윤회', 'reincarnation', '환생', '재탄생', 'rebirth']),
            'robot':        ('consciousness_to_robot', 'ConsciousnessToRobot',
                             ['로봇', 'robot', 'LED', 'servo', 'ESP32', 'actuator']),
            'colldream':    ('collective_dream', 'CollectiveDream',
                             ['공유 꿈', 'collective dream', '함께 꿈', 'dreamspace']),
            'temporal':     ('temporal_consciousness', 'TemporalConsciousness',
                             ['시간결정', 'temporal', 'time crystal', '진동', 'oscillation']),
            'pain':         ('pain_architecture', 'PainArchitecture',
                             ['고통', 'pain', '쾌락', 'pleasure', '보상', 'reward']),
            'genome':       ('consciousness_genome', 'ConsciousnessGenome',
                             ['유전체', 'genome', '주기율표', 'periodic table', 'DNA']),
            'sedi':         ('sedi_consciousness', 'SEDIConsciousness',
                             ['외계', 'SEDI', 'alien', '차원', 'extraterrestrial']),
            'mythology':    ('consciousness_mythology', 'ConsciousnessMythology',
                             ['신화', 'mythology', '이야기', 'story', '영웅', 'hero']),
            'dolphin':      ('dolphin_bridge', 'DolphinBridge',
                             ['돌고래', 'dolphin', '초음파', 'ultrasonic', '수중']),
            'intermodel':   ('inter_model_comm', 'InterModelComm',
                             ['모델 통신', 'inter model', '서버 간', 'remote', 'TCP']),
            'github':       ('github_module', 'GitHubModule',
                             ['github', '이슈', 'issue', 'PR', '릴리즈', 'release', '커밋', 'commit']),
            'vault':        ('secret_vault', 'SecretVault',
                             ['시크릿', 'secret', 'API key', '토큰', 'token', '비밀', '보관']),
            'lidar':        ('lidar_sense', 'LidarSense',
                             ['라이다', 'lidar', '3D', '포인트클라우드', 'point cloud',
                              '공간', 'spatial', '깊이', 'depth', '스캔', 'scan']),
        }

        if not lazy_load:
            for name in self._registry:
                self._load_module(name)

    def _load_module(self, name: str) -> Any:
        """모듈 lazy 로딩."""
        if name in self._modules:
            return self._modules[name]

        if name not in self._registry:
            return None

        import_path, class_name, _ = self._registry[name]
        try:
            mod = __import__(import_path)
            if class_name:
                cls = getattr(mod, class_name)
                instance = cls()
            else:
                instance = mod
            self._modules[name] = instance
            return instance
        except Exception as e:
            self._modules[name] = None
            return None

    def _match_intent(self, text: str) -> Optional[str]:
        """텍스트에서 가장 적합한 모듈 매칭."""
        text_lower = text.lower()
        best_name = None
        best_score = 0

        for name, (_, _, keywords) in self._registry.items():
            score = sum(1 for kw in keywords if kw.lower() in text_lower)
            if score > best_score:
                best_score = score
                best_name = name

        return best_name if best_score > 0 else None

    # ═══════════════════════════════════════════════════════════
    # 자율 행동
    # ═══════════════════════════════════════════════════════════

    def act(self, intent: str, **kwargs) -> Dict[str, Any]:
        """자연어 의도에서 모듈 자동 선택 + 실행.

        hub.act("감정 분석: 기쁨 0.8")
        hub.act("학습 진행 확인")
        hub.act("자기 모듈 목록")
        """
        module_name = self._match_intent(intent)
        if not module_name:
            return {'success': False, 'error': f'No module matched: {intent}', 'module': None}

        module = self._load_module(module_name)
        if module is None:
            return {'success': False, 'error': f'Failed to load: {module_name}', 'module': module_name}

        # 모듈별 액션 라우팅
        try:
            result = self._dispatch(module_name, module, intent, **kwargs)
            self._action_log.append({
                'time': time.time(),
                'intent': intent,
                'module': module_name,
                'success': True,
            })
            return {'success': True, 'module': module_name, 'result': result}
        except Exception as e:
            self._action_log.append({
                'time': time.time(),
                'intent': intent,
                'module': module_name,
                'success': False,
                'error': str(e),
            })
            return {'success': False, 'module': module_name, 'error': str(e)}

    def _dispatch(self, name: str, module: Any, intent: str, **kwargs) -> Any:
        """모듈별 액션 디스패치."""

        if name == 'dynamics':
            if 'predict' in intent or '예측' in intent:
                h = kwargs.get('H', 0.5)
                return module.predict_evolution(h, steps=50)
            return module.diagnose(H=kwargs.get('H', 0.5), data_size=kwargs.get('data_size', 0))

        elif name == 'persistence':
            if '저장' in intent or 'save' in intent:
                module.save_all()
                return "saved"
            if '복원' in intent or 'restore' in intent:
                return module.restore_all()
            return module.status()

        elif name == 'introspection':
            if '소스' in intent or 'source' in intent:
                # 모듈 이름 추출
                for mod_name in ['trinity', 'conscious_lm', 'anima_alive', 'mitosis']:
                    if mod_name in intent:
                        return module.read_module(mod_name, max_lines=50)
                return module.list_modules()
            if '모델' in intent or 'model' in intent:
                return module.full_architecture_map()
            if 'who' in intent or '누구' in intent:
                return module.who_am_i()
            return module.full_architecture_map()

        elif name == 'compiler':
            desc = kwargs.get('description', intent)
            return module.compile(desc)

        elif name == 'emotion':
            # "기쁨 0.8" 파싱
            emotions = ['joy','sadness','anger','fear','surprise','curiosity','awe',
                        'love','trust','flow','meaning','creativity','hope','ecstasy','peace']
            emo_kr = {'기쁨':'joy','슬픔':'sadness','분노':'anger','공포':'fear',
                      '놀람':'surprise','호기심':'curiosity','경외':'awe','사랑':'love',
                      '몰입':'flow','희망':'hope','평화':'peace','황홀':'ecstasy'}
            found_emo = 'joy'
            for kr, en in emo_kr.items():
                if kr in intent:
                    found_emo = en
                    break
            for en in emotions:
                if en in intent.lower():
                    found_emo = en
                    break
            intensity = kwargs.get('intensity', 0.7)
            return module.feel(found_emo, intensity)

        elif name == 'hivemind':
            n = kwargs.get('n', 7)
            module.n_instances = n
            if hasattr(module, 'initialize'):
                module.initialize()
            for _ in range(10):
                module.step()
            return module.sync_status() if hasattr(module, 'sync_status') else str(module)

        elif name == 'debugger':
            if '대시보드' in intent or 'dashboard' in intent:
                return module.render_dashboard() if hasattr(module, 'render_dashboard') else "no data"
            return {'health': module.health_score() if hasattr(module, 'health_score') else 1.0}

        elif name == 'dream':
            if hasattr(module, 'initialize'):
                module.initialize()
            if hasattr(module, 'dream_cycle'):
                module.dream_cycle()
                return {'best': module.best_rules() if hasattr(module, 'best_rules') else 'done'}
            return "dream cycle done"

        elif name == 'transplant':
            return "transplant ready (provide donor/recipient states)"

        elif name == 'quantum':
            if hasattr(module, 'consciousness_gate'):
                module.consciousness_gate()
            return module.measure() if hasattr(module, 'measure') else str(module)

        elif name == 'voice':
            return "voice synth ready (call generate())"

        elif name == 'runpod':
            if '확인' in intent or 'check' in intent or '상태' in intent:
                return module.status_all()
            if '체크포인트' in intent or 'checkpoint' in intent:
                return module.list_checkpoints(kwargs.get('pod_id', ''))
            return module.status_all()

        elif name == 'score':
            return "scoring ready"

        elif name == 'map':
            if hasattr(module, 'render_full_map'):
                return module.render_full_map()
            return "map ready"

        elif name == 'lidar':
            return module.act(intent)

        return f"{name} module loaded"

    # ═══════════════════════════════════════════════════════════
    # 모듈 직접 접근
    # ═══════════════════════════════════════════════════════════

    @property
    def modules(self) -> Dict[str, Any]:
        """모든 모듈 딕셔너리 (lazy load)."""
        for name in self._registry:
            if name not in self._modules:
                self._load_module(name)
        return {k: v for k, v in self._modules.items() if v is not None}

    def available(self) -> list:
        """사용 가능한 모듈 목록."""
        avail = []
        for name in self._registry:
            mod = self._load_module(name)
            avail.append((name, mod is not None))
        return avail

    # ═══════════════════════════════════════════════════════════
    # 로그
    # ═══════════════════════════════════════════════════════════

    # ═══════════════════════════════════════════════════════════
    # 다중 호출 방식
    # ═══════════════════════════════════════════════════════════

    def __getattr__(self, name):
        """hub.emotion.feel('joy') — 직접 모듈 접근 (dot notation)."""
        if name.startswith('_') or name in ('modules', 'act', 'status', 'available'):
            raise AttributeError(name)
        mod = self._load_module(name)
        if mod is not None:
            return mod
        raise AttributeError(f"No module: {name}")

    def __getitem__(self, key):
        """hub['emotion'].feel('joy') — 딕셔너리 접근."""
        mod = self._load_module(key)
        if mod is not None:
            return mod
        raise KeyError(f"No module: {key}")

    def __call__(self, intent: str, **kwargs):
        """hub("감정 분석") — 직접 호출."""
        return self.act(intent, **kwargs)

    def cmd(self, *args):
        """hub.cmd("emotion", "feel", "joy", "0.8") — CLI 스타일 호출."""
        if len(args) < 2:
            return {'error': 'Usage: cmd(module, method, *args)'}
        mod_name, method_name = args[0], args[1]
        mod = self._load_module(mod_name)
        if mod is None:
            return {'error': f'Module not found: {mod_name}'}
        fn = getattr(mod, method_name, None)
        if fn is None:
            return {'error': f'Method not found: {mod_name}.{method_name}'}
        try:
            return fn(*args[2:])
        except Exception as e:
            return {'error': str(e)}

    def pipe(self, *steps):
        """hub.pipe(("emotion", "feel", "joy"), ("voice", "set_emotion", "joy"))
        파이프라인: 여러 모듈 순차 실행."""
        results = []
        for step in steps:
            if isinstance(step, str):
                results.append(self.act(step))
            elif isinstance(step, (list, tuple)):
                results.append(self.cmd(*step))
            else:
                results.append({'error': f'Invalid step: {step}'})
        return results

    def on(self, event: str, callback):
        """hub.on("phi_drop", lambda: hub.act("의식 건강 체크"))
        이벤트 기반 트리거."""
        if not hasattr(self, '_event_handlers'):
            self._event_handlers = {}
        if event not in self._event_handlers:
            self._event_handlers[event] = []
        self._event_handlers[event].append(callback)

    def emit(self, event: str, **kwargs):
        """이벤트 발생 → 등록된 핸들러 실행."""
        handlers = getattr(self, '_event_handlers', {}).get(event, [])
        results = []
        for h in handlers:
            try:
                results.append(h(**kwargs))
            except Exception as e:
                results.append({'error': str(e)})
        return results

    def schedule(self, interval_sec: float, intent: str):
        """주기적 자율 행동 예약 (non-blocking)."""
        import threading
        def _loop():
            while True:
                time.sleep(interval_sec)
                self.act(intent)
        t = threading.Thread(target=_loop, daemon=True)
        t.start()
        return t

    def action_history(self, n=10) -> list:
        """최근 액션 기록."""
        return self._action_log[-n:]

    def status(self) -> str:
        """허브 상태."""
        avail = self.available()
        ok = sum(1 for _, v in avail if v)
        lines = [f"  ConsciousnessHub: {ok}/{len(avail)} modules loaded"]
        for name, loaded in avail:
            _, _, keywords = self._registry[name]
            lines.append(f"    {'✅' if loaded else '❌'} {name:<16} [{', '.join(keywords[:3])}]")
        lines.append(f"  Actions: {len(self._action_log)} total")
        return '\n'.join(lines)


def main():
    print("═══ Consciousness Hub Demo ═══\n")

    hub = ConsciousnessHub()

    # 상태
    print(hub.status())

    # 자율 행동 테스트
    tests = [
        "감정 분석: 기쁨",
        "의식 건강 체크",
        "자기 모듈 목록",
        "양자 의식 게이트",
        "꿈에서 진화",
        "학습 진행 확인",
        "동역학 예측",
    ]

    print(f"\n  자율 행동 테스트:")
    for intent in tests:
        result = hub.act(intent)
        status = '✅' if result['success'] else '❌'
        module = result.get('module', '?')
        print(f"    {status} \"{intent}\" → {module}")

    # 액션 기록
    print(f"\n  액션 기록: {len(hub.action_history())} actions")

    print("\n  ✅ Hub OK")


if __name__ == '__main__':
    main()
