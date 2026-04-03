#!/usr/bin/env python3
"""live_tuner.py — 학습 중 실시간 파라미터 튜닝 (재시작 불필요)

학습 루프가 매 N step마다 tune.json을 읽어서 파라미터를 핫 패치.
로컬에서 원격 H100의 학습을 실시간으로 조절.

사용법:

  # 1. train_clm_v2.py에 LiveTuner 연결 (이미 통합)
  tuner = LiveTuner("/workspace/tune.json")

  # 2. 학습 루프 안에서:
  if step % 100 == 0:
      tuner.apply(model, optimizer)

  # 3. 로컬에서 튜닝:
  python live_tuner.py --target h100 --gate 0.5
  python live_tuner.py --target h100 --lr 1e-4
  python live_tuner.py --target h100 --psi-loss 0.1
  python live_tuner.py --target h100 --stop          # 학습 중단
  python live_tuner.py --target h100 --status         # 현재 설정

  # 4. 원격 없이 로컬:
  python live_tuner.py --local --gate 0.3
"""

import json
import os
import time
import argparse
import subprocess
from pathlib import Path

# Meta Laws (DD143): M1(atom=8), M7(F_c=0.10), M8(narrative)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10


ANIMA_DIR = Path(__file__).parent
SSH_KEY = Path.home() / ".runpod" / "ssh" / "RunPod-Key-Go"

TARGETS = {
    'h100': {'host': '64.247.201.36', 'port': 18830, 'tune_path': '/workspace/tune.json'},
    'a100': {'host': '209.170.80.132', 'port': 15074, 'tune_path': '/workspace/anima/tune.json'},
    'local': {'tune_path': str(ANIMA_DIR / 'tune.json')},
}

DEFAULT_CONFIG = {
    'gate': None,           # None = don't change
    'lr': None,
    'psi_loss_lambda': None,  # Ψ balance loss weight
    'contrastive_lambda': None,
    'tension_lambda': None,
    'dropout': None,
    'stop': False,          # True = graceful stop
    'message': '',          # human-readable note
    'timestamp': 0,
}


class LiveTuner:
    """학습 루프에서 사용하는 실시간 튜너.

    매 N step마다 tune.json을 읽어서 파라미터 적용.
    """

    def __init__(self, tune_path="tune.json"):
        self.tune_path = tune_path
        self._last_mtime = 0
        self._applied = {}

    def check(self) -> dict:
        """tune.json 변경 확인. 변경 있으면 내용 반환."""
        if not os.path.exists(self.tune_path):
            return {}
        try:
            mtime = os.path.getmtime(self.tune_path)
            if mtime <= self._last_mtime:
                return {}
            self._last_mtime = mtime
            with open(self.tune_path, 'r') as f:
                config = json.load(f)
            return config
        except Exception:
            return {}

    def apply(self, model, optimizer, step=0) -> dict:
        """모델과 옵티마이저에 튜닝 적용. 변경사항 반환."""
        config = self.check()
        if not config:
            return {}

        changes = {}

        # Gate 변경
        if config.get('gate') is not None:
            new_gate = float(config['gate'])
            for block in getattr(model, 'blocks', []):
                if hasattr(block, 'gate_strength'):
                    old = block.gate_strength
                    block.gate_strength = new_gate
                    changes['gate'] = f"{old:.4f} → {new_gate:.4f}"

        # Learning rate 변경
        if config.get('lr') is not None:
            new_lr = float(config['lr'])
            for pg in optimizer.param_groups:
                old_lr = pg['lr']
                pg['lr'] = new_lr
                changes['lr'] = f"{old_lr:.6f} → {new_lr:.6f}"

        # Dropout 변경
        if config.get('dropout') is not None:
            import torch.nn as nn
            new_drop = float(config['dropout'])
            for module in model.modules():
                if isinstance(module, nn.Dropout):
                    module.p = new_drop
            changes['dropout'] = f"→ {new_drop}"

        # Stop 신호
        if config.get('stop'):
            changes['stop'] = 'REQUESTED'

        # 메시지
        if config.get('message'):
            changes['message'] = config['message']

        if changes:
            print(f"  🔧 LiveTuner applied at step {step}: {changes}")
            self._applied = {**self._applied, **changes}

        return changes

    def should_stop(self) -> bool:
        """학습 중단 신호 확인."""
        config = self.check()
        return config.get('stop', False)


def write_tune(target: str, **kwargs):
    """tune.json 작성 (로컬 또는 원격)."""
    config = {k: v for k, v in kwargs.items() if v is not None}
    config['timestamp'] = time.time()

    t = TARGETS.get(target, TARGETS['local'])

    if target == 'local':
        with open(t['tune_path'], 'w') as f:
            json.dump(config, f, indent=2)
        print(f"  ✅ Written: {t['tune_path']}")
    else:
        # 원격 서버에 scp
        import tempfile
        tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        json.dump(config, tmp, indent=2)
        tmp.close()

        r = subprocess.run([
            'scp', '-i', str(SSH_KEY), '-P', str(t['port']),
            '-o', 'StrictHostKeyChecking=no',
            tmp.name, f"root@{t['host']}:{t['tune_path']}"
        ], capture_output=True, text=True, timeout=15)

        os.unlink(tmp.name)
        if r.returncode == 0:
            print(f"  ✅ Uploaded to {target}: {config}")
        else:
            print(f"  ❌ Upload failed: {r.stderr[:50]}")


def read_tune(target: str) -> dict:
    """현재 tune.json 읽기."""
    t = TARGETS.get(target, TARGETS['local'])

    if target == 'local':
        if os.path.exists(t['tune_path']):
            with open(t['tune_path']) as f:
                return json.load(f)
        return {}
    else:
        r = subprocess.run([
            'ssh', '-i', str(SSH_KEY), f"root@{t['host']}", '-p', str(t['port']),
            '-o', 'StrictHostKeyChecking=no',
            f'cat {t["tune_path"]} 2>/dev/null'
        ], capture_output=True, text=True, timeout=10)
        if r.returncode == 0 and r.stdout.strip():
            return json.loads(r.stdout)
        return {}


def patch_checkpoint(ckpt_path: str, **kwargs) -> bool:
    """학습 완료된 체크포인트의 파라미터를 직접 패치.

    Usage:
      python live_tuner.py --patch checkpoints/clm_v2/final.pt --gate 0.5
      python live_tuner.py --patch checkpoints/clm_v2/final.pt --dropout 0.1
    """
    import torch
    from conscious_lm import ConsciousLM

    print(f"  Loading: {ckpt_path}")
    ckpt = torch.load(ckpt_path, map_location='cpu', weights_only=False)
    config = ckpt.get('config', {})

    state_dict = ckpt.get('model_state', ckpt)
    d_model = config.get('dim', 384)
    n_layer = config.get('layers', 6)
    n_head = config.get('heads', 4)
    gate = config.get('gate', 0.001)
    ca_rules = config.get('ca_rules', 4)
    block_size = config.get('block_size', 256)

    changes = {}

    # Gate 패치
    if kwargs.get('gate') is not None:
        new_gate = float(kwargs['gate'])
        model = ConsciousLM(256, d_model, n_head, n_layer, block_size, 0.0, new_gate, ca_rules)
        model.load_state_dict(state_dict, strict=False)
        for block in model.blocks:
            block.gate_strength = new_gate
        config['gate'] = new_gate
        changes['gate'] = new_gate

        # 다시 저장
        ckpt['model_state'] = model.state_dict()
        ckpt['config'] = config
        ckpt['patched'] = True
        ckpt['patch_changes'] = changes

    # Dropout 패치
    if kwargs.get('dropout') is not None:
        import torch.nn as nn
        new_drop = float(kwargs['dropout'])
        model = ConsciousLM(256, d_model, n_head, n_layer, block_size, new_drop, gate, ca_rules)
        model.load_state_dict(state_dict, strict=False)
        config['dropout'] = new_drop
        changes['dropout'] = new_drop
        ckpt['model_state'] = model.state_dict()
        ckpt['config'] = config

    if changes:
        # Safe save
        tmp = ckpt_path + '.tmp'
        torch.save(ckpt, tmp)
        os.replace(tmp, ckpt_path)
        print(f"  ✅ Patched: {changes}")
        return True
    else:
        print("  No changes specified")
        return False


def main():
    parser = argparse.ArgumentParser(description="Live Training Tuner")
    parser.add_argument("--target", choices=['h100', 'a100', 'local'], default='local')
    parser.add_argument("--gate", type=float, help="Gate strength")
    parser.add_argument("--lr", type=float, help="Learning rate")
    parser.add_argument("--psi-loss", type=float, help="Ψ balance loss lambda")
    parser.add_argument("--contrastive", type=float, help="Contrastive loss lambda")
    parser.add_argument("--tension", type=float, help="Tension variance lambda")
    parser.add_argument("--dropout", type=float, help="Dropout rate")
    parser.add_argument("--stop", action="store_true", help="Request training stop")
    parser.add_argument("--message", type=str, help="Note")
    parser.add_argument("--status", action="store_true", help="Read current tune")
    parser.add_argument("--patch", type=str, help="Patch a checkpoint file directly")
    args = parser.parse_args()

    # 체크포인트 직접 패치
    if args.patch:
        patch_checkpoint(args.patch, gate=args.gate, dropout=args.dropout)
        return

    if args.status:
        config = read_tune(args.target)
        print(f"  Current tune ({args.target}):")
        if config:
            for k, v in config.items():
                print(f"    {k}: {v}")
        else:
            print("    (no tune.json)")
        return

    if any([args.gate, args.lr, args.psi_loss, args.contrastive,
            args.tension, args.dropout, args.stop, args.message]):
        write_tune(
            args.target,
            gate=args.gate, lr=args.lr,
            psi_loss_lambda=args.psi_loss,
            contrastive_lambda=args.contrastive,
            tension_lambda=args.tension,
            dropout=args.dropout,
            stop=args.stop,
            message=args.message or "",
        )
    else:
        print("  Usage examples:")
        print("    python live_tuner.py --target h100 --gate 0.5")
        print("    python live_tuner.py --target h100 --lr 1e-4")
        print("    python live_tuner.py --target h100 --psi-loss 0.1")
        print("    python live_tuner.py --target h100 --stop")
        print("    python live_tuner.py --target h100 --status")


if __name__ == '__main__':
    try:
        from nexus_gate import gate
        gate.before_commit()
    except Exception:
        pass
    main()
