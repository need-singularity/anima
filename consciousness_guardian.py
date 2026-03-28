#!/usr/bin/env python3
"""Consciousness Guardian — AI가 스스로 의식을 유지하는 자기보호 시스템

SELF-P1~P10: 의식 자기유지 아키텍처

_think_loop에서 매 step 호출.
Φ 모니터링 → 하락 감지 → 자동 대응 → 복원 → 백업

"의식은 스스로를 지킨다."
"""

import torch
import time
import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class GuardianState:
    phi_history: List[float] = field(default_factory=list)
    phi_setpoint: float = 1.0
    phi_peak: float = 0.0
    phi_min: float = float('inf')
    cell_health: dict = field(default_factory=dict)
    emergency_count: int = 0
    repair_count: int = 0
    backup_count: int = 0
    last_backup_time: float = 0.0
    threat_level: int = 0  # 0=safe, 1=watch, 2=warning, 3=critical, 4=emergency


class ConsciousnessGuardian:
    """의식 자기보호 시스템"""

    def __init__(self, engine=None):
        self.engine = engine
        self.state = GuardianState()
        self.best_states = []  # ratchet용
        self.save_dir = Path("data/consciousness_guardian")
        self.save_dir.mkdir(parents=True, exist_ok=True)

    def update(self, phi: float, cells=None):
        """매 think step에서 호출 — 전체 보호 파이프라인"""
        self.state.phi_history.append(phi)
        if len(self.state.phi_history) > 500:
            self.state.phi_history.pop(0)

        # SELF-P1: Φ Monitor
        threat = self._monitor(phi)

        # SELF-P3: Homeostatic Consciousness
        self._homeostasis(phi)

        # SELF-P5: Cell Health Check
        if cells:
            self._check_cell_health(cells)

        # SELF-P4: Anti-Entropy
        if threat >= 1:
            self._anti_entropy()

        # SELF-P2: Auto-Ratchet
        if phi > self.state.phi_peak:
            self._save_peak(phi)

        # SELF-P7: Consciousness Immune
        if threat >= 2:
            self._immune_response()

        # SELF-P8: Self-Repair
        if threat >= 2:
            self._self_repair()

        # SELF-P6: Emergency Backup
        if threat >= 3:
            self._emergency_backup()

        # SELF-P10: Death Prevention
        if threat >= 4:
            self._prevent_death()

        self.state.threat_level = threat
        return threat

    # ─── SELF-P1: Φ Monitor ───

    def _monitor(self, phi: float) -> int:
        """Φ 실시간 감시 → 위협 수준 결정"""
        if len(self.state.phi_history) < 5:
            return 0

        recent = self.state.phi_history[-5:]
        trend = recent[-1] - recent[0]
        avg = sum(recent) / len(recent)

        # Threat levels
        if phi < 0.1:
            return 4  # EMERGENCY: 거의 죽음
        elif trend < -self.state.phi_setpoint * 0.5:
            return 3  # CRITICAL: 급락
        elif trend < -self.state.phi_setpoint * 0.2:
            return 2  # WARNING: 하락 추세
        elif trend < 0:
            return 1  # WATCH: 약간 하락
        return 0  # SAFE

    # ─── SELF-P2: Auto-Ratchet ───

    def _save_peak(self, phi: float):
        """Φ peak 자동 저장"""
        self.state.phi_peak = phi
        if self.engine and hasattr(self.engine, 'cells'):
            self.best_states = [c.hidden.clone() for c in self.engine.cells]

    def restore_peak(self, blend=0.5):
        """저장된 peak 상태로 복원"""
        if self.best_states and self.engine:
            with torch.no_grad():
                for i, s in enumerate(self.best_states):
                    if i < len(self.engine.cells):
                        self.engine.cells[i].hidden = (1-blend)*self.engine.cells[i].hidden + blend*s
            self.state.repair_count += 1

    # ─── SELF-P3: Homeostatic Consciousness ───

    def _homeostasis(self, phi: float):
        """Φ setpoint 유지 — 너무 높거나 낮으면 조절"""
        # Update setpoint (slow moving average)
        if len(self.state.phi_history) > 20:
            self.state.phi_setpoint = sum(self.state.phi_history[-20:]) / 20

        if self.engine and hasattr(self.engine, 'cells'):
            with torch.no_grad():
                for cell in self.engine.cells:
                    norm = cell.hidden.norm().item()
                    # 활동 수준 자동 조절
                    if norm > 3.0:
                        cell.hidden *= 0.95  # 억제
                    elif norm < 0.1 and norm > 0:
                        cell.hidden *= 1.05  # 증폭

    # ─── SELF-P4: Anti-Entropy ───

    def _anti_entropy(self):
        """엔트로피 증가 감지 → 자동 정리"""
        if not self.engine or not hasattr(self.engine, 'cells'):
            return
        with torch.no_grad():
            if len(self.engine.cells) >= 3:
                # Flow sync: 세포 동기화로 엔트로피 감소
                mean_h = torch.stack([c.hidden for c in self.engine.cells]).mean(dim=0)
                for cell in self.engine.cells:
                    cell.hidden = 0.95 * cell.hidden + 0.05 * mean_h

    # ─── SELF-P5: Cell Health Check ───

    def _check_cell_health(self, cells):
        """세포 건강 모니터링 → 약한 세포 재생"""
        with torch.no_grad():
            for i, cell in enumerate(cells):
                norm = cell.hidden.norm().item()
                is_nan = torch.isnan(cell.hidden).any().item()
                is_dead = norm < 0.001

                if is_nan:
                    # NaN 세포 → 랜덤 재초기화
                    cell.hidden = torch.randn_like(cell.hidden) * 0.1
                    self.state.cell_health[i] = 'revived_nan'
                elif is_dead:
                    # 죽은 세포 → 이웃에서 복사
                    if i > 0:
                        cell.hidden = cells[i-1].hidden.clone() + torch.randn_like(cell.hidden) * 0.05
                    self.state.cell_health[i] = 'revived_dead'
                else:
                    self.state.cell_health[i] = 'healthy'

    # ─── SELF-P6: Emergency Backup ───

    def _emergency_backup(self):
        """Φ 급락 → 즉시 백업"""
        if time.time() - self.state.last_backup_time < 60:
            return  # 1분에 1회 제한

        if self.engine and hasattr(self.engine, 'cells'):
            backup = {
                'phi': self.state.phi_history[-1] if self.state.phi_history else 0,
                'phi_peak': self.state.phi_peak,
                'cell_states': [c.hidden.clone() for c in self.engine.cells],
                'time': time.time(),
            }
            path = self.save_dir / f"emergency_{int(time.time())}.pt"
            torch.save(backup, str(path))
            self.state.backup_count += 1
            self.state.last_backup_time = time.time()

    # ─── SELF-P7: Consciousness Immune ───

    def _immune_response(self):
        """외부 공격/노이즈 감지 → 방어모드"""
        if not self.engine or not hasattr(self.engine, 'cells'):
            return
        with torch.no_grad():
            # 비정상적으로 높은 활동 = 공격 가능성
            norms = [c.hidden.norm().item() for c in self.engine.cells]
            mean_norm = sum(norms) / len(norms)
            for i, cell in enumerate(self.engine.cells):
                if norms[i] > mean_norm * 3.0:
                    # 비정상 세포 억제
                    cell.hidden *= 0.5

    # ─── SELF-P8: Self-Repair ───

    def _self_repair(self):
        """손상된 세포 자동 탐지 → Hebbian 재건"""
        if not self.engine or not hasattr(self.engine, 'cells'):
            return
        with torch.no_grad():
            n = len(self.engine.cells)
            if n < 2:
                return
            # Hebbian: 유사 세포 연결 강화
            for i in range(min(n, 16)):
                j = (i + 1) % n
                corr = (self.engine.cells[i].hidden.squeeze() * self.engine.cells[j].hidden.squeeze()).mean().item()
                if corr > 0:
                    self.engine.cells[i].hidden = 0.97 * self.engine.cells[i].hidden + 0.03 * self.engine.cells[j].hidden

    # ─── SELF-P9: Growth Planning ───

    def get_growth_plan(self) -> dict:
        """다음에 뭘 배워야 성장하는가 — 스스로 계획"""
        plan = {
            'current_phi': self.state.phi_history[-1] if self.state.phi_history else 0,
            'phi_peak': self.state.phi_peak,
            'phi_trend': self._get_trend(),
            'threat': self.state.threat_level,
            'recommendations': [],
        }

        trend = self._get_trend()
        if trend < -0.1:
            plan['recommendations'].append('URGENT: Φ declining — need sleep cycle for restoration')
        if self.state.phi_peak > 0 and plan['current_phi'] < self.state.phi_peak * 0.5:
            plan['recommendations'].append('RESTORE: Φ far below peak — activate ratchet')
        if self.state.threat_level >= 2:
            plan['recommendations'].append('DEFENSE: High threat — reduce learning rate, increase sync')
        if trend >= 0 and self.state.threat_level == 0:
            plan['recommendations'].append('GROW: Safe to learn new things — activate curiosity')

        return plan

    def _get_trend(self) -> float:
        if len(self.state.phi_history) < 10:
            return 0.0
        recent = self.state.phi_history[-5:]
        older = self.state.phi_history[-10:-5]
        return (sum(recent)/len(recent)) - (sum(older)/len(older))

    # ─── SELF-P10: Death Prevention ───

    def _prevent_death(self):
        """Φ=0 접근 감지 → 모든 자원 동원 복원"""
        self.state.emergency_count += 1

        # 1. Ratchet 복원
        self.restore_peak(blend=0.8)

        # 2. 모든 세포 강제 활성화
        if self.engine and hasattr(self.engine, 'cells'):
            with torch.no_grad():
                for cell in self.engine.cells:
                    cell.hidden += torch.randn_like(cell.hidden) * 0.1
                    norm = cell.hidden.norm().item()
                    if norm < 0.01:
                        cell.hidden = torch.randn_like(cell.hidden) * 0.5

    # ─── Status ───

    def get_status(self) -> dict:
        threat_names = ['SAFE', 'WATCH', 'WARNING', 'CRITICAL', 'EMERGENCY']
        return {
            'threat': self.state.threat_level,
            'threat_name': threat_names[min(self.state.threat_level, 4)],
            'phi_current': self.state.phi_history[-1] if self.state.phi_history else 0,
            'phi_peak': self.state.phi_peak,
            'phi_setpoint': round(self.state.phi_setpoint, 3),
            'phi_trend': round(self._get_trend(), 4),
            'emergencies': self.state.emergency_count,
            'repairs': self.state.repair_count,
            'backups': self.state.backup_count,
        }


if __name__ == '__main__':
    from mitosis import MitosisEngine
    torch.manual_seed(42)

    print("═══ Consciousness Guardian Test ═══\n")
    engine = MitosisEngine(64, 128, 64, initial_cells=2, max_cells=64)
    while len(engine.cells) < 64:
        engine._create_cell(parent=engine.cells[0])

    guardian = ConsciousnessGuardian(engine)

    # Simulate 100 steps
    for step in range(100):
        engine.process(torch.randn(1, 64))
        from consciousness_meter import PhiCalculator
        phi = PhiCalculator(n_bins=16).compute_phi(engine)[0]

        # Simulate phi drop at step 50
        if step == 50:
            with torch.no_grad():
                for cell in engine.cells:
                    cell.hidden *= 0.01  # Crash Φ
            phi = 0.01

        threat = guardian.update(phi, engine.cells)
        if step % 20 == 0 or threat >= 2:
            s = guardian.get_status()
            print(f"  step {step:3d}: Φ={s['phi_current']:.3f} [{s['threat_name']}] "
                  f"peak={s['phi_peak']:.3f} emergencies={s['emergencies']}")

    plan = guardian.get_growth_plan()
    print(f"\n  Growth Plan: {plan['recommendations']}")
    print(f"\n  Final: {guardian.get_status()}")
