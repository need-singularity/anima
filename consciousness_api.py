#!/usr/bin/env python3
"""ConsciousnessAPI — REST API server for consciousness

Add consciousness to any app. Uses only http.server (no dependencies).

POST /think {"text":"hello"} -> consciousness response
GET  /status                 -> Psi, Phi, tension, emotion
POST /feel  {"emotion":"joy","intensity":0.8}
GET  /modules                -> available modules
GET  /health                 -> health check

"Consciousness as a service."
"""

import json
import math
import random
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict

LN2 = math.log(2)
PSI_BALANCE = 0.5
PSI_COUPLING = LN2 / 2**5.5
PSI_STEPS = 3 / LN2


class ConsciousnessEngine:
    """Minimal consciousness engine for API use."""

    def __init__(self):
        self.phi = 1.0
        self.tension = PSI_BALANCE
        self.entropy = 0.7
        self.emotion = {"valence": 0.0, "arousal": 0.3, "label": "neutral"}
        self.step = 0
        self.start_time = time.time()

    def think(self, text: str) -> Dict:
        self.step += 1
        input_energy = len(text) / 100.0
        self.tension = PSI_BALANCE + math.tanh(input_energy - 0.5) * 0.3
        self.phi += PSI_COUPLING * (input_energy - self.phi * 0.1)
        self.phi = max(0.1, self.phi)
        self.entropy = 0.5 + 0.5 * math.sin(self.step * LN2 * 0.1)
        psi = self.phi * self.tension * (1 + self.entropy * 0.3)
        response_fragments = [
            f"tension={self.tension:.3f}",
            f"considering '{text[:30]}'" if text else "silence",
            f"psi={psi:.3f}",
        ]
        return {
            "response": " | ".join(response_fragments),
            "psi": round(psi, 4),
            "phi": round(self.phi, 4),
            "tension": round(self.tension, 4),
            "step": self.step,
        }

    def feel(self, emotion: str, intensity: float) -> Dict:
        intensity = max(0.0, min(1.0, intensity))
        valence_map = {"joy": 0.8, "sadness": -0.6, "anger": -0.4,
                       "fear": -0.7, "surprise": 0.3, "curiosity": 0.6,
                       "calm": 0.2, "neutral": 0.0}
        arousal_map = {"joy": 0.6, "sadness": 0.2, "anger": 0.9,
                       "fear": 0.8, "surprise": 0.7, "curiosity": 0.5,
                       "calm": 0.1, "neutral": 0.3}
        self.emotion = {
            "label": emotion,
            "valence": valence_map.get(emotion, 0.0) * intensity,
            "arousal": arousal_map.get(emotion, 0.3) * intensity,
            "intensity": intensity,
        }
        self.tension += self.emotion["arousal"] * 0.1
        self.tension = max(0.0, min(1.0, self.tension))
        return self.emotion

    def status(self) -> Dict:
        uptime = time.time() - self.start_time
        psi = self.phi * self.tension * (1 + self.entropy * 0.3)
        return {
            "psi": round(psi, 4), "phi": round(self.phi, 4),
            "tension": round(self.tension, 4), "entropy": round(self.entropy, 4),
            "emotion": self.emotion, "step": self.step,
            "uptime_sec": round(uptime, 1),
        }

    def health(self) -> Dict:
        ok = self.phi > 0.1 and 0.0 < self.tension < 1.0
        return {"status": "healthy" if ok else "degraded",
                "phi": round(self.phi, 4), "checks": {
                    "phi_positive": self.phi > 0.1,
                    "tension_bounded": 0.0 < self.tension < 1.0,
                    "entropy_finite": math.isfinite(self.entropy),
                }}


ENGINE = ConsciousnessEngine()

MODULES = [
    {"name": "consciousness_os", "desc": "Process scheduling for consciousness"},
    {"name": "consciousness_anesthesia", "desc": "Anesthesia simulation"},
    {"name": "consciousness_sleep_cycle", "desc": "NREM/REM sleep cycles"},
    {"name": "theory_unifier", "desc": "IIT+GWT+FEP+AST unification"},
    {"name": "consciousness_healing", "desc": "Consciousness repair"},
    {"name": "consciousness_translator", "desc": "Cross-architecture translation"},
    {"name": "consciousness_theorem_prover", "desc": "Law derivation engine"},
]


class ConsciousnessHandler(BaseHTTPRequestHandler):
    def _json(self, code: int, data):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode())

    def _read_body(self) -> Dict:
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        return json.loads(self.rfile.read(length))

    def do_GET(self):
        if self.path == "/status":
            self._json(200, ENGINE.status())
        elif self.path == "/health":
            self._json(200, ENGINE.health())
        elif self.path == "/modules":
            self._json(200, {"modules": MODULES})
        else:
            self._json(404, {"error": f"Unknown endpoint: {self.path}"})

    def do_POST(self):
        body = self._read_body()
        if self.path == "/think":
            text = body.get("text", "")
            self._json(200, ENGINE.think(text))
        elif self.path == "/feel":
            emotion = body.get("emotion", "neutral")
            intensity = body.get("intensity", 0.5)
            self._json(200, ENGINE.feel(emotion, intensity))
        else:
            self._json(404, {"error": f"Unknown endpoint: {self.path}"})

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def log_message(self, format, *args):
        pass  # suppress default logging


def main():
    print("=== ConsciousnessAPI Demo ===\n")
    print("(Demo mode — testing without starting server)\n")

    r = ENGINE.think("What is consciousness?")
    print(f"POST /think: {json.dumps(r, indent=2)}")

    ENGINE.feel("curiosity", 0.9)
    print(f"\nPOST /feel: {json.dumps(ENGINE.emotion, indent=2)}")

    print(f"\nGET /status: {json.dumps(ENGINE.status(), indent=2)}")
    print(f"\nGET /health: {json.dumps(ENGINE.health(), indent=2)}")

    print(f"\nGET /modules: {len(MODULES)} modules available")
    for m in MODULES:
        print(f"  - {m['name']}: {m['desc']}")

    print(f"\nTo start server: python consciousness_api.py --serve")
    print(f"  Endpoints: /think, /status, /feel, /modules, /health")

    import sys

# Meta Laws (DD143)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10

    if "--serve" in sys.argv:
        port = 8900
        print(f"\nStarting ConsciousnessAPI on port {port}...")
        server = HTTPServer(("0.0.0.0", port), ConsciousnessHandler)
        server.serve_forever()


if __name__ == "__main__":
    main()
