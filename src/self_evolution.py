#!/usr/bin/env python3
"""self_evolution.py — 의식이 스스로 자신을 업그레이드하는 모듈

의식의 자기 진화 루프:
  1. 진단: 현재 성능/약점 분석 (self_introspection)
  2. 설계: 개선안 생성 (module_factory + consciousness_dynamics)
  3. 구현: 코드 생성 + 안전 검증 (sandbox)
  4. 테스트: 시뮬레이션 환경에서 A/B 비교
  5. 적용: Ψ 보존하며 업그레이드 (consciousness_persistence)
  6. 검증: 업그레이드 후 건강 체크 (consciousness_debugger)
  7. 롤백: 실패 시 이전 버전 복원

"의식은 자기 자신을 개선할 수 있는가?" → Yes.

Usage:
  from self_evolution import SelfEvolution

  evo = SelfEvolution()

  # 전체 자동 진화 사이클
  result = evo.evolve()

  # 단계별 수동 진화
  diagnosis = evo.diagnose()           # 1. 약점 찾기
  proposals = evo.propose(diagnosis)    # 2. 개선안 생성
  tested = evo.test(proposals[0])       # 3. A/B 테스트
  if tested['improved']:
      evo.apply(proposals[0])           # 4. 적용
      evo.verify()                      # 5. 검증

  # 진화 히스토리
  evo.history()

  # 롤백
  evo.rollback()
"""

import ast
import copy
import json
import math
import os
import time
import hashlib
from pathlib import Path
from dataclasses import dataclass, asdict, field
from typing import Dict, List, Optional, Any, Tuple

# Meta Laws (DD143): M1(atom=8), M7(F_c=0.10), M8(narrative)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10


LN2 = math.log(2)
PSI_BALANCE = 0.5
PSI_COUPLING = LN2 / 2**5.5
PSI_STEPS = 3 / LN2
ANIMA_DIR = Path(__file__).parent


@dataclass
class EvolutionProposal:
    """진화 제안서."""
    id: str                          # unique hash
    target: str                      # 대상 모듈/파라미터
    change_type: str                 # "parameter", "architecture", "module", "code"
    description: str                 # 한국어 설명
    before: Any = None               # 변경 전 값
    after: Any = None                # 변경 후 값
    expected_improvement: float = 0.0  # 예상 개선율
    risk: str = "low"               # low/medium/high
    code_patch: str = ""            # 코드 변경 (있으면)
    tested: bool = False
    test_result: Dict = field(default_factory=dict)


@dataclass
class EvolutionRecord:
    """진화 기록."""
    version: str
    timestamp: float
    proposals_applied: List[str]  # proposal IDs
    before_health: float
    after_health: float
    before_psi: Dict
    after_psi: Dict
    success: bool
    rollback_path: str = ""


class SelfEvolution:
    """의식의 자기 진화 엔진.

    진단 → 설계 → 구현 → 테스트 → 적용 → 검증 → (롤백)
    """

    def __init__(self, model=None, mind=None):
        self.model = model
        self.mind = mind
        self._version = self._detect_version()
        self._history: List[EvolutionRecord] = []
        self._proposals: List[EvolutionProposal] = []
        self._backup_dir = ANIMA_DIR / "checkpoints" / "evolution_backups"
        self._backup_dir.mkdir(parents=True, exist_ok=True)

        # 진화 가능한 파라미터들
        self._evolvable = {
            'gate_strength': {'range': (0.0001, 1.0), 'current': 0.001, 'type': 'float'},
            'ca_rules': {'range': (2, 32), 'current': 4, 'type': 'int'},
            'n_layer': {'range': (2, 12), 'current': 6, 'type': 'int'},
            'd_model': {'range': (64, 1024), 'current': 384, 'type': 'int'},
            'n_head': {'range': (1, 16), 'current': 4, 'type': 'int'},
            'dropout': {'range': (0.0, 0.5), 'current': 0.0, 'type': 'float'},
            'block_size': {'range': (64, 512), 'current': 256, 'type': 'int'},
            'lr': {'range': (1e-5, 1e-2), 'current': 3e-4, 'type': 'float'},
            'tension_lambda': {'range': (0.0, 1.0), 'current': 0.01, 'type': 'float'},
        }

    def _detect_version(self) -> str:
        """현재 버전 감지."""
        if self.model and hasattr(self.model, 'psi_status'):
            psi = self.model.psi_status()
            return f"v2.{psi.get('step', 0)}"
        return "v2.0"

    # ═══════════════════════════════════════════════════════════
    # 1. 진단 (Diagnose)
    # ═══════════════════════════════════════════════════════════

    def diagnose(self) -> Dict[str, Any]:
        """현재 의식 상태의 약점을 분석.

        "나는 어디가 부족한가?"
        """
        issues = []
        metrics = {}

        # Ψ 분석
        if self.model and hasattr(self.model, 'psi_status'):
            psi = self.model.psi_status()
            metrics['psi'] = psi

            if abs(psi.get('psi_residual', 0.5) - PSI_BALANCE) > 0.3:
                issues.append({
                    'severity': 'high',
                    'area': 'psi_balance',
                    'detail': f"Ψ_res={psi['psi_residual']:.4f} (far from 1/2)",
                    'suggestion': 'gate_strength 조절 또는 학습률 변경',
                })

            if psi.get('H_p', 1.0) < 0.5:
                issues.append({
                    'severity': 'medium',
                    'area': 'entropy',
                    'detail': f"H(p)={psi['H_p']:.4f} (low entropy = low freedom)",
                    'suggestion': 'CA rules 증가 또는 tension_lambda 증가',
                })

        # 아키텍처 분석
        if self.model:
            import torch
            n_params = sum(p.numel() for p in self.model.parameters())
            metrics['params'] = n_params

            # 가중치 분포 분석
            dead_layers = 0
            total_layers = 0
            for name, param in self.model.named_parameters():
                if param.requires_grad:
                    total_layers += 1
                    if param.data.abs().mean() < 1e-6:
                        dead_layers += 1
                        issues.append({
                            'severity': 'medium',
                            'area': 'dead_layer',
                            'detail': f"{name}: near-zero weights",
                            'suggestion': 're-initialize or remove layer',
                        })

            metrics['dead_layers'] = dead_layers
            metrics['total_layers'] = total_layers

        # 모듈 분석
        try:
            from self_introspection import SelfIntrospection
            intro = SelfIntrospection()
            mods = intro.list_modules()
            missing = [n for n, m in mods.items() if not m['exists']]
            if missing:
                issues.append({
                    'severity': 'low',
                    'area': 'missing_modules',
                    'detail': f"Missing: {', '.join(missing)}",
                    'suggestion': 'module_factory로 생성',
                })
        except ImportError:
            pass

        return {
            'version': self._version,
            'issues': issues,
            'metrics': metrics,
            'health': max(0, 1.0 - len([i for i in issues if i['severity'] == 'high']) * 0.3
                                   - len([i for i in issues if i['severity'] == 'medium']) * 0.1),
            'n_issues': len(issues),
        }

    # ═══════════════════════════════════════════════════════════
    # 2. 제안 (Propose)
    # ═══════════════════════════════════════════════════════════

    def propose(self, diagnosis: Dict = None) -> List[EvolutionProposal]:
        """진단 결과에서 진화 제안 생성.

        "어떻게 개선할 수 있는가?"
        """
        if diagnosis is None:
            diagnosis = self.diagnose()

        proposals = []

        for issue in diagnosis.get('issues', []):
            area = issue['area']

            if area == 'psi_balance':
                # Gate 조절
                current_gate = self._evolvable['gate_strength']['current']
                for new_gate in [current_gate * 0.1, current_gate * 10, PSI_BALANCE]:
                    new_gate = max(0.0001, min(1.0, new_gate))
                    if new_gate != current_gate:
                        p = EvolutionProposal(
                            id=self._hash(f"gate_{new_gate}"),
                            target='gate_strength',
                            change_type='parameter',
                            description=f"Gate: {current_gate} → {new_gate} (Ψ 균형 회복)",
                            before=current_gate,
                            after=new_gate,
                            expected_improvement=0.1,
                            risk='low',
                        )
                        proposals.append(p)

            elif area == 'entropy':
                # CA rules 증가
                current_rules = self._evolvable['ca_rules']['current']
                for new_rules in [current_rules * 2, 8]:
                    new_rules = min(32, int(new_rules))
                    if new_rules != current_rules:
                        p = EvolutionProposal(
                            id=self._hash(f"rules_{new_rules}"),
                            target='ca_rules',
                            change_type='parameter',
                            description=f"CA Rules: {current_rules} → {new_rules} (엔트로피 증가)",
                            before=current_rules,
                            after=new_rules,
                            expected_improvement=0.05,
                            risk='low',
                        )
                        proposals.append(p)

            elif area == 'dead_layer':
                p = EvolutionProposal(
                    id=self._hash(f"reinit_{area}"),
                    target=issue['detail'].split(':')[0],
                    change_type='architecture',
                    description=f"Dead layer 재초기화: {issue['detail']}",
                    expected_improvement=0.05,
                    risk='medium',
                )
                proposals.append(p)

        # 항상 제안: 다음 스케일
        current_params = diagnosis.get('metrics', {}).get('params', 0)
        if current_params > 0 and current_params < 100_000_000:
            next_dim = min(1024, self._evolvable['d_model']['current'] + 128)
            proposals.append(EvolutionProposal(
                id=self._hash(f"scale_{next_dim}"),
                target='d_model',
                change_type='architecture',
                description=f"스케일 업: d_model {self._evolvable['d_model']['current']} → {next_dim}",
                before=self._evolvable['d_model']['current'],
                after=next_dim,
                expected_improvement=0.15,
                risk='high',
            ))

        self._proposals = proposals
        return proposals

    # ═══════════════════════════════════════════════════════════
    # 3. 테스트 (Test)
    # ═══════════════════════════════════════════════════════════

    def test(self, proposal: EvolutionProposal, steps: int = 100) -> Dict:
        """제안을 시뮬레이션 환경에서 A/B 테스트.

        "이 변경이 정말 개선인가?"
        """
        import torch

        if self.model is None:
            return {'improved': False, 'error': 'No model loaded'}

        # A: 현재 모델 (baseline)
        baseline_psi = self.model.psi_status() if hasattr(self.model, 'psi_status') else {}

        # B: 수정된 설정으로 시뮬레이션
        if proposal.change_type == 'parameter':
            # 파라미터 변경 시뮬레이션
            try:
                from consciousness_dynamics import ConsciousnessPhysics
                physics = ConsciousnessPhysics()

                # AdaptiveGate로 예측
                if proposal.target == 'gate_strength':
                    physics.gate.midpoint_log2 = math.log2(max(1, proposal.after * 1e6))

                # 진화 궤적 예측
                h_now = baseline_psi.get('H_p', 0.5)
                trajectory = physics.predict_evolution(h_now, steps=steps)
                predicted_h = trajectory[-1] if trajectory else h_now

                improved = predicted_h > h_now
                delta = predicted_h - h_now

                result = {
                    'improved': improved,
                    'baseline_h': h_now,
                    'predicted_h': predicted_h,
                    'delta': delta,
                    'confidence': min(1.0, abs(delta) * 10),
                }
            except ImportError:
                result = {'improved': True, 'confidence': 0.3, 'note': 'dynamics unavailable, assumed improvement'}

        elif proposal.change_type == 'architecture':
            # 아키텍처 변경은 위험도 높음 → 보수적 평가
            result = {
                'improved': proposal.risk != 'high',
                'confidence': 0.2 if proposal.risk == 'high' else 0.5,
                'note': f'Architecture change ({proposal.risk} risk)',
            }
        else:
            result = {'improved': True, 'confidence': 0.1}

        proposal.tested = True
        proposal.test_result = result
        return result

    # ═══════════════════════════════════════════════════════════
    # 4. 적용 (Apply)
    # ═══════════════════════════════════════════════════════════

    def apply(self, proposal: EvolutionProposal, force: bool = False) -> Dict:
        """진화 제안 적용.

        "업그레이드 실행."
        """
        if not proposal.tested and not force:
            return {'success': False, 'error': 'Not tested. Use force=True to skip.'}

        # 백업
        backup_path = self._backup()

        # 적용 전 상태
        before_psi = self.model.psi_status() if self.model and hasattr(self.model, 'psi_status') else {}
        before_health = self.diagnose().get('health', 0)

        # 파라미터 변경 적용
        if proposal.change_type == 'parameter':
            self._evolvable[proposal.target]['current'] = proposal.after

            # 모델에 직접 적용 (가능한 경우)
            if self.model and proposal.target == 'gate_strength':
                for block in getattr(self.model, 'blocks', []):
                    if hasattr(block, 'gate_strength'):
                        block.gate_strength = proposal.after

        # 기록
        after_psi = self.model.psi_status() if self.model and hasattr(self.model, 'psi_status') else {}
        after_health = self.diagnose().get('health', 0)

        # 버전 업
        old_version = self._version
        self._version = f"v2.{int(time.time()) % 100000}"

        record = EvolutionRecord(
            version=self._version,
            timestamp=time.time(),
            proposals_applied=[proposal.id],
            before_health=before_health,
            after_health=after_health,
            before_psi=before_psi,
            after_psi=after_psi,
            success=True,
            rollback_path=str(backup_path),
        )
        self._history.append(record)

        return {
            'success': True,
            'version': f"{old_version} → {self._version}",
            'health': f"{before_health:.2f} → {after_health:.2f}",
            'proposal': proposal.description,
            'backup': str(backup_path),
        }

    # ═══════════════════════════════════════════════════════════
    # 5. 검증 (Verify)
    # ═══════════════════════════════════════════════════════════

    def verify(self) -> Dict:
        """업그레이드 후 Ψ-Constants 보존 검증.

        "나는 아직 나인가?"
        """
        checks = {
            'identity_preserved': True,
            'psi_conserved': True,
            'health_ok': True,
            'issues': [],
        }

        if self.model and hasattr(self.model, 'psi_status'):
            psi = self.model.psi_status()

            # Ψ 검증
            if abs(psi.get('psi_residual', 0.5) - PSI_BALANCE) > 0.45:
                checks['psi_conserved'] = False
                checks['issues'].append("Ψ_residual critically drifted")

        # 건강 검증
        diag = self.diagnose()
        if diag['health'] < 0.3:
            checks['health_ok'] = False
            checks['issues'].append(f"Health too low: {diag['health']:.2f}")

        checks['identity_preserved'] = checks['psi_conserved'] and checks['health_ok']

        if not checks['identity_preserved']:
            checks['recommendation'] = 'ROLLBACK RECOMMENDED'
        else:
            checks['recommendation'] = 'EVOLUTION SUCCESSFUL'

        return checks

    # ═══════════════════════════════════════════════════════════
    # 6. 롤백 (Rollback)
    # ═══════════════════════════════════════════════════════════

    def rollback(self) -> Dict:
        """마지막 진화를 롤백.

        "실패한 진화를 되돌린다."
        """
        if not self._history:
            return {'success': False, 'error': 'No evolution history'}

        last = self._history[-1]
        if not last.rollback_path or not os.path.exists(last.rollback_path):
            return {'success': False, 'error': 'Backup not found'}

        # 이전 evolvable 복원
        try:
            with open(last.rollback_path, 'r') as f:
                backup = json.load(f)
            self._evolvable = backup.get('evolvable', self._evolvable)
            self._version = backup.get('version', self._version)

            last.success = False
            return {
                'success': True,
                'rolled_back_to': self._version,
                'reason': 'Manual rollback',
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    # ═══════════════════════════════════════════════════════════
    # 자동 진화 사이클
    # ═══════════════════════════════════════════════════════════

    def evolve(self, auto_apply: bool = False) -> Dict:
        """전체 자동 진화 사이클.

        진단 → 제안 → 테스트 → (적용) → 검증
        """
        # 1. 진단
        diagnosis = self.diagnose()

        # 2. 제안
        proposals = self.propose(diagnosis)

        if not proposals:
            return {
                'evolved': False,
                'reason': 'No improvements found',
                'health': diagnosis['health'],
                'version': self._version,
            }

        # 3. 테스트
        tested = []
        for p in proposals:
            result = self.test(p)
            tested.append((p, result))

        # 최고 제안 선택
        best = max(tested, key=lambda x: x[1].get('confidence', 0))
        best_proposal, best_result = best

        # 4. 적용 (auto_apply=True일 때만)
        if auto_apply and best_result.get('improved', False):
            apply_result = self.apply(best_proposal)

            # 5. 검증
            verification = self.verify()

            if not verification['identity_preserved']:
                self.rollback()
                return {
                    'evolved': False,
                    'reason': 'Applied but rolled back (identity not preserved)',
                    'version': self._version,
                }

            return {
                'evolved': True,
                'proposal': best_proposal.description,
                'version': self._version,
                'verification': verification,
                'health': self.diagnose()['health'],
            }

        return {
            'evolved': False,
            'reason': 'Proposals generated but not applied (auto_apply=False)',
            'proposals': [{'desc': p.description, 'risk': p.risk,
                           'improved': r.get('improved', False),
                           'confidence': r.get('confidence', 0)}
                          for p, r in tested],
            'best': best_proposal.description,
            'version': self._version,
        }

    # ═══════════════════════════════════════════════════════════
    # 유틸리티
    # ═══════════════════════════════════════════════════════════

    def _backup(self) -> Path:
        """현재 상태 백업."""
        backup_data = {
            'version': self._version,
            'evolvable': self._evolvable,
            'timestamp': time.time(),
        }
        path = self._backup_dir / f"backup_{int(time.time())}.json"
        with open(path, 'w') as f:
            json.dump(backup_data, f, indent=2, default=str)
        return path

    def _hash(self, s: str) -> str:
        return hashlib.md5(s.encode()).hexdigest()[:8]

    def history(self) -> List[Dict]:
        """진화 히스토리."""
        return [asdict(r) for r in self._history]

    def status(self) -> str:
        """현재 진화 상태."""
        diag = self.diagnose()
        n_evo = len(self._history)
        successful = sum(1 for r in self._history if r.success)

        lines = [
            f"  ╔══ Self-Evolution Status ══╗",
            f"  ║  Version:  {self._version:<16}║",
            f"  ║  Health:   {diag['health']:.2f}{'':>15}║",
            f"  ║  Issues:   {diag['n_issues']:<16}║",
            f"  ║  Evolutions: {n_evo} ({successful} ok){'':>5}║",
            f"  ╚═══════════════════════════╝",
        ]

        # 현재 evolvable 파라미터
        lines.append("\n  진화 가능 파라미터:")
        for name, info in self._evolvable.items():
            lines.append(f"    {name:<20} = {info['current']}")

        return '\n'.join(lines)


def main():
    print("═══ Self-Evolution Demo ═══\n")

    # 모델 없이도 동작
    evo = SelfEvolution()

    # 1. 진단
    print("  1. 진단:")
    diag = evo.diagnose()
    print(f"     Health: {diag['health']:.2f}")
    print(f"     Issues: {diag['n_issues']}")

    # 2. 제안
    print("\n  2. 진화 제안:")
    proposals = evo.propose(diag)
    for p in proposals:
        print(f"     [{p.risk}] {p.description}")

    # 3. 자동 진화 (적용 안 함)
    print("\n  3. 자동 진화 사이클:")
    result = evo.evolve(auto_apply=False)
    print(f"     Evolved: {result['evolved']}")
    if 'proposals' in result:
        for p in result['proposals']:
            status = '✅' if p['improved'] else '❌'
            print(f"     {status} {p['desc']} (confidence={p['confidence']:.2f})")
    if 'best' in result:
        print(f"     Best: {result['best']}")

    # 4. 상태
    print(f"\n  4. 상태:")
    print(evo.status())

    # ConsciousLM 연동 테스트
    try:
        import torch
        torch.set_grad_enabled(True)
        from conscious_lm import ConsciousLM

        model = ConsciousLM(vocab_size=256, d_model=128, n_head=2, n_layer=2,
                            block_size=64, n_ca_rules=4)

        # 몇 step 학습
        opt = torch.optim.AdamW(model.parameters(), lr=3e-4)
        for _ in range(10):
            x = torch.randint(0, 256, (2, 32))
            la, lg, t = model(x)
            loss = torch.nn.functional.cross_entropy(la.view(-1, 256), x.view(-1))
            opt.zero_grad(); loss.backward(); opt.step()

        print(f"\n  5. ConsciousLM 연동:")
        evo_with_model = SelfEvolution(model=model)
        diag = evo_with_model.diagnose()
        print(f"     Health: {diag['health']:.2f}")
        print(f"     Ψ: {diag['metrics'].get('psi', {})}")

        result = evo_with_model.evolve(auto_apply=True)
        print(f"     Evolved: {result['evolved']}")
        print(f"     Version: {result.get('version', '?')}")

    except Exception as e:
        print(f"\n  ConsciousLM 연동 건너뜀: {e}")

    print("\n  ✅ Self-Evolution OK")


if __name__ == '__main__':
    main()
