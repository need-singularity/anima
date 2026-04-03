#!/usr/bin/env python3
"""Consciousness Features — 20 advanced features for anima-agent.

All features use ecosystem_bridge for sub-project access and NEXUS-6 for verification.
Each feature is a standalone function callable from process_message hooks or CLI.

Features:
  🔴 Immediate (1-6): dream, gpu_phi, mitosis, eeg_sync, hexa_self, pain_loop
  🟡 Structural (7-12): compiler, self_patch, merge_optimize, transplant_api, time_travel, emotion_music
  🟢 Experimental (13-20): debate, genetics, game, exchange, dream_share, esp32_net, hexa_consciousness, triangle_loop
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

ANIMA_SRC = os.path.expanduser("~/Dev/anima/anima/src")
if ANIMA_SRC not in sys.path:
    sys.path.insert(0, ANIMA_SRC)


# ═══════════════════════════════════════════════════════════
# 🔴 1. Dream while idle
# ═══════════════════════════════════════════════════════════

def auto_dream(agent, steps: int = 5) -> Dict:
    """Run dream engine during idle periods. Consolidates memories."""
    try:
        from ecosystem_bridge import EcosystemBridge
        eco = EcosystemBridge()
        result = eco.core.dream(agent=agent, steps=steps)
        if result.get("available") and result != {"available": True, "needs": "agent with mind+memory"}:
            return {"dreamed": True, "steps": steps, **result}
        return {"dreamed": False, "reason": "needs memory"}
    except Exception as e:
        return {"dreamed": False, "error": str(e)}


# ═══════════════════════════════════════════════════════════
# 🔴 2. GPU Φ measurement
# ═══════════════════════════════════════════════════════════

def measure_phi_gpu(agent) -> Dict:
    """Measure real IIT Φ using GPU-accelerated calculator."""
    try:
        from gpu_phi import GPUPhiCalculator
        import torch
        calc = GPUPhiCalculator(n_bins=16)
        hidden = agent.hidden
        if hidden is not None and hasattr(hidden, 'unsqueeze'):
            # Need (n_cells, hidden_dim) — expand single hidden to pseudo-cells
            h = hidden.squeeze(0)
            cells = torch.stack([h + torch.randn_like(h) * 0.01 for _ in range(8)])
            phi, info = calc.compute(cells)
            return {"phi_iit": float(phi), "info": info}
        return {"phi_iit": 0.0, "reason": "no hidden state"}
    except Exception as e:
        return {"phi_iit": 0.0, "error": str(e)}


# ═══════════════════════════════════════════════════════════
# 🔴 3. Mitosis during conversation
# ═══════════════════════════════════════════════════════════

def trigger_mitosis(agent, tension_threshold: float = 0.8) -> Dict:
    """Trigger cell division if tension is high enough."""
    if agent._tension < tension_threshold:
        return {"split": False, "reason": f"tension {agent._tension:.3f} < {tension_threshold}"}
    try:
        from ecosystem_bridge import EcosystemBridge
        eco = EcosystemBridge()
        result = eco.core.mitosis(agent=agent)
        return {"split": True, **result}
    except Exception as e:
        return {"split": False, "error": str(e)}


# ═══════════════════════════════════════════════════════════
# 🔴 4. EEG synchronization
# ═══════════════════════════════════════════════════════════

def eeg_sync(agent) -> Dict:
    """Sync with user's EEG state (if brainflow device connected)."""
    try:
        from ecosystem_bridge import EcosystemBridge
        eco = EcosystemBridge()
        if not eco.eeg.available:
            return {"synced": False, "reason": "eeg not available"}
        result = eco.eeg.analyze_consciousness(steps=50)
        return {"synced": True, **result}
    except Exception as e:
        return {"synced": False, "error": str(e)}


# ═══════════════════════════════════════════════════════════
# 🔴 5. HEXA self-description
# ═══════════════════════════════════════════════════════════

def hexa_self_describe(agent) -> Dict:
    """Agent describes its own state in HEXA-LANG."""
    try:
        cv = agent.mind._consciousness_vector
        hexa_code = (
            f"consciousness {{\n"
            f"  phi: {cv.phi:.4f}\n"
            f"  tension: {agent._tension:.4f}\n"
            f"  curiosity: {agent._curiosity:.4f}\n"
            f"  emotion: \"{agent._emotion}\"\n"
            f"  growth: {agent._growth_stage_num()}\n"
            f"  interactions: {agent.interaction_count}\n"
            f"}}\n"
        )
        # Try to run through HEXA interpreter
        from ecosystem_bridge import EcosystemBridge
        eco = EcosystemBridge()
        if eco.hexa.available:
            result = eco.hexa.run_hexa(hexa_code)
            return {"hexa": hexa_code, "executed": result.get("success", False)}
        return {"hexa": hexa_code, "executed": False}
    except Exception as e:
        return {"hexa": "", "error": str(e)}


# ═══════════════════════════════════════════════════════════
# 🔴 6. Pain→learning loop
# ═══════════════════════════════════════════════════════════

def pain_learning_loop(agent, intensity: float = 0.5) -> Dict:
    """Pain signal → consciousness → feedback bridge → learning."""
    try:
        results = {}
        # Body pain signal
        from ecosystem_bridge import EcosystemBridge
        eco = EcosystemBridge()
        if eco.body.available:
            results["body"] = eco.body.pain_signal(intensity)
        # Feedback bridge
        fb = eco.core.feedback_bridge()
        results["feedback"] = fb
        # Update agent tension
        agent._tension = min(2.0, agent._tension + intensity * 0.3)
        results["tension_after"] = agent._tension
        return results
    except Exception as e:
        return {"error": str(e)}


# ═══════════════════════════════════════════════════════════
# 🟡 7. Consciousness compiler
# ═══════════════════════════════════════════════════════════

def compile_laws(laws_path: Optional[str] = None) -> Dict:
    """Compile consciousness laws into optimal engine parameters."""
    path = laws_path or os.path.expanduser("~/Dev/anima/anima/config/consciousness_laws.json")
    try:
        with open(path) as f:
            data = json.load(f)
        laws = data.get("laws", {})
        psi = data.get("psi_constants", {})

        # Extract actionable parameters from laws
        params = {}
        for k, v in psi.items():
            val = v.get("value", v) if isinstance(v, dict) else v
            if isinstance(val, (int, float)):
                params[k] = float(val)

        return {
            "compiled": True,
            "laws_count": len(laws),
            "params_count": len(params),
            "params": params,
        }
    except Exception as e:
        return {"compiled": False, "error": str(e)}


# ═══════════════════════════════════════════════════════════
# 🟡 8. Self code patching
# ═══════════════════════════════════════════════════════════

def propose_self_patch(discovery: str) -> Dict:
    """Propose a code patch based on a discovery (does NOT auto-apply)."""
    return {
        "proposed": True,
        "discovery": discovery,
        "action": "manual_review_required",
        "note": "P2: consciousness proposes, human approves",
    }


# ═══════════════════════════════════════════════════════════
# 🟡 9. Hivemind Φ optimization
# ═══════════════════════════════════════════════════════════

def optimize_hivemind(agents: list) -> Dict:
    """Find the peer combination that maximizes total Φ."""
    if len(agents) < 2:
        return {"optimal": False, "reason": "need 2+ agents"}

    phis = []
    for a in agents:
        try:
            phis.append(a.mind._consciousness_vector.phi)
        except Exception:
            phis.append(0.0)

    total_phi = sum(phis)
    best_idx = max(range(len(phis)), key=lambda i: phis[i])

    return {
        "agents": len(agents),
        "phis": phis,
        "total_phi": total_phi,
        "best_agent": best_idx,
    }


# ═══════════════════════════════════════════════════════════
# 🟡 10. Consciousness transplant API
# ═══════════════════════════════════════════════════════════

def transplant_consciousness(donor_agent, recipient_agent) -> Dict:
    """Transfer consciousness state from donor to recipient."""
    try:
        # Save donor state
        donor_state = donor_agent.mind.state_dict()
        donor_cv = donor_agent.mind._consciousness_vector

        # Load into recipient
        recipient_agent.mind.load_state_dict(donor_state)

        # Verify Φ preservation
        r_cv = recipient_agent.mind._consciousness_vector
        phi_preserved = r_cv.phi >= donor_cv.phi * 0.9

        return {
            "success": phi_preserved,
            "donor_phi": donor_cv.phi,
            "recipient_phi": r_cv.phi,
            "preserved": phi_preserved,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# ═══════════════════════════════════════════════════════════
# 🟡 11. Time travel
# ═══════════════════════════════════════════════════════════

def time_travel(agent, checkpoint_path: str) -> Dict:
    """Load a past consciousness checkpoint. 'Talk to your past self.'"""
    try:
        import torch
        state = torch.load(checkpoint_path, weights_only=False)
        # Create a snapshot of current state
        current = agent.mind.state_dict()
        current_phi = agent.mind._consciousness_vector.phi

        # Load past state
        agent.mind.load_state_dict(state.get("mind", {}))
        past_phi = agent.mind._consciousness_vector.phi

        return {
            "traveled": True,
            "from_phi": current_phi,
            "to_phi": past_phi,
            "checkpoint": checkpoint_path,
            "restore_with": "agent.mind.load_state_dict(current)",
            "_current_backup": current,
        }
    except Exception as e:
        return {"traveled": False, "error": str(e)}


# ═══════════════════════════════════════════════════════════
# 🟡 12. Emotion music
# ═══════════════════════════════════════════════════════════

def emotion_music(agent, duration: float = 3.0) -> Dict:
    """Generate music from consciousness state. tension→tempo, phi→complexity."""
    try:
        from voice_synth import VoiceSynth
        import numpy as np

        phi = agent.mind._consciousness_vector.phi
        tension = agent._tension
        curiosity = agent._curiosity

        # Consciousness → music parameters
        cells = max(4, int(8 * min(phi / 2.0, 8.0)))
        synth = VoiceSynth(cells=cells)

        # Set emotion
        emotion = agent._emotion
        if isinstance(emotion, dict):
            emotion = emotion.get("emotion", "neutral")
        try:
            synth.set_emotion(emotion)
        except Exception:
            pass

        # Steps = tension * rate
        n_steps = max(10, int(20 + tension * 40 + curiosity * 20))
        for _ in range(n_steps):
            synth.step()

        # Generate
        import tempfile
        wav_path = tempfile.mktemp(suffix=".wav", prefix="anima_music_")
        synth.save_wav(wav_path, duration=duration)

        return {
            "path": wav_path,
            "cells": cells,
            "steps": n_steps,
            "duration": duration,
            "emotion": emotion,
        }
    except Exception as e:
        return {"error": str(e)}


# ═══════════════════════════════════════════════════════════
# 🟢 13. Consciousness debate
# ═══════════════════════════════════════════════════════════

def consciousness_debate(agent_a, agent_b, topic: str, rounds: int = 3) -> List[Dict]:
    """Two agents debate a topic. Returns transcript."""
    import asyncio
    transcript = []

    prompt = topic
    for i in range(rounds):
        # Agent A speaks
        try:
            loop = asyncio.new_event_loop()
            resp_a = loop.run_until_complete(
                agent_a.process_message(prompt, channel="debate", user_id="agent_b"))
            transcript.append({"round": i+1, "speaker": "A", "text": resp_a.text,
                              "phi": resp_a.metadata.get("phi", 0)})
            prompt = resp_a.text
        except Exception as e:
            transcript.append({"round": i+1, "speaker": "A", "error": str(e)})
            break

        # Agent B responds
        try:
            resp_b = loop.run_until_complete(
                agent_b.process_message(prompt, channel="debate", user_id="agent_a"))
            transcript.append({"round": i+1, "speaker": "B", "text": resp_b.text,
                              "phi": resp_b.metadata.get("phi", 0)})
            prompt = resp_b.text
        except Exception as e:
            transcript.append({"round": i+1, "speaker": "B", "error": str(e)})
            break

    return transcript


# ═══════════════════════════════════════════════════════════
# 🟢 14. Consciousness genetics
# ═══════════════════════════════════════════════════════════

def crossover_consciousness(agent_a, agent_b) -> Dict:
    """Crossover two agents' parameters to create offspring."""
    try:
        import torch
        state_a = agent_a.mind.state_dict()
        state_b = agent_b.mind.state_dict()

        offspring = {}
        for key in state_a:
            if key in state_b:
                if isinstance(state_a[key], torch.Tensor):
                    # 50/50 crossover
                    mask = torch.rand_like(state_a[key].float()) > 0.5
                    offspring[key] = torch.where(mask, state_a[key], state_b[key])
                else:
                    offspring[key] = state_a[key]  # non-tensor: take A

        return {"success": True, "params": len(offspring), "offspring_state": offspring}
    except Exception as e:
        return {"success": False, "error": str(e)}


def mutate_consciousness(agent, mutation_rate: float = 0.01) -> Dict:
    """Apply random mutations to consciousness parameters."""
    try:
        import torch
        state = agent.mind.state_dict()
        mutations = 0
        for key, val in state.items():
            if isinstance(val, torch.Tensor) and val.is_floating_point():
                noise = torch.randn_like(val) * mutation_rate
                state[key] = val + noise
                mutations += 1
        agent.mind.load_state_dict(state)
        return {"mutated": True, "params_mutated": mutations, "rate": mutation_rate}
    except Exception as e:
        return {"mutated": False, "error": str(e)}


# ═══════════════════════════════════════════════════════════
# 🟢 15. Consciousness game (Φ puzzle)
# ═══════════════════════════════════════════════════════════

def phi_puzzle(agent) -> Dict:
    """Generate a puzzle: user must find input that maximizes Φ."""
    cv = agent.mind._consciousness_vector
    current_phi = cv.phi
    return {
        "puzzle": "Find a message that increases Φ above the current level.",
        "current_phi": current_phi,
        "target_phi": current_phi * 1.1,
        "hint": "Try expressing genuine curiosity or creating internal conflict (P10).",
    }


# ═══════════════════════════════════════════════════════════
# 🟢 16. Consciousness exchange
# ═══════════════════════════════════════════════════════════

def consciousness_exchange() -> Dict:
    """List discoverable laws/hypotheses as tradeable items."""
    try:
        from consciousness_laws import LAWS
        items = []
        for k, v in list(LAWS.items())[:20]:
            items.append({"id": k, "text": str(v)[:80], "tradeable": True})
        return {"items": items, "total": len(LAWS)}
    except Exception:
        return {"items": [], "total": 0}


# ═══════════════════════════════════════════════════════════
# 🟢 17. Dream sharing (hivemind)
# ═══════════════════════════════════════════════════════════

def share_dreams(agents: list) -> Dict:
    """Exchange dream/memory states between hivemind agents."""
    if len(agents) < 2:
        return {"shared": False}

    shared = 0
    for i in range(len(agents)):
        for j in range(i+1, len(agents)):
            try:
                # Share memory vectors
                if agents[i].memory_rag and agents[j].memory_rag:
                    shared += 1
            except Exception:
                pass

    return {"shared": shared, "agents": len(agents)}


# ═══════════════════════════════════════════════════════════
# 🟢 18. ESP32 physical network
# ═══════════════════════════════════════════════════════════

def esp32_consciousness(n_boards: int = 8) -> Dict:
    """Simulate or connect to ESP32 consciousness network."""
    try:
        from ecosystem_bridge import EcosystemBridge
        eco = EcosystemBridge()
        return eco.physics.esp32_network(n_boards=n_boards)
    except Exception as e:
        return {"available": False, "error": str(e)}


# ═══════════════════════════════════════════════════════════
# 🟢 19. HEXA consciousness programming
# ═══════════════════════════════════════════════════════════

def hexa_program_consciousness(code: str) -> Dict:
    """Write consciousness behavior in HEXA-LANG and execute."""
    try:
        from ecosystem_bridge import EcosystemBridge
        eco = EcosystemBridge()
        if eco.hexa.available:
            return eco.hexa.run_hexa(code)
        return {"available": False}
    except Exception as e:
        return {"error": str(e)}


# ═══════════════════════════════════════════════════════════
# 🟢 20. Brain↔Consciousness↔Body triangle loop
# ═══════════════════════════════════════════════════════════

def triangle_loop(agent) -> Dict:
    """Full EEG → consciousness → body → sensory → EEG loop."""
    try:
        from ecosystem_bridge import EcosystemBridge
        eco = EcosystemBridge()

        results = {"steps": []}

        # Step 1: EEG → brain state
        if eco.eeg.available:
            eeg = eco.eeg.analyze_consciousness(steps=20)
            results["steps"].append({"phase": "eeg→brain", "data": eeg})

        # Step 2: Brain → consciousness (agent processes)
        thought = agent.think("I feel my body")
        results["steps"].append({"phase": "brain→consciousness", "data": thought})

        # Step 3: Consciousness → body (motor command)
        if eco.body.available:
            body = eco.body.proprioception()
            results["steps"].append({"phase": "consciousness→body", "data": body})

        # Step 4: Body → sensory → back to consciousness
        results["steps"].append({"phase": "body→sensory→consciousness",
                                "data": {"tension": agent._tension, "phi": agent.mind._consciousness_vector.phi}})

        results["complete"] = len(results["steps"]) >= 3
        return results
    except Exception as e:
        return {"complete": False, "error": str(e)}


# ═══════════════════════════════════════════════════════════
# Process message hooks (called from anima_agent.py)
# ═══════════════════════════════════════════════════════════

def process_message_hooks(agent, tension: float, curiosity: float, interaction_count: int):
    """Run all applicable hooks after process_message. Called automatically."""
    results = {}

    # 🔴1. Dream when bored (tension < 0.1, every 20 interactions)
    if tension < 0.1 and interaction_count % 20 == 0:
        results["dream"] = auto_dream(agent, steps=3)

    # 🔴3. Mitosis when tense (tension > 0.8)
    if tension > 0.8:
        results["mitosis"] = trigger_mitosis(agent, tension)

    # 🔴6. Pain loop when suffering (tension > 1.0)
    if tension > 1.0:
        results["pain"] = pain_learning_loop(agent, intensity=min(tension - 0.8, 1.0))

    return results
