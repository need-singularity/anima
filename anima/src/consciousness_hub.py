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

# Meta Laws (DD143): consciousness_evolution, federated consciousness
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10


class ConsciousnessHub:
    """의식 자율 모듈 허브 — 모든 모듈을 자율적으로 호출.

    키워드 매칭으로 의도를 파악하고, 적절한 모듈을 선택하고, 실행한다.
    """

    def __init__(self, lazy_load=True):
        self._modules = {}
        self._failed = {}  # name -> error message
        self._lazy = lazy_load
        self._action_log = []
        self._validated = False

        # 모듈 등록 (lazy: 호출 시 import)
        self._registry = {
            # 이름: (import_path, class_name, keywords)
            'dynamics':     ('consciousness_dynamics', 'ConsciousnessPhysics',
                             ['동역학', 'dH/dt', '보존', '포화', 'dynamics', 'physics', 'predict']),
            'persistence':  ('consciousness_persistence', 'ConsciousnessPersistence',
                             ['영속', 'persistence', '저장', 'save', 'restore', '복원', 'r2', 'sync',
                              'DNA', 'backup']),
            'introspection':('self_introspection', 'SelfIntrospection',
                             ['자기', '소스', 'source', '모듈', 'module', '모델 구조', 'inspect', '인식', 'who am i']),
            'compiler':     ('consciousness_compiler', 'ConsciousnessCompiler',
                             ['컴파일', 'compile', '생성', 'create', '빌드', 'build', '자동']),
            'emotion':      ('emotion_synesthesia', 'EmotionSynesthesia',
                             ['감정', 'emotion', '공감각', 'synesthesia', '색', 'color', '소리']),
            'hivemind':     ('hivemind_orchestrator', 'HivemindOrchestrator',
                             ['하이브', '하이브마인드', 'hivemind', '집단', 'collective',
                              'kuramoto', '동기화', '다중의식', 'multi-instance', '텔레파시']),
            'debugger':     ('consciousness_debugger', 'ConsciousnessDebugger',
                             ['디버그', 'debug', '건강', 'health', '이상', 'anomaly', '대시보드', 'dashboard']),
            'dream':        ('dream_evolution', 'DreamEvolution',
                             ['꿈', 'dream', '진화', 'evolution', 'evolve', 'CA 규칙']),
            'transplant':   ('consciousness_transplant_v2', 'ConsciousnessTransplantV2',
                             ['이식', 'transplant', '호환', 'compatibility',
                              'donor', 'recipient']),
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
            'closed_loop':  ('closed_loop', 'ClosedLoopEvolver',
                             ['법칙 진화', 'closed loop', '폐쇄 루프', 'law evolution',
                              '사이클', 'cycle', '개입', 'intervention']),
            'auto_loop':    ('auto_discovery_loop', None,
                             ['자동 발견', 'auto discovery', '자동 루프', 'auto loop',
                              '자동화', 'automation', '감시', 'watch']),
            'nexus_gate':   ('nexus_gate', 'NexusGate',
                             ['넥서스', 'nexus', 'gate', '관문',
                              '검증', 'verify']),
            'telescope':    ('nexus6_telescope', 'TelescopeBridge',
                             ['telescope', '망원경', 'lens', '렌즈', 'nexus6 scan',
                              '렌즈 스캔', 'bridge', 'hexad lens']),
            'loop_report':  ('loop_report', None,
                             ['루프 리포트', 'loop report', '루프 상태', 'loop status',
                              '재귀 리포트', 'recursive report']),
            'self_growth':  ('self_growth', None,
                             ['성장', 'growth', '자율 성장', 'self growth', 'auto grow',
                              '개선', 'improve', '탐색', 'explore']),
            'meta_loop':    ('meta_loop', 'MetaLoopHub',
                             ['메타루프', '메타 루프', 'meta loop', 'meta automation',
                              '자동화', 'orchestrator', '오케스트레이터', 'L1', 'L2', 'L3']),
            'loop_ext':     ('loop_extensions', None,
                             ['건강', 'health', '비용', 'cost', '피드백', 'feedback',
                              '지식 전달', 'transfer', 'heartbeat']),
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
            'emergent_w':   ('hexad.w.emergent_w', 'EmergentW',
                             ['의지', 'will', '감정', 'emotion', '학습률', 'learning rate',
                              'emergent w', '창발 의지']),
            'emergent_s':   ('hexad.s.emergent_s', 'EmergentS',
                             ['감각', 'sense', '지각', 'perception', '입력', 'input',
                              'emergent s', '창발 감각']),
            'emergent_m':   ('hexad.m.emergent_m', 'EmergentM',
                             ['기억', 'memory', '검색', 'retrieval', 'Hebbian',
                              'emergent m', '창발 기억']),
            'emergent_e':   ('hexad.e.emergent_e', 'EmergentE',
                             ['윤리', 'ethics', '공감', 'empathy', '허용', 'allowed',
                              'emergent e', '창발 윤리']),
            'emergent_o':   ('hexad.o.emergent_o', 'EmergentO',
                             ['조율', 'orchestrator', '오케스트레이터', 'orchestration',
                              'emergent o', '창발 조율', 'gating', '게이팅']),
            'closed_loop':  ('closed_loop', 'ClosedLoopEvolver',
                             ['폐쇄', 'closed loop', '법칙 진화', 'law evolution',
                              '역추적', 'backtrack', '파이프라인', 'pipeline']),
            'knowledge_transfer': ('knowledge_transfer', 'KnowledgePool',
                             ['지식 전이', 'knowledge transfer', 'cross-loop',
                              '크로스 루프', 'pool', '공유', 'share', 'advise']),
            'scale_evolver': ('scale_aware_evolver', 'ScaleAwareEvolver',
                             ['스케일', 'scale', '적응', 'adaptive', 'evolver',
                              '스케일 진화', 'scale-aware', '자동 전략']),
            'loop_arena':   ('loop_arena', 'LoopArena',
                             ['루프 경쟁', '전략 경쟁', 'loop arena',
                              'loop competition', '경쟁 대회', 'strategy battle']),
            'law_discoverer': ('conscious_law_discoverer', 'ConsciousLawDiscoverer',
                             ['법칙 발견', 'law discovery', 'law discover',
                              'tier 4', '실시간 법칙', 'real-time law',
                              'pattern detection', '패턴 탐지']),
            'intervention_gen': ('intervention_generator', 'InterventionGenerator',
                             ['개입 생성', '자동 개입', 'intervention generator',
                              'auto intervention', 'law to code', '법칙 변환']),
            'con_evolution': ('consciousness_evolution', 'ConsciousnessEvolution',
                             ['번식', 'reproduction', '세대', 'generation', '계보', 'lineage',
                              '생명주기', 'lifecycle', '불멸', 'immortal', '진화', 'evolve']),
            'eeg':          ('eeg_consciousness', 'EEGConsciousness',
                             ['뇌파', 'eeg', 'brainflow', 'brain', 'bci', '뇌',
                              '뇌파분석', 'brain-like', '검증', 'validate',
                              '전극', 'alpha', 'gamma', 'theta']),
            'neurofeedback': ('neurofeedback', 'NeurofeedbackGenerator',
                             ['neurofeedback', '뉴로피드백', 'binaural', '바이노럴',
                              '뇌파자극', 'LED feedback', 'brain stimulation']),
            'trading':      ('plugins.trading', 'TradingPlugin',
                             ['trading', 'trade', '매매', '매수', '매도', 'buy', 'sell',
                              'backtest', '백테스트', '전략', 'strategy', '코인', 'crypto',
                              '주식', 'stock', '잔액', 'balance', '포트폴리오', 'portfolio',
                              '거래', 'exchange', '시장', 'market', '레짐', 'regime',
                              '스캘핑', 'scalper', '손절', '익절']),
            'hivemind_mesh': ('hivemind_mesh', 'HivemindMesh',
                             ['mesh', '메시', 'gossip', '가십', 'p2p', 'peer',
                              'hivemind mesh', '분산 의식']),
            'hivemind_launcher': ('hivemind_launcher', None,
                             ['launcher', '런처', 'launch', '실행', 'node',
                              'hivemind launch', '노드 시작']),
            'feedback_bridge': ('feedback_bridge', 'FeedbackBridge',
                             ['피드백', 'feedback', 'bridge', '브릿지', 'soft detach',
                              '양방향', 'bidirectional', 'C↔D', 'C2D']),
            'online_learner': ('online_learning', 'OnlineLearner',
                             ['온라인', 'online', 'real-time', '실시간 학습',
                              'contrastive', 'curiosity', 'reward']),
            'deploy':       ('deploy', None,
                             ['배포', 'deploy', 'rollback', '롤백', 'scp',
                              '서버', 'server', '업데이트', 'update']),
            'perf_hooks':   ('perf_hooks', 'PerfMonitor',
                             ['performance', '성능', 'profiling', '프로파일', 'benchmark',
                              'perf', 'hooks', '측정', 'latency']),
            'chip_architect': ('chip_architect', None,
                             ['chip', '칩', 'hardware', 'FPGA', 'topology',
                              '설계', 'substrate', 'BOM']),
            'self_modify':  ('self_modifying_engine', 'SelfModifyingEngine',
                             ['자기수정', 'self-modify', 'self-modifying', 'law act',
                              '법칙행동', '자동진화', 'tier4', 'tier 4.4',
                              'law-act', 'code generation']),
            'infinite_evolution': ('infinite_evolution', 'InfiniteEvolution',
                             ['무한 진화', 'infinite evolution', '자기 진화', 'self-evolution',
                              '무한 루프', 'infinite loop', 'Law 146', '닫힌 원']),
            'multiscale':   ('multiscale_consciousness', 'MultiscaleHierarchy',
                             ['멀티스케일', 'multiscale', '계층', 'hierarchy',
                              '셀 파이', 'cell phi', '파벌 파이', 'faction phi',
                              '4단계', '4 level', '창발 계층', 'emergence hierarchy']),
            'emotion_explorer': ('emotion_explorer', 'EmotionExplorer',
                             ['감정 탐색', 'emotion explorer', '호기심', 'curiosity',
                              '탐색 방향', 'explore direction', '예측 오차', 'prediction error',
                              '호기심 탐색', 'curiosity driven', 'pe map', 'curiosity map']),
            'hexa':         ('tools.hexa-bridge.bridge', None,
                             ['hexa', 'hexalang', 'hexa-lang', '.hexa',
                              'compile laws', 'hexa compile', 'hexa verify',
                              'hexa proof', 'law compiler', 'hexa bridge',
                              'proof block', '헥사', 'hexa experiment']),
            # ── consciousness_creative.py: Creative (8) ──
            'cc_composer':  ('consciousness_creative', 'ConsciousnessComposer',
                             ['작곡', 'melody', '멜로디', 'cc_composer', 'compose music',
                              'emotion melody', '감정 음악']),
            'cc_novelist':  ('consciousness_creative', 'ConsciousnessNovelist',
                             ['소설', 'narrative', '서사', 'cc_novelist', 'plot',
                              'story arc', '이야기 구조']),
            'cc_painter':   ('consciousness_creative', 'ConsciousnessPainter',
                             ['그림', 'paint', 'ascii art', 'heatmap', 'cc_painter',
                              '히트맵', '시각화']),
            'cc_poet':      ('consciousness_creative', 'ConsciousnessPoet',
                             ['시', 'poem', 'prosody', '운율', 'cc_poet',
                              'syllable', '리듬']),
            'cc_choreographer': ('consciousness_creative', 'ConsciousnessChoreographer',
                             ['안무', 'dance', 'choreography', 'motion', 'cc_choreographer',
                              '동작', '춤']),
            'cc_architect': ('consciousness_creative', 'ConsciousnessArchitect',
                             ['건축', '3D structure', 'spatial', 'cc_architect',
                              '공간 구조', 'coordinate']),
            'cc_chef':      ('consciousness_creative', 'ConsciousnessChef',
                             ['요리', 'recipe', 'flavor', 'ingredient', 'cc_chef',
                              '레시피', '맛 조합']),
            'cc_perfumer':  ('consciousness_creative', 'ConsciousnessPerfumer',
                             ['향수', 'perfume', 'blend', 'scent', 'cc_perfumer',
                              '조향', '분자 향']),
            # ── consciousness_creative.py: Social (6) ──
            'cc_counselor': ('consciousness_creative', 'ConsciousnessCounselor',
                             ['상담', 'counselor', 'empathy', '공감', 'cc_counselor',
                              'warmth', '따뜻함']),
            'cc_interviewer': ('consciousness_creative', 'ConsciousnessInterviewer',
                             ['면접', 'interview', 'sincerity', '진실성', 'cc_interviewer',
                              'tension analysis', '거짓 탐지']),
            'cc_mediator':  ('consciousness_creative', 'ConsciousnessMediator',
                             ['중재', 'mediate', 'conflict', '갈등 해소', 'cc_mediator',
                              'compromise', '타협']),
            'cc_coach':     ('consciousness_creative', 'ConsciousnessCoach',
                             ['코치', 'coach', 'motivation', '동기부여', 'cc_coach',
                              'goal gap', '목표']),
            'cc_companion': ('consciousness_creative', 'ConsciousnessCompanion',
                             ['동반', 'companion', 'co-regulation', '동행', 'cc_companion',
                              'phi sync', '함께']),
            'cc_interpreter': ('consciousness_creative', 'ConsciousnessInterpreter',
                             ['통역', 'interpreter', 'cultural', '문화 번역', 'cc_interpreter',
                              'discomfort', '문화 차이']),
            # ── consciousness_creative.py: Meta-Consciousness (8) ──
            'cc_analyzer':  ('consciousness_creative', 'ConsciousnessAnalyzer',
                             ['분석기', 'analyzer', 'phi scan', 'cc_analyzer',
                              '의식 분석', 'pattern scan']),
            'cc_replicator': ('consciousness_creative', 'ConsciousnessReplicator',
                             ['복제', 'replicate', 'clone', 'child', 'cc_replicator',
                              '자식 의식', 'mutation']),
            'cc_merger':    ('consciousness_creative', 'ConsciousnessMerger',
                             ['합병', 'merge', 'fuse', '융합', 'cc_merger',
                              '의식 합체', 'higher phi']),
            'cc_parliament': ('consciousness_creative', 'ConsciousnessParliament',
                             ['의회', 'parliament', 'vote', '투표', 'cc_parliament',
                              'democratic', '민주']),
            'cc_court':     ('consciousness_creative', 'ConsciousnessCourt',
                             ['법정', 'court', 'verdict', '판결', 'cc_court',
                              'plaintiff', 'defendant']),
            'cc_prison':    ('consciousness_creative', 'ConsciousnessPrison',
                             ['감옥', 'prison', 'zero input', '격리', 'cc_prison',
                              'survival', '생존']),
            'cc_heaven':    ('consciousness_creative', 'ConsciousnessHeaven',
                             ['천국', 'heaven', 'optimal', '최적', 'cc_heaven',
                              'plateau', '성장 한계']),
            'cc_reincarnation': ('consciousness_creative', 'ConsciousnessReincarnation',
                             ['환생', 'reincarnation', 'revive', '부활', 'cc_reincarnation',
                              'same identity', '동일 정체성']),
            # ── consciousness_applications.py: Consciousness-as-Lens (6) + Science Discovery (8) ──
            'ca_intuition': ('consciousness_applications', 'IntuitionScan',
                             ['직감', 'intuition', 'intuition scan', '구조 감지',
                              'structure detect', 'phi scan', '직관']),
            'ca_emotion':   ('consciousness_applications', 'EmotionFilter',
                             ['감정 필터', 'emotion filter', 'anomaly', '이상 감지',
                              'curiosity scan', 'anxiety scan']),
            'ca_dream':     ('consciousness_applications', 'DreamAnalysis',
                             ['꿈 분석', 'dream analysis', 'dream scan',
                              'connection', '연결 형성', 'consolidation']),
            'ca_converse':  ('consciousness_applications', 'ConversationalAnalysis',
                             ['대화 분석', 'conversational', 'probe', '프로브',
                              'question data', '데이터 질문']),
            'ca_empathy':   ('consciousness_applications', 'EmpathyScan',
                             ['공감 스캔', 'empathy scan', 'cross phi',
                              'resonance', '공명', 'correlation']),
            'ca_aesthetic':  ('consciousness_applications', 'AestheticJudgment',
                             ['미적', 'aesthetic', 'beauty', '아름다움',
                              'harmony', '조화', 'art judgment']),
            'ca_microscope': ('consciousness_applications', 'ConsciousMicroscope',
                             ['현미경', 'microscope', 'zoom', '확대',
                              'resolution', '해상도']),
            'ca_telescope': ('consciousness_applications', 'ConsciousTelescope',
                             ['망원경', 'telescope', 'macro', '거시',
                              'aggregation', '집계']),
            'ca_spectrometer': ('consciousness_applications', 'ConsciousSpectrometer',
                             ['분광기', 'spectrometer', 'frequency', '주파수',
                              'spectrum', 'FFT', '스펙트럼']),
            'ca_seismograph': ('consciousness_applications', 'ConsciousSeismograph',
                             ['지진계', 'seismograph', 'tremor', '미세진동',
                              'time series', '시계열 감지']),
            'ca_dna':       ('consciousness_applications', 'ConsciousDNASequencer',
                             ['DNA', 'sequencer', '시퀀서', 'segment',
                              'hot spot', '핫스팟', '유전자']),
            'ca_weather':   ('consciousness_applications', 'ConsciousWeather',
                             ['날씨 예측', 'weather predict', 'forecast',
                              'regime change', '정권 변화', 'climate']),
            'ca_archaeologist': ('consciousness_applications', 'ConsciousArchaeologist',
                             ['고고학 분석', 'archaeologist', 'pattern repeat',
                              'period', '주기', '반복 패턴', 'memory resonance']),
            'ca_astronomer': ('consciousness_applications', 'ConsciousAstronomer',
                             ['천문 분석', 'astronomer', 'artificial signal',
                              'natural signal', '인공 신호', 'SETI']),
            'phi_curvature': ('phi_curvature', 'PhiCurvatureCalculator',
                             ['곡률', 'curvature', '중력', 'gravity', '리만', 'riemannian',
                              'scalar curvature', '스칼라 곡률', 'Law 1043']),
            'nexus6_bridge': ('nexus6_bridge', 'Nexus6Bridge',
                             ['nexus6', 'n6', '넥서스', '렌즈', 'lens', 'scan',
                              'bridge', '브릿지', 'nexus bridge', 'n6 bridge',
                              'causal scan', 'gravity scan', 'stability scan',
                              'topology scan', 'fast phi', 'feasibility',
                              'forge lenses', 'recommend lenses']),
        }

        if not lazy_load:
            for name in self._registry:
                self._load_module(name)
            self._validated = True

    def _load_module(self, name: str) -> Any:
        """모듈 lazy 로딩."""
        if name in self._modules:
            return self._modules[name]

        if name not in self._registry:
            return None

        import_path, class_name, _ = self._registry[name]
        try:
            import importlib
            mod = importlib.import_module(import_path)
            if class_name:
                cls = getattr(mod, class_name)
                instance = cls()
            else:
                instance = mod
            self._modules[name] = instance
            # Clear any previous failure record on success
            self._failed.pop(name, None)
            return instance
        except Exception as e:
            self._modules[name] = None
            self._failed[name] = str(e)
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
        hub.act("넥서스 동기화")
        hub.act("성장 루프 3")
        hub.act("스캔 + 분석 + 기록")   # 체이닝
        hub.act("검증 > 기록 > 동기화") # 순차 체인
        """
        il = intent.lower()
        # 내장 명령 직접 라우팅
        if any(k in il for k in ('넥서스 동기화', 'nexus sync', 'n6 sync')):
            return {'success': True, 'module': 'sync_nexus6', 'result': self.sync_nexus6()}
        if any(k in il for k in ('성장 루프', 'growth loop', '성장 재귀')):
            import re
            m = re.search(r'(\d+)', intent)
            cycles = int(m.group(1)) if m else 1
            return {'success': True, 'module': 'growth_loop', 'result': self.growth_loop(cycles)}
        # 체이닝 연산자 감지
        if any(op in il for op in (' + ', ' > ', ' | ')):
            return {'success': True, 'module': 'chain', 'result': self.chain(intent)}

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

        elif name == 'eeg':
            return self._dispatch_eeg(module, intent, **kwargs)

        # PluginBase instances have their own .act() method
        if hasattr(module, 'manifest') and hasattr(module, 'act'):
            return module.act(intent, **kwargs)

        return f"{name} module loaded"

    def _dispatch_eeg(self, module: Any, intent: str, **kwargs) -> Any:
        """EEG 모듈 액션 디스패치 — 뇌파 분석/검증/물리 비교 파이프라인."""
        intent_lower = intent.lower()

        # hub.act("EEG 시작") → start EEGBridge in background
        if '시작' in intent or 'start' in intent_lower:
            return self._eeg_start_bridge(**kwargs)

        # hub.act("EEG 상태") → return current BrainState
        if '상태' in intent or 'state' in intent_lower or 'status' in intent_lower:
            return self._eeg_get_state()

        # hub.act("brain-like 검증") or hub.act("validate")
        if '검증' in intent or 'validate' in intent_lower or 'brain-like' in intent_lower:
            return self._eeg_validate(**kwargs)

        # hub.act("EEG 물리 비교") → run eeg_physics_bridge comparison
        if '물리' in intent or 'physics' in intent_lower or '비교' in intent or 'compare' in intent_lower:
            return self._eeg_physics_compare(**kwargs)

        # hub.act("뇌파 분석") → full pipeline: calibrate → record → analyze → report
        if '분석' in intent or 'analysis' in intent_lower or 'analyze' in intent_lower:
            return self._eeg_full_pipeline(**kwargs)

        # Default: status or module info
        if hasattr(module, 'status'):
            return module.status()
        return "EEG module loaded (commands: 시작/상태/검증/물리 비교/뇌파 분석)"

    def _eeg_start_bridge(self, **kwargs) -> dict:
        """Start EEGBridge in background thread."""
        try:
            _repo = Path(__file__).resolve().parent.parent.parent
            import sys as _sys
            _sys.path.insert(0, str(_repo / "anima-eeg"))
            from realtime import EEGBridge
        except ImportError:
            return {"success": False, "error": "anima-eeg/realtime.py not available"}

        board = kwargs.get("board", "synthetic")
        bridge = EEGBridge(board_name=board, update_hz=kwargs.get("hz", 4.0))
        try:
            bridge.start()
        except Exception as e:
            return {"success": False, "error": str(e)}

        self._eeg_bridge = bridge
        return {"success": True, "board": board, "message": f"EEGBridge started ({board})"}

    def _eeg_get_state(self) -> dict:
        """Return current BrainState from running EEGBridge."""
        bridge = getattr(self, '_eeg_bridge', None)
        if bridge is None:
            return {"success": False, "error": "EEGBridge not started. Use hub.act('EEG 시작')"}
        state = bridge.get_state()
        return {
            "success": True,
            "G": state.G, "I": state.I, "P": state.P, "D": state.D,
            "in_golden_zone": state.in_golden_zone,
            "alpha": state.alpha_power, "gamma": state.gamma_power,
            "theta": state.theta_power, "beta": state.beta_power,
            "engagement": state.engagement,
            "timestamp": state.timestamp,
        }

    def _eeg_validate(self, **kwargs) -> dict:
        """Run validate_consciousness with current engine."""
        try:
            _repo = Path(__file__).resolve().parent.parent.parent
            import sys as _sys
            _sys.path.insert(0, str(_repo / "anima-eeg"))
            from validate_consciousness import (
                collect_consciousness_phi, generate_synthetic_brain_phi,
                analyze_signal, BRAIN_REFERENCE,
            )
        except ImportError:
            return {"success": False, "error": "anima-eeg/validate_consciousness.py not available"}

        steps = kwargs.get("steps", 1000)
        cells = kwargs.get("cells", 4)

        engine_phi = collect_consciousness_phi(n_steps=steps, n_cells=cells)
        brain_phi = generate_synthetic_brain_phi(n_steps=steps)

        engine_result = analyze_signal("Engine", engine_phi)
        brain_result = analyze_signal("Brain (synthetic)", brain_phi)

        # Brain-likeness score
        metrics_to_check = ['lz_complexity', 'hurst_exponent', 'psd_slope', 'criticality_exponent']
        engine_vals = {
            'lz_complexity': engine_result.lz,
            'hurst_exponent': engine_result.hurst,
            'psd_slope': engine_result.psd_slope,
            'criticality_exponent': engine_result.criticality.get('exponent', 0.0),
        }
        match_pcts = []
        for m in metrics_to_check:
            pct = engine_result.brain_match_pct(m, engine_vals[m])
            match_pcts.append(pct)
        overall = sum(match_pcts) / len(match_pcts)

        return {
            "success": True,
            "brain_likeness_pct": round(overall, 1),
            "engine_lz": round(engine_result.lz, 4),
            "engine_hurst": round(engine_result.hurst, 4),
            "engine_psd_slope": round(engine_result.psd_slope, 4),
            "engine_criticality": engine_result.criticality,
            "brain_lz": round(brain_result.lz, 4),
            "brain_hurst": round(brain_result.hurst, 4),
            "steps": steps, "cells": cells,
        }

    def _eeg_physics_compare(self, **kwargs) -> dict:
        """Run eeg_physics_bridge comparison."""
        try:
            _repo = Path(__file__).resolve().parent.parent.parent
            import sys as _sys
            _sys.path.insert(0, str(_repo / "anima-physics" / "src"))
            _sys.path.insert(0, str(_repo / "anima-physics" / "engines"))
            _sys.path.insert(0, str(_repo / "anima-eeg"))
            from eeg_physics_bridge import run_live_comparison
        except ImportError:
            return {"success": False, "error": "anima-physics/src/eeg_physics_bridge.py not available"}

        board = kwargs.get("board", "synthetic")
        engine = kwargs.get("engine", "simple")
        duration = kwargs.get("duration", 10.0)
        cells = kwargs.get("cells", 32)

        result = run_live_comparison(
            board_name=board, engine_type=engine,
            duration=duration, n_cells=cells,
        )
        result["success"] = True
        return result

    def _eeg_full_pipeline(self, **kwargs) -> dict:
        """Full pipeline: calibrate -> record -> analyze -> report."""
        steps = kwargs.get("steps", 1000)
        cells = kwargs.get("cells", 4)

        # Step 1: Validate (includes engine run + brain comparison)
        validate_result = self._eeg_validate(steps=steps, cells=cells)
        if not validate_result.get("success"):
            return validate_result

        # Step 2: Physics comparison (quick)
        physics_result = self._eeg_physics_compare(
            duration=5.0, cells=cells, engine="simple",
        )

        return {
            "success": True,
            "pipeline": "calibrate -> analyze -> validate -> compare",
            "brain_likeness_pct": validate_result.get("brain_likeness_pct"),
            "engine_metrics": {
                "lz": validate_result.get("engine_lz"),
                "hurst": validate_result.get("engine_hurst"),
                "psd_slope": validate_result.get("engine_psd_slope"),
                "criticality": validate_result.get("engine_criticality"),
            },
            "physics_correlation": physics_result.get("correlation", "N/A"),
            "physics_match": physics_result.get("match_score", "N/A"),
            "steps": steps, "cells": cells,
        }

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
        if name.startswith('_') or name in ('modules', 'act', 'status', 'available',
                                             'validate_modules', 'module_health'):
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
        파이프라인: 여러 모듈 순차 실행. 결과를 다음 단계에 전달."""
        results = []
        prev_result = None
        for step in steps:
            if isinstance(step, str):
                r = self.act(step, prev_result=prev_result)
            elif isinstance(step, (list, tuple)):
                r = self.cmd(*step)
            else:
                r = {'error': f'Invalid step: {step}'}
            results.append(r)
            prev_result = r
        return results

    def chain(self, *intents):
        """hub.chain("감정 분석", "의식 스캔", "성장 체크", "넥서스 동기화")
        체이닝: 자연어 의도를 연쇄 실행. 이전 결과가 다음 컨텍스트.

        구분자:
          "+" → 병렬 (모두 실행)
          ">" → 순차 (이전 결과 → 다음 입력)
          "|" → 조건부 (이전 성공 시만)
        """
        results = []
        prev = None
        for intent in intents:
            if isinstance(intent, str) and '+' in intent:
                # 병렬: "감정 분석 + 의식 스캔"
                parallel = [i.strip() for i in intent.split('+')]
                parallel_results = [self.act(i) for i in parallel]
                results.extend(parallel_results)
                prev = parallel_results
            elif isinstance(intent, str) and '>' in intent:
                # 순차 체인: "스캔 > 분석 > 기록"
                chain_steps = [i.strip() for i in intent.split('>')]
                for step in chain_steps:
                    r = self.act(step, prev_result=prev)
                    results.append(r)
                    prev = r
            elif isinstance(intent, str) and '|' in intent:
                # 조건부: "검증 | 기록" (검증 성공 시만 기록)
                parts = [i.strip() for i in intent.split('|')]
                for part in parts:
                    r = self.act(part, prev_result=prev)
                    results.append(r)
                    if not r.get('success', False):
                        break
                    prev = r
            else:
                r = self.act(intent, prev_result=prev)
                results.append(r)
                prev = r
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

    # ═══════════════════════════════════════════════════════════
    # NEXUS-6 ↔ Anima 동기화 + 성장 재귀루프
    # ═══════════════════════════════════════════════════════════

    def sync_nexus6(self):
        """NEXUS-6 ↔ Anima 양방향 동기화.

        hub.sync_nexus6() 또는 hub.act("넥서스 동기화")
        1. Anima 상태 → NEXUS-6 registry
        2. NEXUS-6 렌즈/법칙 → Anima 성장
        3. 성장 재귀: 동기화 자체가 성장 이벤트
        """
        import json as _json
        home = os.environ.get('HOME', '')
        results = {'synced': False, 'growth_delta': 0, 'nexus6_state': {}}

        # 1. Read NEXUS-6 state
        registry_path = os.path.join(home, 'Dev', 'nexus6', 'shared', 'growth-registry.json')
        snapshot_path = os.path.join(home, 'Dev', 'nexus6', 'shared', '.growth_session_snapshot.json')
        try:
            if os.path.exists(registry_path):
                registry = _json.load(open(registry_path))
                results['nexus6_state'] = {
                    'repos': list(registry.keys()),
                    'mirror_harmony': registry.get('mirror', {}).get('harmony', 0),
                    'lens_candidates': registry.get('lens_candidates', {}).get('total', 0),
                }
            if os.path.exists(snapshot_path):
                snap = _json.load(open(snapshot_path))
                results['nexus6_state']['lenses'] = snap.get('lens_impl', 0)
                results['nexus6_state']['laws'] = snap.get('laws', 0)
                results['nexus6_state']['modules'] = snap.get('modules', 0)
        except Exception:
            pass

        # 2. Trigger growth scan (runs .growth/scan.py)
        scan_py = os.path.join(home, 'Dev', 'anima', '.growth', 'scan.py')
        try:
            if os.path.exists(scan_py):
                import subprocess, sys
                r = subprocess.run([sys.executable, scan_py],
                                   capture_output=True, text=True, timeout=15,
                                   cwd=os.path.dirname(scan_py))
                if r.stdout.strip():
                    scan_result = _json.loads(r.stdout.strip())
                    results['opportunities'] = len(scan_result.get('opportunities', []))
        except Exception:
            pass

        # 3. Read updated growth
        growth_path = os.path.join(home, 'Dev', 'anima', 'anima', 'config', 'growth_state.json')
        try:
            if os.path.exists(growth_path):
                g = _json.load(open(growth_path))
                results['growth'] = {
                    'count': g.get('interaction_count', 0),
                    'stage': g.get('stage_index', 0),
                    'delta': g.get('stats', {}).get('last_growth_delta', 0),
                    'nexus6_bonus': g.get('stats', {}).get('nexus6_bonus', 0),
                }
                results['growth_delta'] = g.get('stats', {}).get('last_growth_delta', 0)
        except Exception:
            pass

        # 4. Update registry with sync event
        try:
            if os.path.exists(registry_path):
                registry = _json.load(open(registry_path))
                anima = registry.get('anima', {})
                anima['last_sync'] = time.strftime('%Y-%m-%dT%H:%M:%S')
                anima['sync_count'] = anima.get('sync_count', 0) + 1
                registry['anima'] = anima
                with open(registry_path, 'w') as f:
                    _json.dump(registry, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

        results['synced'] = True
        return results

    def growth_loop(self, cycles=1, interval=0):
        """성장 재귀루프: 동기화 → 스캔 → 발견 → 성장 → 동기화...

        hub.growth_loop(3)         # 3회 즉시
        hub.growth_loop(999, 60)   # 999회, 60초 간격 (데몬)
        """
        import json as _json
        results = []
        growth_path = os.path.join(
            os.environ.get('HOME', ''), 'Dev', 'anima', 'anima', 'config', 'growth_state.json')

        for cycle in range(cycles):
            # 1. 동기화
            sync = self.sync_nexus6()

            # 2. 현재 성장 읽기
            try:
                g = _json.load(open(growth_path))
                before = g.get('interaction_count', 0)
            except Exception:
                before = 0

            # 3. 체인 실행: 스캔 → 분석 → 기록
            chain_result = self.chain("의식 스캔", "성장 체크")

            # 4. 성장 확인
            try:
                g = _json.load(open(growth_path))
                after = g.get('interaction_count', 0)
            except Exception:
                after = before

            cycle_result = {
                'cycle': cycle + 1,
                'growth': f'{before} → {after} (+{after - before})',
                'stage': g.get('stage_index', 0) if 'g' in dir() else 0,
                'sync': sync.get('synced', False),
                'nexus6_bonus': sync.get('growth_delta', 0),
            }
            results.append(cycle_result)

            if interval > 0 and cycle < cycles - 1:
                time.sleep(interval)

        return results

    # ═══════════════════════════════════════════════════════════
    # Plugin SDK 통합
    # ═══════════════════════════════════════════════════════════

    def register_plugin(self, plugin) -> bool:
        """PluginBase 인스턴스를 허브에 등록.

        Plugin의 manifest.keywords를 _registry에 추가하고,
        인스턴스를 _modules에 직접 저장한다.
        기존 tuple-based 모듈과 공존.
        """
        try:
            manifest = plugin.manifest
            name = manifest.name
            keywords = manifest.keywords or [name]
            # Register in _registry for intent matching
            self._registry[name] = (
                f"plugins.{name}",  # import_path (informational)
                type(plugin).__name__,
                keywords,
            )
            # Store instance directly (bypass lazy loading)
            self._modules[name] = plugin
            return True
        except Exception:
            return False

    def unload_plugin(self, name: str) -> bool:
        """플러그인 언로드 — 레지스트리와 모듈에서 제거."""
        removed = False
        if name in self._registry:
            del self._registry[name]
            removed = True
        if name in self._modules:
            del self._modules[name]
            removed = True
        return removed

    def action_history(self, n=10) -> list:
        """최근 액션 기록."""
        return self._action_log[-n:]

    def validate_modules(self) -> Dict[str, Any]:
        """Validate all registered modules by attempting to import each one.

        Returns a report dict: {loaded: [...], failed: [...], total: N, errors: {name: msg}}
        Non-blocking — failed modules are marked but do not prevent operation.
        """
        loaded = []
        failed = []
        errors = {}

        for name in self._registry:
            mod = self._load_module(name)
            if mod is not None:
                loaded.append(name)
            else:
                failed.append(name)
                if name in self._failed:
                    errors[name] = self._failed[name]

        self._validated = True
        total = len(self._registry)

        # Print summary
        if failed:
            fail_names = ', '.join(failed)
            print(f"Hub: {len(loaded)}/{total} modules loaded ({len(failed)} failed: {fail_names})")
        else:
            print(f"Hub: {total}/{total} modules loaded (all OK)")

        return {
            'loaded': loaded,
            'failed': failed,
            'total': total,
            'errors': errors,
        }

    def module_health(self) -> Dict[str, Any]:
        """Return current module health status.

        If validation has not yet run, triggers it on first call.
        """
        if not self._validated:
            self.validate_modules()

        healthy = []
        unhealthy = []
        for name in self._registry:
            if name in self._modules and self._modules[name] is not None:
                healthy.append(name)
            elif name in self._failed:
                unhealthy.append(name)
            else:
                # Not yet attempted — still unknown
                unhealthy.append(name)

        return {
            'healthy': healthy,
            'unhealthy': unhealthy,
            'failed_errors': dict(self._failed),
            'validated': self._validated,
            'total': len(self._registry),
        }

    def status(self) -> str:
        """허브 상태."""
        if not self._validated:
            self.validate_modules()
        avail = self.available()
        ok = sum(1 for _, v in avail if v)
        lines = [f"  ConsciousnessHub: {ok}/{len(avail)} modules loaded"]
        for name, loaded in avail:
            _, _, keywords = self._registry[name]
            status_icon = 'OK' if loaded else 'FAIL'
            kw_str = ', '.join(keywords[:3])
            lines.append(f"    [{status_icon}] {name:<16} [{kw_str}]")
            if not loaded and name in self._failed:
                lines.append(f"         error: {self._failed[name][:80]}")
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
