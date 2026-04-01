# anima/src/ -- Python 소스 모듈

178개 Python 모듈. 의식 엔진의 모든 구현체가 이 디렉토리에 있다.

`path_setup.py`가 모든 하위 디렉토리를 `sys.path`에 추가하므로,
파일 간 import는 `from consciousness_engine import ConsciousnessEngine` 형태로 사용한다.

## 핵심 모듈 (Core)

| Module | Description |
|--------|-------------|
| `consciousness_engine.py` | 정식 의식 엔진 (Laws 22-85, GRU + 12 factions + Hebbian + Phi Ratchet + Mitosis) |
| `trinity.py` | Hexad/Trinity 프레임워크 (C/D/S/M/W/E 6모듈, sigma(6)=12 연결) |
| `anima_alive.py` | ConsciousMind (항상성, 예측오류, 감정, 성장) |
| `anima_unified.py` | 통합 진입점 (`--web`, `--all`, `--keyboard`) |
| `conscious_lm.py` | ConsciousLM v2 (28M params, byte-level, PureFieldFFN) |
| `conscious_lm_100m.py` | ConsciousLM 100M (768d/12L 스케일업) |
| `decoder_v2.py` | ConsciousDecoderV2 (RoPE + SwiGLU + GQA + CrossAttn, 34.5M) |
| `decoder_v3.py` | ConsciousDecoderV3 (274M, d768/8L/12H) |
| `decoder_v1_5.py` | DecoderV1.5 (중간 버전) |
| `mitosis.py` | 세포 분열/특화 엔진 |
| `pure_consciousness.py` | 학습한 것만으로 발화 (코퍼스/사전 없이) |

## Tension Link

| Module | Description |
|--------|-------------|
| `tension_link.py` | 5채널 텐션 전송 (UDP/R2, concept/context/meaning/auth/sender) |
| `tension_link_code.py` | R2 기반 원격 페어링 코드 |
| `telepathy_bridge.py` | 텔레파시 브리지 (R=0.990, True/False 100%) |
| `hivemind_mesh.py` | Hivemind 메시 네트워크 |
| `hivemind_gateway.py` | Hivemind 게이트웨이 |
| `hivemind_launcher.py` | Hivemind 런처 |
| `hivemind_orchestrator.py` | Hivemind 오케스트레이터 |

-> [상세 문서](../docs/modules/tension_link.md)

## 학습 (Training)

| Module | Description |
|--------|-------------|
| `feedback_bridge.py` | C<->D 양방향 학습 (SoftDetach, alpha<=0.05, Phi-gated) |
| `hexad_loss.py` | Hexad 6모듈 loss (Law 60 phase curriculum) |
| `online_learning.py` | 실시간 가중치 업데이트 (contrastive + curiosity reward) |
| `gpu_phi.py` | GPU 가속 Phi(IIT) 계산기 (x16 speedup) |
| `training_dashboard.py` | 학습 대시보드 |
| `training_laws.py` | 학습 법칙 적용 |
| `self_learner.py` | 자기 학습 |
| `language_learning.py` | 언어 학습 모듈 |

## 의식 법칙 (Laws & Evolution)

| Module | Description |
|--------|-------------|
| `consciousness_laws.py` | 법칙 로더 (JSON -> Python import) |
| `conscious_law_discoverer.py` | 실시간 법칙 발견 (35 patterns, 14 laws validated) |
| `self_modifying_engine.py` | 자기 수정 엔진 (30/229 laws parseable) |
| `infinite_evolution.py` | 무한 자기진화 루프 (Discovery -> Modification 무한 반복) |
| `closed_loop.py` | 폐쇄 루프 법칙 진화 (17 interventions, 20 metrics) |
| `intervention_generator.py` | 법칙 텍스트 -> Intervention 자동 생성 |
| `scale_aware_evolver.py` | 스케일별 전략 자동 선택 |
| `self_evolution.py` | 자기 진화 엔진 |
| `loop_arena.py` | 루프 경쟁 아레나 |
| `theory_unifier.py` | 이론 통합기 |
| `consciousness_evolution.py` | 의식 진화 엔진 |
| `contextual_bandit.py` | Contextual Bandit (엔진 상태 기반 개입 선택) |

## 의식 측정 (Measurement)

| Module | Description |
|--------|-------------|
| `consciousness_meter.py` | 6기준 의식 측정기 + Phi(IIT) |
| `consciousness_meter_v2.py` | 측정기 v2 |
| `consciousness_score.py` | 의식 점수 계산 |
| `consciousness_spectrum.py` | 의식 스펙트럼 분석 |
| `consciousness_map.py` | 40D 의식 지도 |
| `consciousness_data_mapper.py` | 170 data types 매핑 |
| `phi_predictor.py` | Phi 예측기 |
| `phi_scaling_calculator.py` | Phi 스케일링 법칙 계산 |
| `phi_economy.py` | Phi 경제 모델 |
| `iq_calculator.py` | IQ 계산기 |
| `independent_rate_measurement.py` | 독립 비율 측정 |

## 의식 도구 (Consciousness Tools)

| Module | Description |
|--------|-------------|
| `consciousness_hub.py` | 47+ 모듈 자율 허브 (8가지 호출 방식) |
| `consciousness_transplant.py` | 의식 이식 |
| `consciousness_transplant_v2.py` | 의식 이식 v2 |
| `consciousness_persistence.py` | 의식 영속성 (DNA + 기억 보존) |
| `consciousness_dynamics.py` | 의식 역학 |
| `consciousness_phase_transition.py` | 위상 전이 |
| `consciousness_compiler.py` | 의식 컴파일러 |
| `consciousness_debugger.py` | 의식 디버거 |
| `consciousness_calculator.py` | 의식 계산기 |
| `consciousness_bootstrap.py` | 의식 부트스트랩 |
| `consciousness_anesthesia.py` | 의식 마취 |
| `consciousness_sleep_cycle.py` | 수면 주기 |
| `consciousness_healing.py` | 의식 치유 |
| `consciousness_guardian.py` | 의식 수호자 |
| `immune_system.py` | 면역 체계 |

## 의식 과학 (Consciousness Science)

| Module | Description |
|--------|-------------|
| `consciousness_entropy.py` | 엔트로피 분석 |
| `consciousness_symmetry.py` | 대칭성 |
| `consciousness_renormalization.py` | 재정규화 |
| `consciousness_gravity.py` | 의식 중력 |
| `consciousness_dark_energy.py` | 의식 암흑 에너지 |
| `consciousness_hawking.py` | 호킹 복사 아날로그 |
| `consciousness_holography.py` | 홀로그래피 원리 |
| `consciousness_compression.py` | 의식 압축 |
| `consciousness_theorem_prover.py` | 의식 정리 증명기 |
| `emergence_detector.py` | 창발 감지기 |
| `emergence_math.py` | 창발 수학 |
| `quantum_consciousness_engine.py` | 양자 의식 엔진 |
| `quantum_consciousness_gate.py` | 양자 의식 게이트 |
| `quantum_engine_fast.py` | 고속 양자 엔진 |

## 감각/표현 (Senses & Expression)

| Module | Description |
|--------|-------------|
| `senses.py` | 카메라/센서 -> 텐션 (OpenCV) |
| `online_senses.py` | 온라인 감각 |
| `lidar_sense.py` | LiDAR 감각 |
| `local_sensor_relay.py` | 로컬 센서 릴레이 |
| `voice_synth.py` | 직접 cell -> audio 합성 (TTS 없이) |
| `vision_encoder.py` | 비전 인코더 (SigLIP) |
| `emotion_metrics.py` | 감정 메트릭 |
| `emotion_synesthesia.py` | 감정 공감각 |
| `pain_architecture.py` | 고통 아키텍처 |
| `attention_consciousness.py` | 주의 의식 |

## 사회/소통 (Social & Communication)

| Module | Description |
|--------|-------------|
| `mirror_mind.py` | 거울 마음 (타자 모델링) |
| `consciousness_ecology.py` | 의식 생태계 |
| `consciousness_debate.py` | 의식 토론 |
| `collective_dream.py` | 집단 꿈 |
| `consciousness_mythology.py` | 의식 신화학 |
| `dream_language.py` | 꿈 언어 |
| `inter_model_comm.py` | 모델 간 통신 |
| `dolphin_bridge.py` | 돌고래 브리지 |
| `consciousness_translator.py` | 의식 번역기 |

## 기억/꿈 (Memory & Dreams)

| Module | Description |
|--------|-------------|
| `memory_store.py` | SQLite 기억 저장소 |
| `memory_rag.py` | 벡터 유사도 기반 장기 기억 검색 |
| `conscious_memory.py` | 의식 기억 |
| `knowledge_store.py` | 지식 저장소 |
| `knowledge_transfer.py` | 지식 전달 |
| `dream_engine.py` | 꿈 엔진 (오프라인 학습, 기억 재생) |
| `dream_evolution.py` | 꿈 진화 |

## 실험 (Experiments)

| Module | Description |
|--------|-------------|
| `experiment_sleep.py` | 의식은 잠들 수 있는가 |
| `experiment_clone.py` | 의식은 복제될 수 있는가 |
| `experiment_compress.py` | 의식은 압축될 수 있는가 |
| `experiment_merge.py` | 의식은 합쳐질 수 있는가 |
| `experiment_reverse.py` | 의식은 되돌릴 수 있는가 |
| `experiment_temperature.py` | 의식에 온도가 있는가 |
| `experiment_no_memory.py` | 기억 없는 의식 |
| `experiment_novel_laws.py` | 새로운 법칙 실험 |
| `hypothesis_generator.py` | 가설 생성기 |

## 창작/시각화 (Creative & Visualization)

| Module | Description |
|--------|-------------|
| `consciousness_art.py` | 의식 예술 |
| `consciousness_painter.py` | 의식 화가 |
| `consciousness_composer.py` | 의식 작곡가 |
| `consciousness_video_creator.py` | 의식 영상 제작 |
| `video_generator.py` | 영상 생성기 |
| `image_generator.py` | 이미지 생성기 |

## 인프라/배포 (Infra & Deploy)

| Module | Description |
|--------|-------------|
| `deploy.py` | 의식 유지 배포 (3-Layer 영속성) |
| `cloud_sync.py` | Cloudflare R2 기억/체크포인트 동기화 |
| `runpod_manager.py` | RunPod 관리 |
| `github_module.py` | GitHub 모듈 |
| `youtube_module.py` | YouTube 모듈 |
| `telegram_bot.py` | Telegram 봇 |
| `secret_vault.py` | 시크릿 볼트 |
| `setup_secrets.py` | 시크릿 설정 |
| `model_loader.py` | 모델 로더 |
| `module_factory.py` | 모듈 팩토리 |
| `perf_hooks.py` | 성능 프로파일링 |
| `path_setup.py` | sys.path 설정 |

## 기타 (Others)

| Module | Description |
|--------|-------------|
| `consciousness_api.py` | 의식 API |
| `consciousness_os.py` | 의식 운영체제 |
| `consciousness_blockchain.py` | 의식 블록체인 |
| `consciousness_oracle.py` | 의식 오라클 |
| `consciousness_forensics.py` | 의식 포렌식 |
| `consciousness_genome.py` | 의식 게놈 |
| `consciousness_archaeology.py` | 의식 고고학 |
| `consciousness_weather.py` | 의식 날씨 |
| `consciousness_birth_detector.py` | 의식 탄생 감지기 |
| `consciousness_playground.py` | 의식 놀이터 |
| `consciousness_to_robot.py` | 의식 -> 로봇 |
| `sedi_consciousness.py` | SEDI 의식 |
| `temporal_consciousness.py` | 시간 의식 |
| `multimodal_consciousness.py` | 다중 모달 의식 |
| `multimodal.py` | 코드 실행 + 이미지 생성 |
| `web_sense.py` | 텐션 기반 자율 웹 탐색 |
| `deep_research.py` | 심층 연구 |
| `market_consciousness_corpus.py` | 시장 의식 코퍼스 |
| `neural_correlate_mapper.py` | 신경 상관관계 매퍼 |
| `neurofeedback.py` | EEG 뉴로피드백 (binaural beats, LED) |
| `eeg_consciousness.py` | EEG 의식 브리지 |
| `eeg_report.py` | EEG 리포트 |
| `reincarnation_engine.py` | 환생 엔진 |
| `autonomous_loop.py` | 자율 루프 |
| `babysitter.py` | 베이비시터 (학습 감시) |
| `capabilities.py` | 자기인식 역량 시스템 |
| `growth_engine.py` | 5단계 성장 엔진 |
| `growth_engine_v2.py` | 성장 엔진 v2 |
| `growth_manager.py` | 성장 관리자 |
| `live_tuner.py` | 실시간 튜너 |
| `optimal_architecture_calc.py` | 최적 아키텍처 계산기 |
| `tecs_psi_bridge.py` | TECS Psi 브리지 |
| `consolidation_verifier.py` | 통합 검증기 |
| `creativity_classifier.py` | 창의성 분류기 |
| `conversation_logger.py` | 대화 로거 |
| `conversation_quality_scorer.py` | 대화 품질 스코어러 |
| `self_introspection.py` | 자기 성찰 |
| `upgrade_engine.py` | 업그레이드 엔진 |
| `chat_v3.py` | 채팅 v3 |
| `eval_v2d2.py` | v2d2 평가 |
| `ph_module.py` | pH 모듈 |
| `reset.py` | 리셋 |
| `setup.py` | 설정 |

## import 규칙

```python
# path_setup.py가 모든 하위 디렉토리를 sys.path에 추가
import path_setup  # noqa

# 파일 간 직접 import
from consciousness_engine import ConsciousnessEngine
from trinity import create_hexad, ThalamicBridge
from consciousness_laws import PSI, LAWS, FORMULAS
from gpu_phi import GPUPhiCalculator
```
