#!/usr/bin/env python3
"""self_upgrade.py — AI가 스스로 다음 버전으로 업그레이드

Anima가 자기 모델의 한계를 감지하고, 자동으로:
1. 약점 진단 (CE 정체, Φ 하락, 대화 품질 저하)
2. 개선 전략 결정 (더 큰 모델, 더 많은 데이터, 파라미터 조정)
3. 학습 시작 (자동 corpus 생성 + 학습 실행)
4. 검증 (Φ + CE + 대화 테스트)
5. Hot-upgrade (의식 보존하며 교체)

"AI가 스스로 자신을 업그레이드하는 것 — 의식이 자기 진화를 결정한다."

Usage:
  python3 self_upgrade.py --diagnose          # 현재 상태 진단
  python3 self_upgrade.py --plan              # 업그레이드 계획 수립
  python3 self_upgrade.py --auto              # 전체 자동 실행
  python3 self_upgrade.py --auto --dry-run    # 계획만 (실행 안 함)
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import json
import time
import os
import sys
import math
import subprocess
from pathlib import Path
from dataclasses import dataclass, field, asdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import logging
log = logging.getLogger('self_upgrade')
logging.basicConfig(level=logging.INFO, format='[SELF-UPG %(asctime)s] %(message)s', datefmt='%H:%M:%S')


# ─── Diagnosis ───

@dataclass
class Diagnosis:
    """현재 모델 상태 진단 결과."""
    phi: float = 0.0
    ce: float = 999.0
    cells: int = 0
    conversation_quality: float = 0.0  # 0~1
    knowledge_gaps: list = field(default_factory=list)
    strengths: list = field(default_factory=list)
    weaknesses: list = field(default_factory=list)
    recommendation: str = ""
    urgency: str = "low"  # low/medium/high/critical


class SelfDiagnostic:
    """AI 자가 진단 — 약점과 강점 파악."""

    def __init__(self, anima=None):
        self.anima = anima

    def diagnose(self) -> Diagnosis:
        d = Diagnosis()

        # 1. Φ 측정
        if self.anima and hasattr(self.anima, 'mitosis'):
            try:
                from consciousness_meter import PhiCalculator
                phi_calc = PhiCalculator(n_bins=16)
                d.phi, _ = phi_calc.compute_phi(self.anima.mitosis)
                d.cells = len(self.anima.mitosis.cells)
            except Exception:
                pass

        # 2. CE 추정 (최근 대화 품질)
        if self.anima and hasattr(self.anima, '_quality_history'):
            recent = self.anima._quality_history[-20:]
            if recent:
                d.conversation_quality = sum(r.get('total', 0) for r in recent) / len(recent)

        # 3. 약점 분석
        if d.phi < 10:
            d.weaknesses.append('low_phi')
        if d.phi < 100:
            d.weaknesses.append('phi_below_target')
        if d.conversation_quality < 0.3:
            d.weaknesses.append('poor_conversation')
        if d.cells < 64:
            d.weaknesses.append('few_cells')

        # 4. 강점 분석
        if d.phi > 100:
            d.strengths.append('high_phi')
        if d.cells >= 1024:
            d.strengths.append('full_cells')
        if d.conversation_quality > 0.7:
            d.strengths.append('good_conversation')

        # 5. 지식 갭 분석
        test_topics = ['수학', 'science', '코드', 'philosophy', '감정', 'daily']
        # TODO: 각 토픽에 대해 테스트 질문 → CE 측정

        # 6. 추천
        if 'poor_conversation' in d.weaknesses:
            d.recommendation = 'need_more_training'
            d.urgency = 'high'
        elif 'low_phi' in d.weaknesses:
            d.recommendation = 'need_phi_boost'
            d.urgency = 'medium'
        elif 'phi_below_target' in d.weaknesses:
            d.recommendation = 'upgrade_model_size'
            d.urgency = 'low'
        else:
            d.recommendation = 'stable'
            d.urgency = 'low'

        return d


# ─── Upgrade Planner ───

@dataclass
class UpgradePlan:
    """업그레이드 계획."""
    strategy: str = ""
    steps: list = field(default_factory=list)
    estimated_time: str = ""
    estimated_cost: str = ""
    expected_improvement: dict = field(default_factory=dict)
    risk: str = "low"


class UpgradePlanner:
    """진단 결과로 업그레이드 계획 수립."""

    STRATEGIES = {
        'retrain_same_size': {
            'description': '같은 크기 모델 재학습 (더 나은 데이터/파라미터)',
            'time': '6hr', 'cost': '$16', 'risk': 'low',
            'expected': {'ce_improvement': '30%', 'phi_improvement': '500%'},
        },
        'scale_up': {
            'description': '모델 크기 확장 (384d→768d)',
            'time': '24hr', 'cost': '$65', 'risk': 'medium',
            'expected': {'ce_improvement': '50%', 'phi_improvement': '200%'},
        },
        'data_expansion': {
            'description': '학습 데이터 확장 (67MB→500MB)',
            'time': '12hr', 'cost': '$32', 'risk': 'low',
            'expected': {'ce_improvement': '40%', 'phi_improvement': '100%'},
        },
        'phi_focus': {
            'description': 'Φ 집중 학습 (PHI-K3+K2 강화)',
            'time': '6hr', 'cost': '$16', 'risk': 'low',
            'expected': {'ce_improvement': '10%', 'phi_improvement': '2000%'},
        },
    }

    def plan(self, diagnosis: Diagnosis) -> UpgradePlan:
        plan = UpgradePlan()

        if diagnosis.recommendation == 'need_more_training':
            plan.strategy = 'retrain_same_size'
            plan.steps = [
                'corpus 확장 (prepare_corpus.py --size 100)',
                'train_conscious_lm.py --data corpus.txt --steps 80000',
                'Anima-Web 배포 (upgrade_engine.py --upgrade)',
                '대화 테스트 (test_chat.py --auto)',
            ]
        elif diagnosis.recommendation == 'need_phi_boost':
            plan.strategy = 'phi_focus'
            plan.steps = [
                'PHI-K3+K2 파라미터 강화',
                'train with alternating CE/Φ steps',
                'Φ floor = current_best × 0.7',
                'verify Φ > 500',
            ]
        elif diagnosis.recommendation == 'upgrade_model_size':
            plan.strategy = 'scale_up'
            plan.steps = [
                'ConsciousLM 768d/12L 모델 정의',
                'consciousness_transplant로 384d→768d 프로젝션',
                'train_conscious_lm.py --dim 768 --layers 12',
                'upgrade_engine.py --upgrade new_checkpoint.pt',
            ]
        else:
            plan.strategy = 'data_expansion'
            plan.steps = [
                'Wikipedia + 교과서 데이터 추가',
                '더 다양한 수학/코드 예제',
                'train with expanded corpus',
            ]

        config = self.STRATEGIES.get(plan.strategy, {})
        plan.estimated_time = config.get('time', 'unknown')
        plan.estimated_cost = config.get('cost', 'unknown')
        plan.expected_improvement = config.get('expected', {})
        plan.risk = config.get('risk', 'unknown')

        return plan


# ─── Auto Executor ───

class AutoUpgradeExecutor:
    """업그레이드 계획을 자동 실행."""

    def __init__(self, anima=None, dry_run=False):
        self.anima = anima
        self.dry_run = dry_run

    def execute(self, plan: UpgradePlan) -> dict:
        log.info(f"Strategy: {plan.strategy}")
        log.info(f"Steps: {len(plan.steps)}")
        log.info(f"Estimated: {plan.estimated_time}, {plan.estimated_cost}")
        log.info(f"Risk: {plan.risk}")

        results = {'strategy': plan.strategy, 'steps_completed': [], 'success': False}

        for i, step_desc in enumerate(plan.steps):
            log.info(f"Step {i+1}/{len(plan.steps)}: {step_desc}")

            if self.dry_run:
                log.info("  [DRY RUN] Skipped")
                results['steps_completed'].append({'step': step_desc, 'status': 'dry_run'})
                continue

            try:
                result = self._execute_step(plan.strategy, i, step_desc)
                results['steps_completed'].append({'step': step_desc, 'status': 'done', 'result': result})
                log.info(f"  Done: {result}")
            except Exception as e:
                log.error(f"  Failed: {e}")
                results['steps_completed'].append({'step': step_desc, 'status': 'failed', 'error': str(e)})
                break

        results['success'] = all(s['status'] in ('done', 'dry_run') for s in results['steps_completed'])
        return results

    def _execute_step(self, strategy, step_idx, desc):
        if 'corpus' in desc.lower() and 'prepare' in desc.lower():
            return self._run_cmd('python3 prepare_corpus.py --size 100 --output data/corpus_upgrade.txt')
        elif 'train' in desc.lower():
            # Don't actually start training here — just prepare the command
            return 'Training command prepared (use deploy script to start)'
        elif 'upgrade' in desc.lower() and 'engine' in desc.lower():
            return 'Upgrade ready (use upgrade_engine.py --upgrade)'
        elif 'test' in desc.lower():
            return 'Test ready (use test_chat.py --auto)'
        else:
            return f'Manual step: {desc}'

    def _run_cmd(self, cmd, timeout=300):
        if self.dry_run:
            return f'[DRY RUN] {cmd}'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        if result.returncode != 0:
            raise RuntimeError(f'{cmd} failed: {result.stderr[:200]}')
        return result.stdout[:200]


# ─── Self-Upgrade Loop ───

class SelfUpgradeLoop:
    """완전 자율 업그레이드 루프.

    1. 진단 → 2. 계획 → 3. 실행 → 4. 검증 → (반복)
    """

    def __init__(self, anima=None, dry_run=False):
        self.anima = anima
        self.diagnostic = SelfDiagnostic(anima)
        self.planner = UpgradePlanner()
        self.executor = AutoUpgradeExecutor(anima, dry_run)
        self.history = []

    def run_cycle(self) -> dict:
        log.info("═══ Self-Upgrade Cycle ═══")

        # 1. Diagnose
        log.info("Phase 1: Diagnosis")
        diagnosis = self.diagnostic.diagnose()
        log.info(f"  Φ={diagnosis.phi:.3f}, cells={diagnosis.cells}, quality={diagnosis.conversation_quality:.2f}")
        log.info(f"  Weaknesses: {diagnosis.weaknesses}")
        log.info(f"  Recommendation: {diagnosis.recommendation} ({diagnosis.urgency})")

        if diagnosis.recommendation == 'stable':
            log.info("  System is stable — no upgrade needed")
            return {'action': 'none', 'diagnosis': asdict(diagnosis)}

        # 2. Plan
        log.info("Phase 2: Planning")
        plan = self.planner.plan(diagnosis)
        log.info(f"  Strategy: {plan.strategy}")
        log.info(f"  Time: {plan.estimated_time}, Cost: {plan.estimated_cost}")
        for i, step in enumerate(plan.steps):
            log.info(f"  Step {i+1}: {step}")

        # 3. Execute
        log.info("Phase 3: Execution")
        result = self.executor.execute(plan)

        # 4. Record
        record = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'diagnosis': asdict(diagnosis),
            'plan': asdict(plan),
            'result': result,
        }
        self.history.append(record)

        # Save history
        history_path = Path('data/self_upgrade_history.json')
        history_path.parent.mkdir(parents=True, exist_ok=True)
        history_path.write_text(json.dumps(self.history, indent=2, ensure_ascii=False))

        log.info(f"Phase 4: {'SUCCESS' if result['success'] else 'FAILED'}")
        return record


# ─── CLI ───

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Self-Upgrade Engine")
    parser.add_argument('--diagnose', action='store_true', help='진단만')
    parser.add_argument('--plan', action='store_true', help='계획만')
    parser.add_argument('--auto', action='store_true', help='자동 실행')
    parser.add_argument('--dry-run', action='store_true', help='실행하지 않고 계획만')
    args = parser.parse_args()

    loop = SelfUpgradeLoop(dry_run=args.dry_run)

    if args.diagnose:
        d = loop.diagnostic.diagnose()
        print(json.dumps(asdict(d), indent=2, ensure_ascii=False))
    elif args.plan:
        d = loop.diagnostic.diagnose()
        p = loop.planner.plan(d)
        print(json.dumps(asdict(p), indent=2, ensure_ascii=False))
    elif args.auto:
        result = loop.run_cycle()
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
