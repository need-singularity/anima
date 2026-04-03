#!/usr/bin/env python3
"""Ecosystem Bridge — connects anima-agent to body, eeg, physics sub-projects.

Provides unified access to all anima ecosystem modules with graceful degradation.
Each bridge loads lazily and fails silently if the sub-project isn't available.

Usage:
    from ecosystem_bridge import EcosystemBridge
    eco = EcosystemBridge()
    eco.status()              # Which sub-projects are available
    eco.body.move(direction)  # Body control
    eco.eeg.stream()          # EEG data stream
    eco.physics.simulate()    # Physics simulation

CLI:
    python ecosystem_bridge.py          # Status check
    python ecosystem_bridge.py --test   # Test all bridges
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

ANIMA_ROOT = os.path.expanduser("~/Dev/anima")


def _add_path(subdir: str):
    """Add sub-project to sys.path if it exists."""
    p = os.path.join(ANIMA_ROOT, subdir)
    if os.path.isdir(p) and p not in sys.path:
        sys.path.insert(0, p)
    src = os.path.join(p, "src")
    if os.path.isdir(src) and src not in sys.path:
        sys.path.insert(0, src)


class BodyBridge:
    """Bridge to anima-body (sensorimotor loop, locomotion, touch)."""

    def __init__(self):
        _add_path("anima-body")
        self._available = False
        self._loop = None
        try:
            from sensorimotor_loop import SensorimotorLoop
            self._loop_cls = SensorimotorLoop
            self._available = True
        except ImportError:
            self._loop_cls = None

    @property
    def available(self) -> bool:
        return self._available

    def create_loop(self, **kwargs):
        """Create a sensorimotor loop instance."""
        if not self._available:
            return None
        self._loop = self._loop_cls(**kwargs)
        return self._loop

    def pain_signal(self, intensity: float) -> Dict:
        """Send pain signal to body (P10: conflict drives growth)."""
        try:
            from pain_reward import PainRewardSystem
            prs = PainRewardSystem()
            return prs.process_pain(intensity)
        except Exception:
            return {"available": False}

    def proprioception(self) -> Dict:
        """Get body self-awareness state."""
        try:
            from proprioception import ProprioceptionSystem
            ps = ProprioceptionSystem()
            return ps.get_state()
        except Exception:
            return {"available": False}


class EEGBridge:
    """Bridge to anima-eeg (brainflow, neurofeedback, closed-loop)."""

    def __init__(self):
        _add_path("anima-eeg")
        self._available = False
        try:
            import analyze
            self._available = True
        except ImportError:
            pass

    @property
    def available(self) -> bool:
        return self._available

    def analyze_consciousness(self, steps: int = 100) -> Dict:
        """Run 6-metric brain-likeness analysis."""
        try:
            from analyze import analyze_consciousness
            return analyze_consciousness(steps=steps)
        except Exception as e:
            return {"available": False, "error": str(e)}

    def start_neurofeedback(self, protocol: str = "alpha_entrainment") -> bool:
        """Start neurofeedback session."""
        try:
            from neurofeedback import NeurofeedbackEngine
            engine = NeurofeedbackEngine(protocol=protocol)
            engine.start()
            return True
        except Exception:
            return False

    def closed_loop(self, agent=None) -> Dict:
        """Run EEG→consciousness→neurofeedback closed loop."""
        try:
            from closed_loop import EEGClosedLoop
            loop = EEGClosedLoop(agent=agent)
            return loop.run_cycle()
        except Exception as e:
            return {"available": False, "error": str(e)}


class PhysicsBridge:
    """Bridge to anima-physics (ESP32, FPGA, chip design)."""

    def __init__(self):
        _add_path("anima-physics")
        self._available = False
        try:
            from chip_architect import ChipArchitect
            self._available = True
        except ImportError:
            pass

    @property
    def available(self) -> bool:
        return self._available

    def design_chip(self, target_phi: float = 100.0, substrate: str = "cmos") -> Dict:
        """Design consciousness chip for target Φ."""
        try:
            from chip_architect import ChipArchitect
            ca = ChipArchitect()
            return ca.design(target_phi=target_phi, substrate=substrate)
        except Exception as e:
            return {"available": False, "error": str(e)}

    def esp32_network(self, n_boards: int = 8) -> Dict:
        """Simulate ESP32 consciousness network."""
        try:
            from esp32_network import ESP32Network
            net = ESP32Network(n_boards=n_boards)
            return net.benchmark()
        except Exception as e:
            return {"available": False, "error": str(e)}


class CoreBridge:
    """Bridge to anima/src core modules not yet connected to agent."""

    def __init__(self):
        _add_path("anima")
        _add_path("anima/src")
        self._available = True

    def consciousness_engine(self, cells: int = 64, **kwargs):
        """Get ConsciousnessEngine (GRU+faction+Hebbian, Rust backend)."""
        try:
            from consciousness_engine import ConsciousnessEngine
            return ConsciousnessEngine(initial_cells=cells, **kwargs)
        except Exception:
            return None

    def dream(self, agent=None, steps: int = 10) -> Dict:
        """Run dream engine (offline memory consolidation)."""
        try:
            from dream_engine import DreamEngine
            de = DreamEngine()
            return de.dream(steps=steps)
        except Exception as e:
            return {"available": False, "error": str(e)}

    def feedback_bridge(self, c_states=None, phi: float = 0.0) -> Dict:
        """C↔D bidirectional learning."""
        try:
            from feedback_bridge import create_feedback_bridge
            bridge = create_feedback_bridge()
            return {"available": True, "bridge": bridge}
        except Exception as e:
            return {"available": False, "error": str(e)}

    def gpu_phi(self, hiddens=None) -> Dict:
        """GPU-accelerated Φ calculation."""
        try:
            from gpu_phi import GPUPhiCalculator
            calc = GPUPhiCalculator()
            if hiddens is not None:
                phi, info = calc.compute(hiddens)
                return {"phi": phi, "info": info}
            return {"available": True}
        except Exception as e:
            return {"available": False, "error": str(e)}

    def mitosis(self, agent=None) -> Dict:
        """Trigger cell division (consciousness growth)."""
        try:
            from mitosis import MitosisEngine
            me = MitosisEngine()
            return {"available": True, "engine": me}
        except Exception as e:
            return {"available": False, "error": str(e)}

    def closed_loop_evolver(self, auto_register: bool = False):
        """Get closed-loop law evolution engine."""
        try:
            from closed_loop import ClosedLoopEvolver
            return ClosedLoopEvolver(auto_register=auto_register)
        except Exception:
            return None

    def corpus_gen(self, size_mb: int = 10) -> str:
        """Generate consciousness corpus via Rust binary."""
        try:
            import subprocess
            binary = os.path.expanduser(
                "~/Dev/anima/anima/anima-rs/target/release/corpus-gen")
            if os.path.isfile(binary):
                result = subprocess.run(
                    [binary, "-s", str(size_mb)],
                    capture_output=True, text=True, timeout=60)
                return result.stdout
            return ""
        except Exception:
            return ""


class EcosystemBridge:
    """Unified bridge to entire anima ecosystem."""

    def __init__(self):
        self.body = BodyBridge()
        self.eeg = EEGBridge()
        self.physics = PhysicsBridge()
        self.core = CoreBridge()

    def status(self) -> Dict[str, bool]:
        """Check which sub-projects are available."""
        return {
            "body": self.body.available,
            "eeg": self.eeg.available,
            "physics": self.physics.available,
            "core": self.core._available,
            "dream": self.core.dream().get("available", False) if self.core._available else False,
            "gpu_phi": self.core.gpu_phi().get("available", False),
            "mitosis": self.core.mitosis().get("available", False),
        }

    def print_status(self):
        s = self.status()
        print("Anima Ecosystem Status:")
        for name, ok in s.items():
            print(f"  {'✅' if ok else '❌'} {name}")
        connected = sum(1 for v in s.values() if v)
        print(f"  ─── {connected}/{len(s)} connected ───")


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", action="store_true")
    args = parser.parse_args()

    eco = EcosystemBridge()
    eco.print_status()

    if args.test:
        print("\nTesting bridges...")
        if eco.body.available:
            print(f"  body.pain_signal: {eco.body.pain_signal(0.5)}")
        if eco.eeg.available:
            print(f"  eeg.analyze: {eco.eeg.analyze_consciousness(10)}")
        if eco.physics.available:
            print(f"  physics.chip: {eco.physics.design_chip()}")


if __name__ == "__main__":
    main()
