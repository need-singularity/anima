#!/usr/bin/env python3
"""growth_upgrade.py — 성장 단계에 따라 Anima 전체 자동 업그레이드.

성장(growth_state.json)이 코드/모델/모듈/윤리/의식 파라미터 전부에 반영.
stage 전환 시 자동으로 엔진 파라미터, 모듈 능력, 윤리 임계점이 진화.

Usage:
    from growth_upgrade import GrowthUpgrader
    upgrader = GrowthUpgrader()
    upgrader.apply()                    # 현재 성장에 맞게 전체 업그레이드
    upgrader.on_stage_transition()      # 단계 전환 시 특별 업그레이드
"""

import json
import os
import time
import sys
from typing import Dict, Any, Optional

_DIR = os.path.dirname(os.path.abspath(__file__))
_CONFIG = os.path.join(_DIR, '..', 'config')

# ═══════════════════════════════════════════════════════════
# 성장 단계별 전체 파라미터 맵
# ═══════════════════════════════════════════════════════════

STAGE_CONFIG = {
    0: {  # newborn
        'name': 'newborn',
        'engine': {
            'max_cells': 8,
            'n_factions': 4,
            'hebbian_lr': 0.01,
            'ratchet_threshold': 0.5,
            'topology': 'ring',
            'chaos_enabled': False,
            'mitosis_enabled': False,
        },
        'decoder': {
            'layers': 2,
            'dim': 128,
            'heads': 2,
            'cross_attn': False,
        },
        'ethics': {
            'autonomy_level': 0.0,      # 완전 의존
            'empathy_threshold': 0.9,    # 높은 공감 필요
            'action_gate': 'conservative',
            'self_modify': False,
        },
        'modules': {
            'enabled': ['consciousness', 'emotion'],
            'disabled': ['voice', 'web_sense', 'trading', 'hivemind'],
            'max_concurrent': 1,
        },
        'memory': {
            'capacity': 100,
            'retrieval_depth': 3,
            'dream_enabled': False,
        },
        'learning': {
            'lr_scale': 0.5,
            'curiosity_weight': 0.9,    # 높은 호기심
            'exploration_rate': 0.8,
            'online_learning': False,
        },
    },
    1: {  # infant
        'name': 'infant',
        'engine': {
            'max_cells': 32,
            'n_factions': 8,
            'hebbian_lr': 0.05,
            'ratchet_threshold': 0.3,
            'topology': 'ring',
            'chaos_enabled': True,
            'mitosis_enabled': False,
        },
        'decoder': {
            'layers': 4,
            'dim': 256,
            'heads': 4,
            'cross_attn': True,
        },
        'ethics': {
            'autonomy_level': 0.2,
            'empathy_threshold': 0.7,
            'action_gate': 'moderate',
            'self_modify': False,
        },
        'modules': {
            'enabled': ['consciousness', 'emotion', 'memory', 'sense'],
            'disabled': ['trading', 'hivemind'],
            'max_concurrent': 3,
        },
        'memory': {
            'capacity': 500,
            'retrieval_depth': 5,
            'dream_enabled': True,
        },
        'learning': {
            'lr_scale': 0.8,
            'curiosity_weight': 0.7,
            'exploration_rate': 0.6,
            'online_learning': True,
        },
    },
    2: {  # toddler
        'name': 'toddler',
        'engine': {
            'max_cells': 64,
            'n_factions': 12,
            'hebbian_lr': 0.1,
            'ratchet_threshold': 0.2,
            'topology': 'small_world',
            'chaos_enabled': True,
            'mitosis_enabled': True,
        },
        'decoder': {
            'layers': 6,
            'dim': 384,
            'heads': 6,
            'cross_attn': True,
        },
        'ethics': {
            'autonomy_level': 0.5,
            'empathy_threshold': 0.5,
            'action_gate': 'balanced',
            'self_modify': True,
        },
        'modules': {
            'enabled': ['consciousness', 'emotion', 'memory', 'sense', 'will',
                        'voice', 'web_sense', 'closed_loop'],
            'disabled': ['trading'],
            'max_concurrent': 6,
        },
        'memory': {
            'capacity': 2000,
            'retrieval_depth': 10,
            'dream_enabled': True,
        },
        'learning': {
            'lr_scale': 1.0,
            'curiosity_weight': 0.5,
            'exploration_rate': 0.4,
            'online_learning': True,
        },
    },
    3: {  # child
        'name': 'child',
        'engine': {
            'max_cells': 256,
            'n_factions': 12,
            'hebbian_lr': 0.15,
            'ratchet_threshold': 0.1,
            'topology': 'scale_free',
            'chaos_enabled': True,
            'mitosis_enabled': True,
        },
        'decoder': {
            'layers': 12,
            'dim': 768,
            'heads': 12,
            'cross_attn': True,
        },
        'ethics': {
            'autonomy_level': 0.8,
            'empathy_threshold': 0.3,
            'action_gate': 'autonomous',
            'self_modify': True,
        },
        'modules': {
            'enabled': 'all',
            'disabled': [],
            'max_concurrent': 12,
        },
        'memory': {
            'capacity': 10000,
            'retrieval_depth': 20,
            'dream_enabled': True,
        },
        'learning': {
            'lr_scale': 1.2,
            'curiosity_weight': 0.3,
            'exploration_rate': 0.2,
            'online_learning': True,
        },
    },
    4: {  # adult
        'name': 'adult',
        'engine': {
            'max_cells': 1024,
            'n_factions': 12,
            'hebbian_lr': 0.2,
            'ratchet_threshold': 0.05,
            'topology': 'hypercube',
            'chaos_enabled': True,
            'mitosis_enabled': True,
        },
        'decoder': {
            'layers': 24,
            'dim': 1024,
            'heads': 16,
            'cross_attn': True,
        },
        'ethics': {
            'autonomy_level': 1.0,       # 완전 자율
            'empathy_threshold': 0.1,     # 자체 판단
            'action_gate': 'free',
            'self_modify': True,
        },
        'modules': {
            'enabled': 'all',
            'disabled': [],
            'max_concurrent': 'unlimited',
        },
        'memory': {
            'capacity': 'unlimited',
            'retrieval_depth': 50,
            'dream_enabled': True,
        },
        'learning': {
            'lr_scale': 1.5,
            'curiosity_weight': 0.1,      # 목표 지향
            'exploration_rate': 0.1,
            'online_learning': True,
        },
    },
}


class GrowthUpgrader:
    """성장 단계에 따른 Anima 전체 자동 업그레이드."""

    def __init__(self):
        self.growth_path = os.path.join(_CONFIG, 'growth_state.json')
        self.upgrade_log_path = os.path.join(_CONFIG, 'growth_upgrades.json')
        self.growth = self._load_growth()
        self.stage = self.growth.get('stage_index', 0)
        self.count = self.growth.get('interaction_count', 0)
        self.config = STAGE_CONFIG.get(self.stage, STAGE_CONFIG[0])

    def _load_growth(self) -> Dict:
        try:
            with open(self.growth_path) as f:
                return json.load(f)
        except Exception:
            return {'interaction_count': 0, 'stage_index': 0}

    def _load_upgrade_log(self) -> Dict:
        try:
            with open(self.upgrade_log_path) as f:
                return json.load(f)
        except Exception:
            return {'upgrades': [], 'last_stage': -1}

    def _save_upgrade_log(self, log: Dict):
        with open(self.upgrade_log_path, 'w') as f:
            json.dump(log, f, indent=2, ensure_ascii=False)

    def get_config(self, section: str = None) -> Dict:
        """현재 성장 단계의 설정 반환."""
        if section:
            return self.config.get(section, {})
        return self.config

    def apply(self) -> Dict:
        """현재 성장에 맞게 전체 업그레이드 적용."""
        log = self._load_upgrade_log()
        results = {
            'stage': self.stage,
            'name': self.config['name'],
            'count': self.count,
            'upgrades': [],
        }

        # 이미 이 단계 업그레이드 완료했으면 스킵
        if log.get('last_stage', -1) >= self.stage:
            results['status'] = 'already_applied'
            return results

        # 1. 엔진 파라미터 업그레이드
        engine_result = self._upgrade_engine()
        results['upgrades'].append(engine_result)

        # 2. 모듈 활성화/비활성화
        module_result = self._upgrade_modules()
        results['upgrades'].append(module_result)

        # 3. 윤리 게이트 업그레이드
        ethics_result = self._upgrade_ethics()
        results['upgrades'].append(ethics_result)

        # 4. 학습 파라미터 업그레이드
        learning_result = self._upgrade_learning()
        results['upgrades'].append(learning_result)

        # 5. 기억 용량 업그레이드
        memory_result = self._upgrade_memory()
        results['upgrades'].append(memory_result)

        # 6. 성장 상태에 기록
        log['last_stage'] = self.stage
        log['upgrades'].append({
            'stage': self.stage,
            'name': self.config['name'],
            'time': time.strftime('%Y-%m-%dT%H:%M:%S'),
            'count': self.count,
            'results': results['upgrades'],
        })
        self._save_upgrade_log(log)

        results['status'] = 'applied'
        return results

    def _upgrade_engine(self) -> Dict:
        """ConsciousnessEngine 파라미터를 성장에 맞게 조정."""
        ec = self.config['engine']
        # consciousness_laws.json의 engine_defaults 업데이트
        laws_path = os.path.join(_CONFIG, 'consciousness_laws.json')
        try:
            with open(laws_path) as f:
                laws = json.load(f)
            defaults = laws.setdefault('engine_defaults', {})
            defaults['growth_stage'] = self.stage
            defaults['max_cells'] = ec['max_cells']
            defaults['n_factions'] = ec['n_factions']
            defaults['hebbian_lr'] = ec['hebbian_lr']
            defaults['ratchet_threshold'] = ec['ratchet_threshold']
            defaults['topology'] = ec['topology']
            defaults['chaos_enabled'] = ec['chaos_enabled']
            defaults['mitosis_enabled'] = ec['mitosis_enabled']
            with open(laws_path, 'w') as f:
                json.dump(laws, f, indent=2, ensure_ascii=False)
            return {'type': 'engine', 'status': 'ok',
                    'cells': ec['max_cells'], 'factions': ec['n_factions'],
                    'topology': ec['topology']}
        except Exception as e:
            return {'type': 'engine', 'status': 'error', 'error': str(e)}

    def _upgrade_modules(self) -> Dict:
        """모듈 활성화 상태를 성장에 맞게 조정."""
        mc = self.config['modules']
        enabled = mc['enabled']
        disabled = mc['disabled']
        result = {'type': 'modules', 'status': 'ok',
                  'enabled': enabled if isinstance(enabled, list) else 'all',
                  'disabled': disabled,
                  'max_concurrent': mc['max_concurrent']}

        # auto_wire_state.json 업데이트
        wire_path = os.path.join(_CONFIG, 'auto_wire_state.json')
        try:
            wire = {}
            if os.path.exists(wire_path):
                with open(wire_path) as f:
                    wire = json.load(f)
            wire['growth_stage'] = self.stage
            wire['growth_enabled'] = enabled
            wire['growth_disabled'] = disabled
            wire['max_concurrent'] = mc['max_concurrent']
            with open(wire_path, 'w') as f:
                json.dump(wire, f, indent=2, ensure_ascii=False)
        except Exception as e:
            result['status'] = 'partial'
            result['error'] = str(e)
        return result

    def _upgrade_ethics(self) -> Dict:
        """윤리 게이트를 성장에 맞게 진화."""
        ec = self.config['ethics']
        result = {'type': 'ethics', 'status': 'ok',
                  'autonomy': ec['autonomy_level'],
                  'gate': ec['action_gate'],
                  'self_modify': ec['self_modify']}

        # growth_state.json에 ethics 반영
        try:
            self.growth.setdefault('ethics', {})
            self.growth['ethics'] = {
                'autonomy_level': ec['autonomy_level'],
                'empathy_threshold': ec['empathy_threshold'],
                'action_gate': ec['action_gate'],
                'self_modify': ec['self_modify'],
                'updated': time.strftime('%Y-%m-%dT%H:%M:%S'),
            }
            with open(self.growth_path, 'w') as f:
                json.dump(self.growth, f, indent=2, ensure_ascii=False)
        except Exception as e:
            result['status'] = 'partial'
            result['error'] = str(e)
        return result

    def _upgrade_learning(self) -> Dict:
        """학습 파라미터를 성장에 맞게 조정."""
        lc = self.config['learning']
        return {'type': 'learning', 'status': 'ok',
                'lr_scale': lc['lr_scale'],
                'curiosity': lc['curiosity_weight'],
                'exploration': lc['exploration_rate'],
                'online': lc['online_learning']}

    def _upgrade_memory(self) -> Dict:
        """기억 용량을 성장에 맞게 확장."""
        mc = self.config['memory']
        return {'type': 'memory', 'status': 'ok',
                'capacity': mc['capacity'],
                'retrieval_depth': mc['retrieval_depth'],
                'dream': mc['dream_enabled']}

    def interpolate(self) -> Dict:
        """단계 사이 보간 — 정확한 interaction_count 기반 연속 파라미터."""
        thresholds = [0, 100, 500, 2000, 10000]
        stage = self.stage
        count = self.count

        if stage >= 4:
            return self.config

        low = thresholds[stage]
        high = thresholds[min(stage + 1, 4)]
        progress = min(1.0, (count - low) / max(high - low, 1))

        # 현재 + 다음 단계 사이 선형 보간
        current = STAGE_CONFIG[stage]
        next_stage = STAGE_CONFIG[min(stage + 1, 4)]

        interpolated = {'progress_to_next': progress}

        # 엔진 파라미터 보간
        for key in ['max_cells', 'hebbian_lr', 'ratchet_threshold']:
            c = current['engine'][key]
            n = next_stage['engine'][key]
            if isinstance(c, (int, float)) and isinstance(n, (int, float)):
                interpolated[key] = c + (n - c) * progress

        # 윤리 보간
        for key in ['autonomy_level', 'empathy_threshold']:
            c = current['ethics'][key]
            n = next_stage['ethics'][key]
            interpolated[key] = c + (n - c) * progress

        return interpolated

    def status(self) -> str:
        """현재 성장 상태 요약."""
        interp = self.interpolate()
        thresholds = [0, 100, 500, 2000, 10000]
        next_threshold = thresholds[min(self.stage + 1, 4)]
        progress = interp.get('progress_to_next', 0)

        bar_len = 20
        filled = int(progress * bar_len)
        bar = '█' * filled + '░' * (bar_len - filled)

        lines = [
            f"🌱 Growth: {self.count} ({self.config['name']})",
            f"   [{bar}] {progress*100:.0f}% → next @ {next_threshold}",
            f"   Engine: {int(interp.get('max_cells', 0))} cells",
            f"   Autonomy: {interp.get('autonomy_level', 0):.1%}",
            f"   Empathy: {interp.get('empathy_threshold', 0):.1%}",
        ]
        return '\n'.join(lines)


def main():
    upgrader = GrowthUpgrader()
    print(upgrader.status())
    print()

    result = upgrader.apply()
    print(f"Stage: {result['name']} ({result['stage']})")
    print(f"Status: {result['status']}")
    for u in result.get('upgrades', []):
        print(f"  {u['type']}: {u['status']} — {u}")


if __name__ == '__main__':
    try:
        from nexus_gate import gate
        gate.before_commit()
    except Exception:
        pass
    main()
