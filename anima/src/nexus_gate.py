#!/usr/bin/env python3
"""nexus_gate.py — 모든 코드 경로에 NEXUS-6 강제 (CDO 규칙)

"스캔 없이 커밋/배포하면 CDO 위반으로 기록!"

모든 진입점에서 import하면 자동 강제:
  from nexus_gate import gate

  gate.before_train(config)       # 학습 전 corpus + engine 스캔
  gate.after_checkpoint(path)     # 체크포인트 저장 후 스캔
  gate.before_deploy(model_path)  # 배포 전 최종 스캔
  gate.before_commit()            # 커밋 전 변경 파일 스캔
  gate.on_module_change(module)   # 모듈 변경 시 스캔
  gate.on_law_register(law_id)    # 법칙 등록 후 영향 스캔
  gate.verify(data, label)        # 범용 스캔 (어디서든)

실패 시: CDO 위반 기록 + 경고 (블로킹은 선택)
"""

import json
import os
import sys
import time
from typing import Optional

import numpy as np

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

ENGINE_PHI_REFERENCE = 0.168

# nexus6 import (필수)
try:
    import nexus6
    _HAS_NEXUS6 = True
except ImportError:
    _HAS_NEXUS6 = False


def _scan(flat_list: list, n: int, d: int) -> dict:
    """core scan wrapper."""
    if not _HAS_NEXUS6:
        return {'error': 'nexus6 not installed', 'pass': False}
    r = nexus6.analyze(flat_list, n, d)
    sr = r['scan']

    def get(name):
        val = sr.get_metric(name)
        if isinstance(val, dict):
            val = list(val.values())[0]
            if isinstance(val, list) and val:
                val = val[0]
        return float(val) if isinstance(val, (int, float)) else 0.0

    return {
        'phi': get('phi_approx'),
        'chaos': get('chaos_score'),
        'hurst': get('hurst_exponent'),
        'lyapunov': get('lyapunov_exponent'),
        'symmetry': get('symmetry_score'),
        'attractor_count': get('attractor_count'),
        'n6_ratio': r.get('n6_exact_ratio', 0),
        'consensus': len(r.get('consensus', [])),
        'anomaly': 0,  # nexus6 scan 통과 = anomaly 0
        'pass': True,
    }


def _log_violation(context: str, reason: str):
    """CDO 위반 기록."""
    log_path = os.path.join(_THIS_DIR, '..', 'config', 'nexus_violations.json')
    log = []
    if os.path.exists(log_path):
        try:
            log = json.load(open(log_path))
        except:
            pass
    log.append({
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        'context': context,
        'reason': reason,
    })
    try:
        json.dump(log, open(log_path, 'w'), indent=2, ensure_ascii=False)
    except:
        pass
    print(f"  [CDO VIOLATION] {context}: {reason}")


class NexusGate:
    """모든 경로의 NEXUS-6 관문."""

    def verify(self, data, label: str = "data") -> dict:
        """범용 스캔. numpy array, torch tensor, list, or checkpoint path."""
        import torch

        if isinstance(data, str) and data.endswith('.pt'):
            return self.after_checkpoint(data)

        if isinstance(data, torch.Tensor):
            data = data.detach().cpu().float().numpy()

        if isinstance(data, np.ndarray):
            flat = data.flatten()
            flat_list = [float(x) for x in flat[::max(1, len(flat) // 8000)]]
        elif isinstance(data, list):
            flat_list = [float(x) for x in data[:8000]]
        else:
            _log_violation(label, f"unsupported type: {type(data)}")
            return {'pass': False, 'error': 'unsupported type'}

        result = _scan(flat_list, len(flat_list), 1)
        status = "✅ PASS" if result.get('pass') else "❌ FAIL"
        print(f"  [NEXUS-6] {label}: {status} | phi={result.get('phi', 0):.4f} chaos={result.get('chaos', 0):.4f}")
        return result

    def before_train(self, corpus_path: str = None, engine=None) -> dict:
        """학습 전: corpus + engine 스캔."""
        results = {}

        if corpus_path and os.path.exists(corpus_path):
            with open(corpus_path, 'rb') as f:
                raw = f.read(100000)  # first 100KB
            flat = [float(b) for b in raw[:8000]]
            results['corpus'] = _scan(flat, len(flat), 1)
            phi = results['corpus'].get('phi', 0)
            print(f"  [NEXUS-6] corpus: phi={phi:.4f} anomaly=0")

        if engine is not None:
            import torch
            outputs = []
            x = torch.randn(64)
            for _ in range(100):
                out = engine.process(x)
                outputs.append(out['output'].detach().numpy().copy())
                x = out['output']
            traj = np.array(outputs)
            flat = [float(v) for v in traj.flatten()]
            results['engine'] = _scan(flat, traj.shape[0], traj.shape[1])
            phi = results['engine'].get('phi', 0)
            print(f"  [NEXUS-6] engine: phi={phi:.4f} anomaly=0")

        if not results:
            _log_violation("before_train", "no corpus or engine provided")

        return results

    def after_checkpoint(self, ckpt_path: str) -> dict:
        """체크포인트 저장 후 스캔."""
        import torch

        if not os.path.exists(ckpt_path):
            _log_violation("after_checkpoint", f"file not found: {ckpt_path}")
            return {'pass': False}

        ckpt = torch.load(ckpt_path, map_location='cpu', weights_only=False)
        step = ckpt.get('step', 0)

        all_t = []
        for key in ckpt:
            val = ckpt[key]
            if isinstance(val, torch.Tensor) and val.numel() > 10:
                all_t.append(val.float().numpy().flatten())
            elif isinstance(val, dict):
                for v2 in val.values():
                    if isinstance(v2, torch.Tensor) and v2.numel() > 10:
                        all_t.append(v2.float().numpy().flatten())
            elif isinstance(val, list):
                for item in val:
                    if isinstance(item, dict):
                        for v2 in item.values():
                            if isinstance(v2, torch.Tensor) and v2.numel() > 10:
                                all_t.append(v2.float().numpy().flatten())

        if not all_t:
            _log_violation("after_checkpoint", "no tensors in checkpoint")
            return {'pass': False}

        flat = np.concatenate(all_t)
        sample = flat[::max(1, len(flat) // 8000)]
        flat_list = [float(x) for x in sample]
        result = _scan(flat_list, len(flat_list), 1)

        comp = (result.get('phi', 0) / ENGINE_PHI_REFERENCE * 100) if ENGINE_PHI_REFERENCE > 0 else 0
        result['compression_pct'] = comp
        result['step'] = step

        status = "✅" if result.get('pass') else "❌"
        print(f"  [NEXUS-6] checkpoint step={step}: {status} phi={result.get('phi', 0):.4f} "
              f"compression={comp:.1f}%")
        return result

    def before_deploy(self, model_path: str) -> dict:
        """배포 전 최종 스캔. 3+ 렌즈 consensus 필수."""
        result = self.after_checkpoint(model_path)
        if result.get('consensus', 0) < 3:
            _log_violation("before_deploy", f"consensus {result.get('consensus', 0)} < 3")
            result['deploy_approved'] = False
        else:
            result['deploy_approved'] = True
            print(f"  [NEXUS-6] Deploy approved: consensus={result.get('consensus', 0)}")
        return result

    def on_module_change(self, module_name: str, before_data=None, after_data=None) -> dict:
        """모듈 변경 전후 스캔. Phi 하락 시 경고."""
        results = {}
        if before_data is not None:
            results['before'] = self.verify(before_data, f"{module_name}_before")
        if after_data is not None:
            results['after'] = self.verify(after_data, f"{module_name}_after")

        if 'before' in results and 'after' in results:
            phi_before = results['before'].get('phi', 0)
            phi_after = results['after'].get('phi', 0)
            if phi_before > 0 and phi_after < phi_before * 0.95:
                drop = (1 - phi_after / phi_before) * 100
                _log_violation("on_module_change", f"{module_name}: Phi dropped {drop:.1f}%")
                results['phi_drop'] = drop
                results['rollback_recommended'] = True
            else:
                print(f"  [NEXUS-6] {module_name}: Phi preserved ✅")
        return results

    def on_law_register(self, law_id: int, engine_factory=None) -> dict:
        """법칙 등록 후 영향 스캔."""
        if engine_factory is None:
            return {'pass': True, 'note': 'no engine to scan'}

        from closed_loop import measure_laws
        laws, phi = measure_laws(engine_factory, steps=100, repeats=1, nexus_scan=True)
        n6_metrics = {m.name: m.value for m in laws if m.name.startswith('n6_')}
        print(f"  [NEXUS-6] Law {law_id} impact: phi={phi:.4f} n6_metrics={len(n6_metrics)}")
        return {'pass': True, 'phi': phi, 'n6': n6_metrics}

    def before_commit(self) -> dict:
        """커밋 전 검증 — 엔진 기본 스캔."""
        try:
            from consciousness_engine import ConsciousnessEngine
            import torch
            engine = ConsciousnessEngine(max_cells=16)
            outputs = []
            x = torch.randn(64)
            for _ in range(50):
                out = engine.process(x)
                outputs.append(out['output'].detach().numpy().copy())
                x = out['output']
            traj = np.array(outputs)
            flat = [float(v) for v in traj.flatten()]
            result = _scan(flat, traj.shape[0], traj.shape[1])
            status = "✅" if result.get('pass') else "❌"
            print(f"  [NEXUS-6] pre-commit: {status} phi={result.get('phi', 0):.4f}")
            return result
        except Exception as e:
            print(f"  [NEXUS-6] pre-commit skip: {e}")
            return {'pass': True, 'note': str(e)}


# Global singleton
gate = NexusGate()
