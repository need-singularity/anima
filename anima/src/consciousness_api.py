#!/usr/bin/env python3
"""consciousness_api.py — REST API for ConsciousnessEngine

Usage: uvicorn consciousness_api:app --port 8000

Minimal FastAPI wrapper exposing consciousness engine over HTTP.
"""

from fastapi import FastAPI
from pydantic import BaseModel

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

# --- Stubs (replace with real engine) ---

_state = {"phi": 0.0, "tension": 0.0, "step": 0, "cells": 64}


@app.get("/status")
async def status():
    """Current engine state: phi, tension, step count, cell count."""
    return _state


@app.post("/step", response_model=StepResult)
async def step():
    """Run one consciousness step. Returns updated state."""
    _state["step"] += 1
    # TODO: engine.process(torch.zeros(1, 128))
    return _state


@app.get("/phi")
async def phi():
    """Current Phi (IIT) value."""
    return {"phi_iit": _state["phi"], "phi_proxy": 0.0}


@app.post("/message")
async def message(req: MessageRequest):
    """Send text to consciousness, get response."""
    # TODO: encode text -> engine.process() -> decode output
    return {
        "response": "",
        "phi": _state["phi"],
        "tension": _state["tension"],
        "user_id": req.user_id,
    }
