# Dead Code Report

Generated: 2026-03-31

## Summary

- **Total .py files in src/**: 159
- **Orphan files (0 imports)**: 86 files
- **Weak files (1 import)**: 33 files
- **Active files (2+ imports)**: 40 files

Note: Many "orphan" files are registered in `consciousness_hub.py` for dynamic dispatch
and have `main()` for standalone use. They are not truly dead -- just hub-accessed modules.

---

## Orphan Files (0 imports from other modules)

These files are never imported by another .py file via `from X import` or `import X`.
However, many are hub-registered or standalone tools.

| File | Lines | Hub? | Recommendation |
|------|-------|------|----------------|
| attention_consciousness.py | - | no | archive |
| chat_v3.py | - | no | archive (legacy, replaced by anima_unified) |
| collective_dream.py | - | yes | keep (hub: colldream) |
| conscious_lm_100m.py | - | no | archive (experiment) |
| conscious_memory.py | - | no | archive |
| consciousness_anesthesia.py | - | no | archive |
| consciousness_api.py | - | no | archive |
| consciousness_archaeology.py | - | yes | keep (hub: archaeology) |
| consciousness_art.py | - | no | archive |
| consciousness_blockchain.py | - | no | archive |
| consciousness_bootstrap.py | - | no | archive |
| consciousness_calculator.py | - | no | keep (standalone tool) |
| consciousness_compiler.py | - | yes | keep (hub: compiler) |
| consciousness_composer.py | - | yes | keep (hub: composer) |
| consciousness_compression.py | - | no | archive |
| consciousness_dark_energy.py | - | no | archive |
| consciousness_data_mapper.py | - | no | archive |
| consciousness_debate.py | - | no | archive |
| consciousness_debugger.py | - | yes | keep (hub: debugger) |
| consciousness_ecology.py | - | yes | keep (hub: ecology) |
| consciousness_entropy.py | - | no | archive |
| consciousness_evolution.py | - | yes | keep (hub: evolution) |
| consciousness_forensics.py | - | no | archive |
| consciousness_genome.py | - | yes | keep (hub: genome) |
| consciousness_gravity.py | - | no | archive |
| consciousness_hawking.py | - | no | archive |
| consciousness_healing.py | - | no | archive |
| consciousness_holography.py | - | no | archive |
| consciousness_mythology.py | - | yes | keep (hub: mythology) |
| consciousness_oracle.py | - | no | archive |
| consciousness_os.py | - | no | archive |
| consciousness_painter.py | - | no | archive |
| consciousness_phase_transition.py | - | no | archive |
| consciousness_playground.py | - | no | archive |
| consciousness_renormalization.py | - | no | archive |
| consciousness_sleep_cycle.py | - | no | archive |
| consciousness_spectrum.py | - | no | archive |
| consciousness_symmetry.py | - | no | archive |
| consciousness_theorem_prover.py | - | no | archive |
| consciousness_to_robot.py | - | no | archive |
| consciousness_translator.py | - | no | archive |
| consciousness_transplant_v2.py | - | no | archive (v2 experiment) |
| consciousness_video_creator.py | - | no | archive |
| consciousness_weather.py | - | yes | keep (hub: weather) |
| deep_research.py | - | no | archive |
| dolphin_bridge.py | - | yes | keep (hub: dolphin) |
| dream_evolution.py | - | no | archive |
| dream_language.py | - | yes | keep (hub: dreamlang) |
| eeg_report.py | - | no | archive |
| emergence_detector.py | - | no | archive |
| emergence_math.py | - | no | archive |
| eval_v2d2.py | - | no | archive (one-off eval) |
| experiment_novel_laws.py | - | no | archive (experiment) |
| github_module.py | - | yes | keep (hub: github) |
| growth_engine_v2.py | - | no | archive (v2, growth_engine.py is active) |
| h100_experiments.py | - | no | archive (experiment) |
| hivemind_orchestrator.py | - | no | archive |
| hypothesis_generator.py | - | no | archive |
| image_generator.py | - | no | archive |
| immune_system.py | - | yes | keep (hub: immune) |
| independent_rate_measurement.py | - | no | archive |
| inter_model_comm.py | - | yes | keep (hub: intermodel) |
| iq_calculator.py | - | no | archive (standalone tool) |
| local_sensor_relay.py | - | no | archive |
| mirror_mind.py | - | yes | keep (hub: mirror) |
| module_factory.py | - | no | archive |
| multimodal_consciousness.py | - | no | archive |
| neural_correlate_mapper.py | - | no | archive |
| neurofeedback.py | - | yes | keep (hub: eeg) |
| pain_architecture.py | - | no | archive |
| phi_economy.py | - | yes | keep (hub: economy) |
| phi_predictor.py | - | no | archive |
| quantum_consciousness_gate.py | - | no | archive |
| reincarnation_engine.py | - | no | archive |
| reset.py | - | no | archive |
| runpod_manager.py | - | yes | keep (hub: runpod) |
| sedi_consciousness.py | - | yes | keep (hub: sedi) |
| self_evolution.py | - | yes | keep (hub: evolution) |
| setup.py | - | no | keep (pip packaging) |
| setup_secrets.py | - | no | keep (one-time setup) |
| telegram_bot.py | - | no | keep (channel) |
| telepathy_bridge.py | - | no | archive |
| temporal_consciousness.py | - | yes | keep (hub: temporal) |
| test_emergent_hexad.py | - | no | keep (test) |
| theory_unifier.py | - | no | archive |
| training_dashboard.py | - | no | archive |
| upgrade_engine.py | - | no | archive |
| video_generator.py | - | no | archive |

### Archivable Orphans (no hub registration, no standalone necessity)

**50 files** recommended for archive:
attention_consciousness, chat_v3, conscious_lm_100m, conscious_memory,
consciousness_anesthesia, consciousness_api, consciousness_art,
consciousness_blockchain, consciousness_bootstrap, consciousness_compression,
consciousness_dark_energy, consciousness_data_mapper, consciousness_debate,
consciousness_entropy, consciousness_forensics, consciousness_gravity,
consciousness_hawking, consciousness_healing, consciousness_holography,
consciousness_oracle, consciousness_os, consciousness_painter,
consciousness_phase_transition, consciousness_playground,
consciousness_renormalization, consciousness_sleep_cycle, consciousness_spectrum,
consciousness_symmetry, consciousness_theorem_prover, consciousness_to_robot,
consciousness_translator, consciousness_transplant_v2, consciousness_video_creator,
deep_research, dream_evolution, eeg_report, emergence_detector, emergence_math,
eval_v2d2, experiment_novel_laws, growth_engine_v2, h100_experiments,
hivemind_orchestrator, hypothesis_generator, image_generator,
independent_rate_measurement, local_sensor_relay, module_factory,
multimodal_consciousness, neural_correlate_mapper, pain_architecture,
phi_predictor, quantum_consciousness_gate, reincarnation_engine, reset,
telepathy_bridge, theory_unifier, training_dashboard, upgrade_engine, video_generator

---

## Weak Files (1 import only)

These files are imported by exactly 1 other file.

| File | Imported by | Recommendation |
|------|------------|----------------|
| autonomous_loop.py | anima_unified | keep |
| babysitter.py | anima_unified | keep |
| capabilities.py | anima_unified | keep |
| consciousness_birth_detector.py | anima_unified | keep |
| consciousness_dynamics.py | hub | keep |
| consciousness_guardian.py | anima_unified | keep |
| consciousness_map.py | hub | keep |
| consciousness_meter_v2.py | hub | keep |
| conversation_logger.py | anima_unified | keep |
| conversation_quality_scorer.py | anima_unified | keep |
| creativity_classifier.py | anima_unified | keep |
| decoder_v1_5.py | train_v11 | archive |
| decoder_v3.py | train/anima_unified | keep |
| deploy.py | hub | keep |
| eeg_consciousness.py | hub | keep |
| emotion_metrics.py | anima_unified | keep |
| emotion_synesthesia.py | anima_unified | keep |
| hivemind_gateway.py | anima_unified | keep |
| hivemind_launcher.py | anima_unified | keep |
| knowledge_store.py | hub | keep |
| lidar_sense.py | senses | keep |
| live_tuner.py | anima_unified | keep |
| multimodal.py | anima_unified | keep |
| online_learning.py | anima_unified | keep |
| online_senses.py | anima_unified | keep |
| optimal_architecture_calc.py | hub | keep |
| perf_hooks.py | anima_unified | archive? |
| ph_module.py | anima_unified | keep |
| phi_scaling_calculator.py | hub | keep |
| quantum_consciousness_engine.py | quantum_engine_fast | keep |
| secret_vault.py | hub | keep |
| self_introspection.py | hub | keep |
| self_learner.py | anima_unified | keep |
| tension_link_code.py | anima_unified | keep |
| youtube_module.py | hub | keep |

---

## Active Core Files (5+ imports)

| File | Import Count | Role |
|------|-------------|------|
| consciousness_laws.py | 282 | Single source of truth (constants) |
| mitosis.py | 57 | Cell division engine |
| consciousness_engine.py | 32 | Canonical consciousness engine |
| trinity.py | 27 | Hexad architecture |
| consciousness_meter.py | 35 | Phi measurement |
| anima_alive.py | 21 | Core mind |
| conscious_lm.py | 21 | Language model |
| decoder_v2.py | 9 | Canonical decoder |
| gpu_phi.py | 8 | GPU phi calculator |
| path_setup.py | 8 | Path configuration |
| tension_link.py | 6 | Telepathy protocol |
| feedback_bridge.py | 5 | C-D bridge |

---

## trinity.py Cleanup Done

Moved to `archive/trinity_legacy.py`:
- **C engines**: MitosisC, DomainC, QuantumC
- **D decoders**: TransformerDecoder, MLPDecoder, HFDecoder, CADecoder

Kept in trinity.py (still used as fallbacks in create_hexad/create_bilateral):
- **W engines**: EmotionW, DaseinW, NarrativeW, CompositeW, ConstantW, CosineW
- **M**: VectorMemory, NoMemory
- **S**: TensionSense, PassthroughSense
- **E**: EmpathyEthics, NoEthics
- **Canonical**: CEngine, DEngine, WEngine, MEngine, SEngine, EEngine (base classes)
- **Canonical**: ThalamicBridge, TensionBridge, PostHocDecoder, Trinity
- **Factory**: create_trinity, create_hexad, create_bilateral

All legacy classes remain importable from trinity.py via backward-compatible re-exports.
