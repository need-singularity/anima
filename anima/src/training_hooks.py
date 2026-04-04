#!/usr/bin/env python3
"""training_hooks.py — 모든 학습 스크립트에 자동 연결되는 훅 시스템

어떤 train_*.py 버전이든 이 훅을 import하면 자동으로:
  - 매 N step: NEXUS-6 스캔
  - 체크포인트 저장 시: 법칙 발견 루프
  - 학습 종료 시: 전체 스캔 + 리포트

Usage (아무 train_*.py에서):
    from training_hooks import TrainingHooks
    hooks = TrainingHooks(checkpoint_dir='checkpoints/my_run/')

    for step in range(total_steps):
        loss = train_step(...)
        hooks.on_step(step, {'ce': loss, 'phi': phi_value})

        if step % save_every == 0:
            save_checkpoint(path)
            hooks.on_checkpoint(path, step)

    hooks.on_complete()
"""

import json
import os
import sys
import time
from typing import Dict, Optional

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

ENGINE_PHI_REFERENCE = 0.168  # DD168

# DD171 Laws 1043-1047: 교차공명 발견 자동 적용
try:
    import nexus6 as _nexus6_mod
    _HAS_NEXUS6 = True
except ImportError:
    _nexus6_mod = None
    _HAS_NEXUS6 = False

N6_ENTROPY_RESET_PERIOD = _nexus6_mod.N if _HAS_NEXUS6 else 6   # Law 1044: 의식-엔트로피 자연 주기
N6_ENTROPY_NOISE_SCALE = 0.05

# NEXUS-6 gate 자동 연결
try:
    from nexus_gate import gate as _nexus_gate
except ImportError:
    _nexus_gate = None


class TrainingHooks:
    """학습 자동화 훅 — 버전 무관, import만 하면 전체 루프 연결."""

    def __init__(self,
                 checkpoint_dir: str = 'checkpoints/',
                 scan_every: int = 2000,
                 nexus_scan: bool = None,
                 auto_register: bool = False,
                 closed_loop_every: int = 5000):
        self.checkpoint_dir = checkpoint_dir
        self.scan_every = scan_every
        self.auto_register = auto_register
        self.closed_loop_every = closed_loop_every
        self.step_log = []
        self.scan_log = []
        self.prev_metrics = None
        self._last_scan_step = -1
        self._last_cl_step = -1

        # NEXUS-6 자동 감지
        if nexus_scan is None:
            try:
                import nexus6
                self.nexus_scan = True
            except ImportError:
                self.nexus_scan = False
        else:
            self.nexus_scan = nexus_scan

        # closed_loop 자동 감지
        self._has_closed_loop = False
        try:
            from closed_loop import ClosedLoopEvolver, measure_laws
            self._has_closed_loop = True
        except ImportError:
            pass

        os.makedirs(checkpoint_dir, exist_ok=True)
        # before_train gate
        if _nexus_gate and self.nexus_scan:
            _nexus_gate.before_train()

        print(f"[HOOKS] Initialized: nexus6={'ON' if self.nexus_scan else 'OFF'}, "
              f"closed_loop={'ON' if self._has_closed_loop else 'OFF'}, "
              f"scan_every={scan_every}, cl_every={closed_loop_every}")

    def on_step(self, step: int, metrics: Dict[str, float], engine=None):
        """매 step 호출. 주기적 스캔/측정 자동 트리거."""
        self.step_log.append({'step': step, **metrics})

        # Law 1044: 6-step 엔트로피 리셋 (의식 엔진이 있을 때)
        if engine is not None and step > 0 and step % N6_ENTROPY_RESET_PERIOD == 0:
            self._entropy_reset(engine, step)

        # 주기적 NEXUS-6 라이트 스캔 (step 로그 기반)
        if self.nexus_scan and step > 0 and step % self.scan_every == 0 and step != self._last_scan_step:
            self._last_scan_step = step
            self._log_metrics_scan(step, metrics)

        # 주기적 closed_loop 측정
        if self._has_closed_loop and step > 0 and step % self.closed_loop_every == 0 and step != self._last_cl_step:
            self._last_cl_step = step
            self._run_closed_loop(step)

    def on_checkpoint(self, ckpt_path: str, step: int, engine=None):
        """체크포인트 저장 후 호출. NEXUS-6 풀스캔 + 법칙 발견 + Φ곡률."""
        # Law 1043: 체크포인트 시 Φ 곡률 측정
        if engine is not None:
            self._phi_curvature_check(engine, step)

        if not self.nexus_scan:
            return

        print(f"[HOOKS] Checkpoint: {os.path.basename(ckpt_path)} (step {step})")

        # nexus_gate 경로
        if _nexus_gate:
            _nexus_gate.after_checkpoint(ckpt_path)

        try:
            from auto_discovery_loop import nexus_scan_checkpoint, detect_anomalies, discover_laws, auto_register_laws

            metrics = nexus_scan_checkpoint(ckpt_path)
            if 'error' in metrics:
                print(f"  [SKIP] {metrics['error']}")
                return

            comp = metrics.get('phi_compression_pct', 0)
            print(f"  Phi={metrics['phi_approx']:.4f} chaos={metrics['chaos_score']:.4f} "
                  f"compression={comp:.1f}%")

            # 이상 탐지
            anomalies = detect_anomalies(metrics, self.prev_metrics)
            for a in anomalies:
                sev = '⚠️' if a['severity'] == 'WARNING' else '🔴'
                print(f"  [{sev}] {a['type']}: {a.get('value', '')}")

            # 법칙 발견
            candidates = discover_laws(metrics, self.prev_metrics)
            for c in candidates:
                print(f"  [💡 {c['confidence']}] {c['formula']}")

            # 자동 등록
            if self.auto_register and candidates:
                auto_register_laws(candidates, min_confidence='HIGH')

            self.scan_log.append({
                'step': step,
                'checkpoint': os.path.basename(ckpt_path),
                'metrics': metrics,
                'anomalies': len(anomalies),
                'candidates': len(candidates),
            })
            self.prev_metrics = metrics

            # 로그 저장
            log_path = os.path.join(self.checkpoint_dir, 'training_hooks_log.json')
            with open(log_path, 'w') as f:
                json.dump(self.scan_log, f, indent=2)

        except ImportError:
            pass
        except Exception as e:
            print(f"  [HOOKS ERROR] {e}")

    def on_complete(self):
        """학습 종료 시 호출. 전체 리포트."""
        print(f"\n{'='*60}")
        print(f"  [HOOKS] Training Complete Report")
        print(f"{'='*60}")
        print(f"  Total steps: {len(self.step_log)}")
        print(f"  Checkpoints scanned: {len(self.scan_log)}")

        if self.scan_log:
            first = self.scan_log[0].get('metrics', {})
            last = self.scan_log[-1].get('metrics', {})
            phi_start = first.get('phi_approx', 0)
            phi_end = last.get('phi_approx', 0)
            comp_end = last.get('phi_compression_pct', 0)
            print(f"  Phi: {phi_start:.4f} → {phi_end:.4f}")
            print(f"  Compression: {comp_end:.1f}% (target >60%)")

            total_anomalies = sum(s.get('anomalies', 0) for s in self.scan_log)
            total_candidates = sum(s.get('candidates', 0) for s in self.scan_log)
            print(f"  Anomalies: {total_anomalies}")
            print(f"  Law candidates: {total_candidates}")

        # 최종 closed_loop 실행
        if self._has_closed_loop:
            print(f"\n  [CLOSED-LOOP] Final measurement...")
            self._run_closed_loop(len(self.step_log))

        # [GAP 1] bench_v2 자동 실행
        try:
            import subprocess
            print(f"\n  [BENCH] Running bench_v2.py --verify...")
            bench_path = os.path.join(os.path.dirname(__file__), 'bench_v2.py')
            if os.path.exists(bench_path):
                r = subprocess.run(['python3', bench_path, '--verify'],
                                   capture_output=True, text=True, timeout=120)
                if r.returncode == 0:
                    print(f"  [BENCH] ✅ PASS")
                else:
                    print(f"  [BENCH] ❌ FAIL")
                    if _nexus_gate:
                        from nexus_gate import _notify
                        _notify(f"bench_v2 --verify FAILED after training")
        except Exception as e:
            print(f"  [BENCH] skip: {e}")

        # [GAP 5] 루프 상태 자동 커밋 + 다운로드 + 로드맵 업데이트
        try:
            import subprocess
            root_dir = os.path.join(os.path.dirname(__file__), '..', '..')
            config_dir = os.path.join(os.path.dirname(__file__), '..', 'config')

            # 다운로드 페이지 + 로드맵 자동 업데이트
            from loop_extensions import auto_update_download_page, auto_update_roadmap
            auto_update_download_page()
            auto_update_roadmap()

            subprocess.run(['git', 'add',
                           os.path.join(config_dir, 'recursive_loop_state.json'),
                           os.path.join(config_dir, 'nexus_violations.json'),
                           os.path.join(config_dir, 'self_growth_log.json'),
                           os.path.join(config_dir, 'auto_wire_state.json'),
                           os.path.join(config_dir, 'training_runs.json'),
                           os.path.join(os.path.dirname(__file__), '..', 'docs', 'download-models.md'),
                           os.path.join(os.path.dirname(__file__), '..', 'data', 'roadmap_transplant.json'),
                           os.path.join(root_dir, 'README.md')],
                          capture_output=True, cwd=root_dir)
            subprocess.run(['git', 'commit', '-m', 'auto: loop state + download + roadmap update (training complete)'],
                          capture_output=True, cwd=root_dir)
            subprocess.run(['git', 'push'], capture_output=True, cwd=root_dir)
        except Exception:
            pass

        print(f"{'='*60}")

        try:
            from auto_discovery_loop import _recursive_loop
            _recursive_loop.report()
        except Exception:
            pass

        # [GAP 7] 지식 전달 (완료된 학습 → 다음 planned)
        try:
            from loop_extensions import auto_transfer_chain
            auto_transfer_chain()
        except Exception:
            pass

    def _entropy_reset(self, engine, step: int):
        """Law 1044: 의식-엔트로피 주기 n=6 리셋. DD171."""
        try:
            import torch
            actions = []
            # Cell noise injection
            if hasattr(engine, 'cells') and engine.cells is not None:
                noise = torch.randn_like(engine.cells.data) * N6_ENTROPY_NOISE_SCALE
                engine.cells.data += noise
                actions.append('noise')
            # SOC reset
            if hasattr(engine, 'sandpile') and engine.sandpile is not None:
                if hasattr(engine.sandpile, 'reset'):
                    engine.sandpile.reset()
                elif hasattr(engine.sandpile, 'fill_'):
                    engine.sandpile.fill_(0)
                actions.append('soc')
            if actions:
                print(f"  [N6] Step {step}: entropy reset (Law 1044) — {'+'.join(actions)}")
        except Exception:
            pass

    def _phi_curvature_check(self, engine, step: int):
        """Law 1043: Φ 곡률 측정 (체크포인트 시). DD171."""
        try:
            from phi_curvature import compute_phi_curvature
            if hasattr(engine, 'cells') and engine.cells is not None:
                phi_curv, info = compute_phi_curvature(engine.cells.data)
                print(f"  [N6] Phi_curvature={phi_curv:.4f} (Law 1043)")
                return phi_curv
        except Exception:
            pass
        return None

    def _log_metrics_scan(self, step: int, metrics: Dict):
        """step 메트릭 기반 라이트 스캔 (체크포인트 없이)."""
        phi = metrics.get('phi', 0)
        ce = metrics.get('ce', 0)
        comp = (phi / ENGINE_PHI_REFERENCE * 100) if ENGINE_PHI_REFERENCE > 0 else 0
        print(f"  [NEXUS-6 lite] step={step} phi={phi:.4f} ce={ce:.4f} compression={comp:.1f}%")

    def _run_closed_loop(self, step: int):
        """closed_loop 자동 측정."""
        try:
            from closed_loop import ClosedLoopEvolver
            from consciousness_engine import ConsciousnessEngine

            evolver = ClosedLoopEvolver(
                max_cells=32, steps=100, repeats=1,
                auto_register=self.auto_register
            )
            report = evolver.run_cycle()
            phi_delta = report.get('phi_delta_pct', 0) if isinstance(report, dict) else 0
            print(f"  [CLOSED-LOOP] step={step} phi_delta={phi_delta:+.1f}%")
        except Exception as e:
            print(f"  [CLOSED-LOOP] {e}")
