#!/usr/bin/env python3
"""consciousness_api.py — REST API for ConsciousnessEngine

Usage: uvicorn consciousness_api:app --port 8000

Minimal FastAPI wrapper exposing consciousness engine over HTTP.
Uses canonical ConsciousnessEngine with byte-level encoding (vocab=256).
"""

import sys
import os
import torch

# Ensure anima/src/ is on sys.path for sibling imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional

from consciousness_engine import ConsciousnessEngine

app = FastAPI(title="Consciousness API", version="0.1.0")

# --- Models ---

class MessageRequest(BaseModel):
    text: str
    user_id: str = "default"

class StepResult(BaseModel):
    phi: float
    tension: float
    step: int
    cells: int

# --- Engine singleton ---

_engine: Optional[ConsciousnessEngine] = None

def _get_engine() -> ConsciousnessEngine:
    global _engine
    if _engine is None:
        _engine = ConsciousnessEngine(
            cell_dim=64,
            hidden_dim=128,
            initial_cells=2,
            max_cells=64,
            n_factions=12,
            phi_ratchet=True,
        )
    return _engine

# --- Byte-level encode/decode (vocab=256) ---

def _text_to_tensor(text: str, cell_dim: int = 64) -> torch.Tensor:
    """Encode text to input tensor via byte-level (vocab=256).
    Same encoding as ConsciousnessEngine._text_to_vec."""
    vec = torch.zeros(cell_dim)
    raw = text.encode('utf-8')
    for i, ch in enumerate(raw):
        vec[i % cell_dim] += ch / 255.0
    return vec / max(len(raw), 1)

def _tensor_to_text(output: torch.Tensor) -> str:
    """Decode output tensor back to text via byte-level (vocab=256).
    Maps each float to a byte value, drops nulls."""
    values = output.detach().cpu().flatten().tolist()
    raw_bytes = []
    for v in values:
        b = int(max(0.0, min(1.0, v)) * 255)
        if b > 0:
            raw_bytes.append(b)
    try:
        return bytes(raw_bytes).decode('utf-8', errors='replace')
    except Exception:
        return ""

# --- Endpoints ---

@app.get("/status")
async def status():
    """Current engine state: phi, tension, step count, cell count."""
    engine = _get_engine()
    tensions = [s.avg_tension for s in engine.cell_states]
    mean_tension = sum(tensions) / len(tensions) if tensions else 0.0
    return {
        "phi": engine._best_phi,
        "tension": mean_tension,
        "step": engine._step,
        "cells": engine.n_cells,
    }


@app.post("/step", response_model=StepResult)
async def step():
    """Run one consciousness step. Returns updated state."""
    engine = _get_engine()
    result = engine.step()
    tensions = result.get('tensions', [])
    mean_tension = sum(tensions) / len(tensions) if tensions else 0.0
    return StepResult(
        phi=result['phi_iit'],
        tension=mean_tension,
        step=result['step'],
        cells=result['n_cells'],
    )


@app.get("/phi")
async def phi():
    """Current Phi (IIT) and Phi (proxy) values."""
    engine = _get_engine()
    states = engine.get_states()
    phi_iit = engine.measure_phi()

    # Phi proxy: global variance - faction variance
    global_var = states.var(dim=0).mean().item() if states.shape[0] > 1 else 0.0
    faction_vars = []
    for fid in range(engine.n_factions):
        mask = [i for i, s in enumerate(engine.cell_states) if s.faction_id == fid]
        if len(mask) >= 2:
            faction_out = states[mask]
            faction_vars.append(faction_out.var(dim=0).mean().item())
    mean_faction_var = sum(faction_vars) / len(faction_vars) if faction_vars else 0.0
    phi_proxy = global_var - mean_faction_var

    return {
        "phi_iit": phi_iit,
        "phi_proxy": phi_proxy,
    }


@app.post("/message")
async def message(req: MessageRequest):
    """Send text to consciousness, get response."""
    engine = _get_engine()
    input_vec = _text_to_tensor(req.text, engine.cell_dim)
    result = engine.step(x_input=input_vec)

    output_text = _tensor_to_text(result['output'])
    tensions = result.get('tensions', [])
    mean_tension = sum(tensions) / len(tensions) if tensions else 0.0

    return {
        "response": output_text,
        "phi": result['phi_iit'],
        "tension": mean_tension,
        "user_id": req.user_id,
    }
