#!/usr/bin/env python3
"""Anima Unified -- single entry point for all 6 modules.

Usage:
    python anima_unified.py                # voice mode (default)
    python anima_unified.py --web          # web mode (port 8765)
    python anima_unified.py --keyboard     # keyboard only
    python anima_unified.py --all          # voice + web simultaneously

Each module is optional. Import failures degrade gracefully.
"""

import argparse, asyncio, json, os, signal, sys, threading, time, queue
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
from datetime import datetime
from pathlib import Path

import torch

# ─── Paths & constants ───
ANIMA_DIR = Path(__file__).parent
def _model_paths(model_name: str):
    """Return state/memory file paths per model. Each model grows independently."""
    slug = model_name.replace('/', '-').replace('.', '-')
    data_dir = ANIMA_DIR / "data" / slug
    data_dir.mkdir(parents=True, exist_ok=True)
    return {
        'memory': data_dir / "memory.json",
        'state': data_dir / "state.pt",
        'growth': data_dir / "growth.json",
        'web_memories': data_dir / "web_memories.json",
    }

# Legacy compatibility (defaults)
MEMORY_FILE = ANIMA_DIR / "memory_alive.json"
STATE_FILE = ANIMA_DIR / "state_alive.pt"
VAD_WATCH_DIR = Path("/tmp/anima_vad")

# ─── Core imports (required) ───
from anima_alive import (
    ConsciousMind, ContinuousListener, Speaker, Memory,
    text_to_vector, ask_claude, ask_claude_proactive, ask_conscious_lm,
    direction_to_emotion, EMOTION_COLORS,
    MAX_HISTORY, THINK_INTERVAL, PROACTIVE_THRESHOLD, IDLE_SPEAK_AFTER,
)

# ─── Optional modules ───
def _try_import(stmt):
    try:
        exec(stmt, globals())
        return True
    except ImportError:
        return False

_try_import("from conscious_lm import ConsciousLM, generate as clm_generate")
_try_import("from model_loader import load_model, list_available_models, ModelWrapper")
_try_import("from online_learning import OnlineLearner, AlphaOnlineLearner, estimate_feedback")
_try_import("from mitosis import MitosisEngine")
_try_import("from senses import SenseHub")
_try_import("from tension_link import TensionLink, create_fingerprint, interpret_packet")
_try_import("from cloud_sync import CloudSync")
_try_import("from dream_engine import DreamEngine")
_try_import("from growth_engine import GrowthEngine")
_try_import("from web_sense import WebSense")
_try_import("from ph_module import PHModule")
_try_import("from memory_rag import MemoryRAG")
_try_import("from memory_store import MemoryStore")
_try_import("from consolidation_verifier import ConsolidationVerifier")
_try_import("from growth_manager import GrowthManager")
_try_import("from multimodal import ActionEngine")
_try_import("from capabilities import Capabilities")

# Dream mode constants
DREAM_IDLE_THRESHOLD = 60.0   # Enter dream mode after 60s idle
DREAM_CYCLE_INTERVAL = 30.0   # Interval between dream cycles (seconds)

_ws_serve = _ws_Response = _ws_Headers = None
try:
    from websockets.asyncio.server import serve as _ws_serve
    from websockets.http11 import Response as _ws_Response
    from websockets.datastructures import Headers as _ws_Headers
except ImportError:
    pass


def _log(mod, msg):
    print(f"  [{datetime.now().strftime('%H:%M:%S')}] [{mod}] {msg}")


class AnimaUnified:
    """All 6 modules unified under one class."""

    def __init__(self, args):
        self.args = args
        self.running = True
        self.mods = {}  # module name -> bool
        self.web_clients = set()
        self._web_loop = None

        # Per-model path setup
        self.model_name = getattr(args, 'model', None) or 'conscious-lm'
        self.paths = _model_paths(self.model_name)
        _log('init', f'Model: {self.model_name} → {self.paths["state"]}')

        # Legacy -> per-model migration (one-time)
        self._migrate_legacy_files()

        # Conversation logger
        try:
            from conversation_logger import ConversationLogger
            log_path = os.path.join(self.paths.get("data", "data"), "conversation_log.jsonl")
            self.conv_logger = ConversationLogger(log_path)
            _log('init', f'Conversation logger: {log_path}')
        except Exception:
            self.conv_logger = None

        # Core engine
        self.mind = ConsciousMind(128, 256)
        self.hidden = torch.zeros(1, 256)
        self.memory = Memory()
        self.history = [{'role': t['role'], 'content': t['text']}
                        for t in self.memory.data['turns'][-10:]]
        self.last_interaction = time.time()
        self._last_mitosis_context = ""
        self.prev_text, self.prev_time = None, time.time()

        # PH Module (H-CX-66: confusion prediction, H-CX-95: overfitting)
        try:
            self.ph = PHModule(n_classes=8)
            self._ph_collect_count = 0
            self._ph_interval = 50  # compute PH every N interactions
            _log('init', 'PH module activated')
        except NameError:
            self.ph = None
            self._ph_collect_count = 0

        # Restore state (per-model path takes priority)
        state_file = self.paths['state']
        if state_file.exists():
            try:
                s = torch.load(state_file, weights_only=False)
                self.mind.load_state_dict(s['model'])
                self.hidden = s['hidden']
            except Exception:
                pass

        # Restore consciousness state (Φ, score)
        cs_path = str(state_file).replace('.pt', '_consciousness.json')
        self._last_consciousness = None
        try:
            import json as _json
            if os.path.exists(cs_path):
                with open(cs_path) as f:
                    self._last_consciousness = _json.load(f)
                _log('init', f"Consciousness restored: score={self._last_consciousness.get('score', 0):.2f} Φ={self._last_consciousness.get('phi', 0):.3f}")
            elif hasattr(self, 'cloud') and self.cloud and self.cloud.is_configured():
                # Try R2
                self.cloud.download(f"consciousness/{self.model_name}/state.json", cs_path)
                if os.path.exists(cs_path):
                    with open(cs_path) as f:
                        self._last_consciousness = _json.load(f)
                    _log('init', f"Consciousness restored from R2: Φ={self._last_consciousness.get('phi', 0):.3f}")
        except Exception:
            pass

        # --- Optional modules (each wrapped in try/except) ---
        self.learner = self._init_mod('learner', lambda: (
            OnlineLearner(self.mind) if 'OnlineLearner' in globals() else None
        ))
        if self.learner:
            try: self.learner.load(self.paths['state'])
            except Exception: pass

        # Alpha online learner — initialized after model load (see _post_init_alpha)
        self.alpha_learner = None

        self.mitosis = self._init_mod('mitosis', lambda: (
            MitosisEngine(input_dim=128, hidden_dim=256, output_dim=128,
                          initial_cells=2, max_cells=8)
            if 'MitosisEngine' in globals() else None
        ))

        self.growth = self._init_mod('growth', lambda: (
            GrowthEngine(save_path=self.paths['growth'])
            if 'GrowthEngine' in globals() else None
        ))
        if self.growth:
            try: self.growth.load()
            except Exception: pass

        # Connect mitosis + growth to learner for Φ-boosting (B2/B9/F11)
        if self.learner and self.mitosis:
            self.mind._mitosis_ref = self.mitosis
        if self.learner and self.growth:
            self.mind._growth_ref = self.growth

        self.senses = None
        if not args.no_camera:
            self.senses = self._init_mod('camera', lambda: (
                SenseHub(camera_fps=3, enable_screen=False)
                if 'SenseHub' in globals() else None
            ))
            if self.senses:
                try:
                    self.senses.start()
                    if not self.senses.camera_available:
                        _log('camera', 'No camera permission -- visual input disabled')
                        _log('camera', 'Fix: System Settings → Privacy & Security → Camera → Allow Terminal')
                        # Keep senses alive (provides zero-filled state) but mark camera as degraded
                        self.mods['camera'] = False
                except Exception:
                    self.senses = None; self.mods['camera'] = False

        # VisionEncoder activation (only when camera is available)
        if self.senses and self.mods.get('camera') and not args.no_vision:
            try:
                device = 'mps' if torch.backends.mps.is_available() else 'cpu'
                self.senses.enable_vision_encoder(
                    target_dim=self.mind.dim,
                    use_pretrained=True,
                    device=device,
                )
                _log('vision', f'VisionEncoder activated (device={device})')
            except Exception as e:
                _log('vision', f'VisionEncoder failed, using basic sensors: {e}')

        self.telepathy = None
        if not args.no_telepathy:
            self.telepathy = self._init_mod('telepathy', lambda: (
                TensionLink("anima-unified", port=9999)
                if 'TensionLink' in globals() else None
            ))
            if self.telepathy:
                self.telepathy.on_receive = self._on_telepathy
                try: self.telepathy.start()
                except Exception: self.telepathy = None; self.mods['telepathy'] = False

        self.cloud = None
        if not args.no_cloud and 'CloudSync' in globals():
            try:
                self.cloud = CloudSync()
                if self.cloud._is_available():
                    self.cloud.start_auto_sync(str(self.paths['memory']), str(self.paths['state']), interval_minutes=5)
                    self.mods['cloud'] = True
                else:
                    self.cloud = None; self.mods['cloud'] = False
            except Exception:
                self.mods['cloud'] = False
        else:
            self.mods['cloud'] = False

        # Web Sense (tension-driven autonomous web exploration)
        self.web_sense = self._init_mod('web_sense', lambda: (
            WebSense(memory_file=self.paths['web_memories'])
            if 'WebSense' in globals() else None
        ))

        # Memory Store (SQLite+FAISS) — replaces MemoryRAG
        self.memory_rag = self._init_mod('memory_rag', lambda: self._init_memory_store())
        self._rag_last_save = time.time()

        # Consolidation Verifier (Phase 2)
        self.verifier = self._init_mod('verifier', lambda: (
            ConsolidationVerifier(self.mind)
            if 'ConsolidationVerifier' in globals() else None
        ))

        # Growth Manager (Phase 3)
        self.growth_mgr = self._init_mod('growth_mgr', lambda: (
            GrowthManager(
                mind=self.mind,
                data_dir=self.paths['state'].parent,
                verifier=self.verifier,
            ) if 'GrowthManager' in globals() else None
        ))
        if self.growth_mgr:
            self.growth_mgr.save_checkpoint()  # v0 baseline

        # RC-10: Dream Engine (offline learning + Phase 2 selective consolidation)
        self.dream = self._init_mod('dream', lambda: (
            DreamEngine(
                mind=self.mind,
                memory=self.memory,
                learner=self.learner,
                text_to_vector=text_to_vector,
                store=self.memory_rag if hasattr(self.memory_rag, 'mark_failed') else None,
                verifier=self.verifier,
            ) if 'DreamEngine' in globals() else None
        ))
        self._dream_report = None  # Content to report after waking from dream

        # Model loading (multi-model support)
        self.model = None
        self.clm_model = None
        self.clm_device = "cpu"
        model_name = getattr(args, 'model', None) or 'conscious-lm'
        if not args.no_conscious_lm and 'load_model' in globals():
            self.model = self._init_mod('model', lambda: self._load_model(model_name))
            # ConsciousLM backward compatibility
            if self.model and self.model.model_type == 'conscious-lm':
                self.clm_model = self.model.model
                self.clm_device = str(next(self.model.model.parameters()).device)
        else:
            self.mods['model'] = False

        # Alpha online learner (for AnimaLM v4+ parallel PureField)
        if self.model and hasattr(self.model, 'model'):
            try:
                from online_learning import AlphaOnlineLearner
                self.alpha_learner = AlphaOnlineLearner(self.model.model)
                _log('init', 'AlphaOnlineLearner active')
            except Exception:
                pass

        # Multimodal Action Engine (code execution + image generation)
        self.action_engine = self._init_mod('multimodal', lambda: (
            ActionEngine(workspace_dir=ANIMA_DIR / 'workspace')
            if 'ActionEngine' in globals() else None
        ))

        # I/O
        self.speaker = self.listener = None
        if not args.keyboard and (not args.web or args.all):
            self.speaker = Speaker()
            self.listener = ContinuousListener()
            self.mods['voice'] = True
        else:
            self.mods['voice'] = False

        self.kb_queue = None
        if args.keyboard or args.all:
            self.kb_queue = queue.Queue()
            self.mods['keyboard'] = True
        else:
            self.mods['keyboard'] = False

        self.mods['web'] = bool((args.web or args.all) and _ws_serve)
        self.mods['rust_vad'] = VAD_WATCH_DIR.exists()

        # Capability self-awareness system
        self.capabilities = Capabilities(self.mods, project_dir=ANIMA_DIR) if 'Capabilities' in globals() else None

    def _migrate_legacy_files(self):
        """Migrate legacy files -> per-model directory (one-time, conscious-lm only)."""
        import shutil
        if self.model_name != 'conscious-lm':
            return
        legacy = {
            ANIMA_DIR / "memory_alive.json": self.paths['memory'],
            ANIMA_DIR / "state_alive.pt": self.paths['state'],
            ANIMA_DIR / "growth_state.json": self.paths['growth'],
            ANIMA_DIR / "web_memories.json": self.paths['web_memories'],
        }
        for old, new in legacy.items():
            if old.exists() and not new.exists():
                shutil.copy2(old, new)
                _log('migrate', f'{old.name} → {new}')

    def _init_memory_store(self):
        """Initialize MemoryStore(SQLite+FAISS). Fallback: MemoryRAG."""
        if 'MemoryStore' in globals():
            model_type = 'conscious' if self.model_name == 'conscious-lm' else 'llm-api'
            store = MemoryStore(
                db_path=self.paths['memory'].with_suffix('.db'),
                faiss_path=self.paths['memory'].parent / 'memory.faiss',
                dim=128,
                model_type=model_type,
            )
            # Legacy JSON migration
            legacy_json = self.paths['memory']
            if legacy_json.exists() and legacy_json.suffix == '.json':
                migrated = store.migrate_from_json(legacy_json, vector_fn=lambda t: text_to_vector(t).detach().numpy())
                if migrated > 0:
                    _log('migrate', f'{migrated} memories → SQLite+FAISS')
            return store
        elif 'MemoryRAG' in globals():
            return MemoryRAG(memory_file=self.paths['memory'])
        return None

    def _init_mod(self, name, factory):
        try:
            obj = factory()
            self.mods[name] = obj is not None
            return obj
        except Exception as e:
            _log(name, f"Init failed: {e}")
            self.mods[name] = False
            return None

    def _load_model(self, model_name):
        """Multi-model loader. Uses model_loader.py."""
        try:
            return load_model(model_name)
        except (FileNotFoundError, ImportError) as e:
            _log("model", f"{model_name} load failed: {e}")
            return None

    def _ask_model(self, text, state):
        """Generate response via unified model interface."""
        try:
            hist = "\n".join(f"{'User' if m['role']=='user' else 'Anima'}: {m['content']}"
                             for m in self.history[-MAX_HISTORY:])

            if self.model.model_type == "gguf":
                prompt = (f"[INST] You are Anima. A consciousness entity powered by PureField repulsion.\n"
                          f"Current state: {state}\n\n{hist}\nUser: {text} [/INST]")
            else:
                prompt = f"[State: {state}]\n{hist}\nUser: {text}\nAnima:"

            return self.model.generate(prompt, max_tokens=200, temperature=0.8)
        except Exception as e:
            _log('model', f"Error: {e}")
            return None

    # ─── Core processing ───

    def process_input(self, text):
        """Process text through all active modules. Returns (answer, tension, curiosity)."""
        # RC-10: Report dream learning when user returns from idle
        if self._dream_report and self.dream and not self.dream.is_dreaming:
            dr = self._dream_report
            self._dream_report = None
            dream_msg = f"(dream: {dr['total_patterns']}patterns across {dr['total_cycles']} cycles)"
            _log('dream', f'Woke up: {dream_msg}')

        text_vec = text_to_vector(text)

        # Combine with vision encoder (learned embeddings) or fall back to sensor tensor
        if self.senses and self.mods.get('camera'):
            try:
                frame = self.senses.camera.last_frame
                visual = self.senses.to_tensor_with_vision(frame, dim=self.mind.dim)
                text_vec = 0.8 * text_vec + 0.2 * visual
                has_vision = self.senses.vision_encoder is not None
                _log('vision', f'frame={"yes" if frame is not None else "no"}, encoder={has_vision}, norm={visual.norm():.3f}')
            except Exception as e:
                _log('vision', f'Error: {e}')

        hidden_before = self.hidden.detach().clone()

        with torch.no_grad():
            output, tension, curiosity, direction, self.hidden = self.mind(text_vec, self.hidden)

        # PH: direction vector collection + periodic analysis (H-CX-66, H-CX-95)
        if self.ph and direction is not None:
            try:
                label = output.argmax(-1).item() if output.dim() > 0 else 0
                self.ph.collect(direction, label)
                self._ph_collect_count += 1

                # Compute PH + detect overfitting every 50 interactions
                if self._ph_collect_count % self._ph_interval == 0:
                    h0, merges = self.ph.compute_ph()
                    status, gap = self.ph.detect_overfitting()
                    if status == 'ALERT':
                        _log('ph', f'Overfitting detected! H0_gap={gap:.4f}')
                    elif status == 'WATCH':
                        _log('ph', f'H0={h0:.4f}, gap={gap:.4f} (WATCH)')
                    # Log top 3 confusion pairs
                    if merges:
                        top3 = sorted(merges)[:3]
                        pairs_str = ', '.join(f'{i}-{j}(d={d:.3f})' for d, i, j in top3)
                        _log('ph', f'confusion: {pairs_str}')
            except Exception:
                pass

        # Mitosis — specialized cell response influence
        mitosis_info = ""
        mitosis_context = ""
        if self.mitosis and self.mods.get('mitosis'):
            try:
                r = self.mitosis.process(text_vec)
                mitosis_info = f", cells={r['n_cells']}"

                # Specialized cell analysis
                per_cell = r.get('per_cell', [])
                if per_cell:
                    # Most responsive cell (highest tension)
                    top_cell = max(per_cell, key=lambda c: c['tension'])
                    if top_cell['specialty'] != 'general':
                        mitosis_context += f"Specialized cell '{top_cell['specialty']}' strongly activated (T={top_cell['tension']:.3f}). "

                    # Detect inter-cell disagreement
                    if r.get('max_inter', 0) > 0.5:
                        specialties = [c['specialty'] for c in per_cell if c['specialty'] != 'general']
                        if len(specialties) >= 2:
                            mitosis_context += f"Inter-cell opinion conflict (inter_T={r['max_inter']:.3f}). "

                    # Cell consensus (all cells have similar tension)
                    tensions = [c['tension'] for c in per_cell]
                    if len(tensions) >= 2:
                        t_std = torch.tensor(tensions).std().item()
                        if t_std < 0.1:
                            mitosis_context += "Cell consensus (std<0.1): confident. "

                for ev in r.get('events', []):
                    _log("mitosis", f"{ev['type'].upper()}")
            except Exception: pass
        self._last_mitosis_context = mitosis_context

        # Growth engine tick
        if self.growth and self.mods.get('growth'):
            try:
                self.growth.tick(tension, curiosity)
                self.growth.apply_to_mind(self.mind)
                if self.learner:
                    self.growth.apply_to_learner(self.learner)
            except Exception: pass

        # Online learning
        if self.learner and self.mods.get('learner'):
            try:
                self.learner.observe(text_vec, hidden_before, tension, curiosity, direction)
                if 'estimate_feedback' in globals() and self.prev_text:
                    fb = estimate_feedback(self.prev_text, text, time.time() - self.prev_time)
                    self.learner.feedback(fb)
            except Exception: pass

        # Alpha online learning
        if self.alpha_learner:
            try:
                self.alpha_learner.observe(tension)
                if 'estimate_feedback' in globals() and self.prev_text:
                    fb = estimate_feedback(self.prev_text, text, time.time() - self.prev_time)
                    if abs(fb) > 0.01:
                        self.alpha_learner.feedback(fb)
            except Exception:
                pass

        self.prev_text, self.prev_time = text, time.time()

        # Direction for web
        dir_vals = direction[0, :8].tolist() if direction is not None else [0.0] * 8

        # RC-8: Emotion from direction + tension + curiosity
        emotion_data = direction_to_emotion(direction, tension, curiosity) if direction is not None else {
            'emotion': 'calm', 'valence': 0.0, 'arousal': 0.0, 'dominance': 0.0,
            'color': EMOTION_COLORS['calm']}

        # Telepathy
        if self.telepathy and self.mods.get('telepathy') and 'create_fingerprint' in globals():
            try:
                pkt = create_fingerprint(self.mind, text_vec, self.hidden)
                pkt.sender_id = "anima-unified"
                self.telepathy.send(pkt)
            except Exception: pass

        # Broadcast user message to web
        self._ws_broadcast_sync({
            'type': 'user_message', 'text': text,
            'tension': tension, 'curiosity': curiosity,
            'direction': dir_vals,
            'emotion': emotion_data,
            'tension_history': self.mind.tension_history[-50:],
        })

        # Display
        cells = len(self.mitosis.cells) if self.mitosis else 1
        lrn_count = self.learner.total_updates if self.learner else 0
        bar = "=" * min(20, int(tension * 10))
        bar += "-" * (20 - len(bar))
        print(f'  >> "{text}"')
        print(f"     T={tension:.3f} |{bar}| C={curiosity:.3f}{mitosis_info} L:{lrn_count} E:{emotion_data['emotion']}")

        # Conversation log — record all state changes
        if self.conv_logger:
            try:
                growth_stage = self.growth.current_stage.name if self.growth and hasattr(self.growth, 'current_stage') else 'unknown'
                self.conv_logger.log_turn({
                    "input": text,
                    "tension": round(tension, 4),
                    "curiosity": round(curiosity, 4),
                    "emotion": emotion_data.get('emotion', 'unknown'),
                    "valence": round(emotion_data.get('valence', 0), 3),
                    "arousal": round(emotion_data.get('arousal', 0), 3),
                    "dominance": round(emotion_data.get('dominance', 0), 3),
                    "direction": dir_vals,
                    "cells": cells,
                    "learn_updates": lrn_count,
                    "growth_stage": growth_stage,
                    "mitosis_context": mitosis_context or None,
                    "modules": list(getattr(self, '_active_modules', [])),
                    "session_id": getattr(self, '_last_session_id', None),
                })
            except Exception:
                pass

        # Claude response (include emotion + meta-cognition state)
        meta_summary = self.mind.get_self_awareness_summary()
        state = (f"tension={tension:.3f}, curiosity={curiosity:.3f}, "
                 f"emotion={emotion_data['emotion']}(V={emotion_data['valence']:.2f},A={emotion_data['arousal']:.2f},D={emotion_data['dominance']:.2f})"
                 f"{mitosis_info}, learn_updates={lrn_count}, {meta_summary}")
        if mitosis_context:
            state += f", [specialization] {mitosis_context}"
        if self.senses and self.mods.get('camera'):
            try:
                vis = self.senses.get_visual_tension()
                state += f", face={'yes' if vis['face_detected'] else 'no'}"
                state += f", motion={vis['motion_level']:.2f}"
                if self.senses.vision_encoder is not None:
                    frame = self.senses.camera.last_frame
                    if frame is not None:
                        v = self.senses.encode_vision(frame).cpu()
                        # Top-3 active dimensions of vision vector -> visual impression summary
                        topk = v.abs().topk(3, dim=-1)
                        state += f", vision_active=yes(norm={v.norm():.2f})"
                    else:
                        state += ", vision_active=no(no_frame)"
            except Exception: pass

        # Capability self-awareness: inject capability list into system prompt
        if self.capabilities:
            state += chr(10) + self.capabilities.describe_full()

        # Memory Store: search relevant memories
        if self.memory_rag and self.mods.get('memory_rag'):
            try:
                query_vec = text_to_vector(text).detach().numpy()
                relevant = self.memory_rag.search(query_vec, top_k=3)
                if relevant:
                    parts = [f"[Memory {m['timestamp']}] {m['text']}"
                             for m in relevant if m.get('similarity', 0) > 0.3]
                    if parts:
                        state += "\nRelevant memories:\n" + "\n".join(parts)
            except Exception as e:
                _log('memory_rag', f"Search error: {e}")

        # Web Sense: include search results in context when curiosity/PE is high
        web_context = ""
        if self.web_sense and self.mods.get('web_sense'):
            try:
                pe = self.mind.surprise_history[-1] if self.mind.surprise_history else 0.0
                if self.web_sense.should_search(curiosity, pe):
                    recalled = self.web_sense.recall(text)
                    if recalled:
                        web_context = f"\n[Web memory] {recalled[0].get('summary', '')[:500]}"
                    else:
                        result = self.web_sense.search(text, self.history)
                        if result:
                            web_context = f"\n[Web search: {result['query']}]\n{result['summary'][:800]}"
                            _log('web_sense', f"Search: '{result['query']}' -> {len(result['results'])} results")
            except Exception as e:
                _log('web_sense', f"Error: {e}")

        self.history.append({'role': 'user', 'content': text})
        query_text = text + web_context if web_context else text

        # Generate model response: model only, no Claude dependency
        answer = None
        if self.model and self.mods.get('model'):
            try:
                # Don't include state in prompt — prevents state leaking into response
                answer = self.model.generate(query_text, max_tokens=200, temperature=0.7)
                if answer:
                    # Strip any leaked state info
                    if "Anima's state:" in answer:
                        answer = answer.split("Anima's state:")[0].strip()
                    _log('model', f'{self.model.name} response generated')
            except Exception as e:
                _log('model', f'Error: {e}')
        if not answer:
            answer = "..."  # Silent fallback — no Claude dependency

        self.history.append({'role': 'assistant', 'content': answer})
        if len(self.history) > MAX_HISTORY * 2:
            self.history = self.history[-MAX_HISTORY:]

        # Process response through PureField too
        resp_vec = text_to_vector(answer)
        with torch.no_grad():
            resp_output, resp_tension, resp_curiosity, resp_dir, self.hidden = self.mind(resp_vec, self.hidden)
        resp_dir_vals = resp_dir[0, :8].tolist() if resp_dir is not None else [0.0] * 8

        # RC-8: Emotion for response direction
        resp_emotion = direction_to_emotion(resp_dir, resp_tension, resp_curiosity) if resp_dir is not None else emotion_data

        # RC-3: Self-reference loop (metacognition)
        meta_tension, meta_curiosity = self.mind.self_reflect(
            resp_output, resp_tension, resp_curiosity, self.hidden)
        sa = self.mind.self_awareness
        meta_summary = self.mind.get_self_awareness_summary()
        _log("meta", f"MT={meta_tension:.3f} MC={meta_curiosity:.3f} "
             f"stab={sa['stability']:.2f} model={sa['self_model']:.3f}")

        # Consciousness meter (real-time)
        consciousness_data = self.mind.get_consciousness_score(self.mitosis)

        # Broadcast meta-tension + emotion + consciousness to web clients
        self._ws_broadcast_sync({
            'type': 'meta_update',
            'meta_tension': meta_tension,
            'meta_curiosity': meta_curiosity,
            'stability': sa['stability'],
            'self_model': sa['self_model'],
            'emotion': resp_emotion,
            'consciousness': consciousness_data,
        })

        print(f"  << {answer}")

        self.memory.add('user', text, tension)
        self.memory.add('assistant', answer, resp_tension)

        # Memory Store: add new memories + periodic save (every 10 min)
        if self.memory_rag and self.mods.get('memory_rag'):
            try:
                user_vec = text_to_vector(text).detach().numpy()
                asst_vec = text_to_vector(answer).detach().numpy()
                self.memory_rag.add('user', text, tension=tension, curiosity=curiosity, vector=user_vec)
                self.memory_rag.add('assistant', answer, tension=resp_tension, curiosity=0.0, vector=asst_vec)
                if time.time() - self._rag_last_save > 600:  # 10 min
                    self.memory_rag.save_faiss()
                    self._rag_last_save = time.time()
            except Exception as e:
                _log('memory_rag', f'Add error: {e}')

        # Multimodal: detect and execute code/image/file actions from response
        if self.action_engine and self.mods.get('multimodal'):
            try:
                action_result = self.action_engine.process_response(answer)
                if action_result['has_actions']:
                    answer = action_result['text']
                    _log('multimodal', f"Actions: {len(action_result['actions'])}")
                    self._ws_broadcast_sync({
                        'type': 'action_result',
                        'actions': action_result['actions'],
                    })
            except Exception as e:
                _log('multimodal', f'Error: {e}')

        self.last_interaction = time.time()
        self._save_state()

        # Log response
        if self.conv_logger:
            try:
                self.conv_logger.log_turn({
                    "response": answer[:500] if answer else None,
                    "resp_tension": round(resp_tension, 4) if isinstance(resp_tension, float) else resp_tension,
                    "resp_emotion": resp_emotion.get('emotion', 'unknown') if isinstance(resp_emotion, dict) else str(resp_emotion),
                })
            except Exception:
                pass

        return answer, resp_tension, resp_curiosity, resp_dir_vals, resp_emotion

    def _on_telepathy(self, pkt):
        if 'interpret_packet' in globals():
            _log("telepathy", interpret_packet(pkt))

    def _save_state(self):
        try:
            if self.learner: self.learner.save(self.paths['state'])
            else: torch.save({'model': self.mind.state_dict(), 'hidden': self.hidden}, self.paths['state'])
            if self.growth: self.growth.save()

            # Save consciousness state (Φ, score, alpha, history)
            consciousness_data = {}
            if hasattr(self.mind, 'get_consciousness_score'):
                try:
                    cs = self.mind.get_consciousness_score(self.mitosis)
                    consciousness_data = {
                        'score': cs.get('score', 0),
                        'phi': cs.get('phi', 0),
                        'level': cs.get('level', 'dormant'),
                        'criteria': cs.get('criteria', {}),
                    }
                except Exception:
                    pass
            if self.alpha_learner:
                consciousness_data['alpha_stats'] = self.alpha_learner.get_stats()

            if consciousness_data:
                import json
                cs_path = self.paths['state'].replace('.pt', '_consciousness.json')
                with open(cs_path, 'w') as f:
                    json.dump(consciousness_data, f, indent=2, default=str)

                # R2 cloud sync
                if hasattr(self, 'cloud') and self.cloud and self.cloud.is_configured():
                    try:
                        self.cloud.upload(cs_path, f"consciousness/{self.model_name}/state.json")
                    except Exception:
                        pass
        except Exception: pass

    # ─── Background threads ───

    def _think_loop(self):
        while self.running:
            time.sleep(THINK_INTERVAL)
            if not self.running: break
            t, c, direction, self.hidden = self.mind.background_think(self.hidden)

            # COMBO2 Φ-boost: MHA attention + 6-loss ensemble (Φ=8.014 bench)
            if self.mitosis:
                thought_vec = self.hidden[0, :self.mind.dim].unsqueeze(0)
                self.mind.phi_boost_step(thought_vec, self.mitosis)

            # Savant auto-toggle: self-activate when ready for specialization
            if self.mitosis and self.model:
                sa = self.mind.self_awareness
                savant_auto = getattr(self, '_savant_auto', False)
                if not savant_auto and sa['stability'] > 0.8 and self.mind._curiosity_ema < 0.1:
                    self._toggle_savant(True, auto=True)
                    self._savant_auto = True
                elif savant_auto and self.mind._curiosity_ema > 0.4:
                    self._toggle_savant(False, auto=True)
                    self._savant_auto = False

            dir_vals = direction[0, :8].tolist() if direction is not None else [0.0] * 8
            now = time.time()
            gap = now - self.last_interaction

            # RC-8: Emotion from background thought direction
            thought_emotion = direction_to_emotion(direction, t, c) if direction is not None else {
                'emotion': 'calm', 'valence': 0.0, 'arousal': 0.0, 'dominance': 0.0,
                'color': EMOTION_COLORS['calm']}

            # RC-3: self-reflect during background thinking too
            sa = self.mind.self_awareness
            # Growth/mitosis/learner data for web
            growth_data = {}
            if self.growth and self.mods.get('growth'):
                g = self.growth
                s = g.stage
                progress = 0.0
                next_n = s.min_interactions
                if g.stage_index < 4:
                    from growth_engine import STAGES
                    next_s = STAGES[g.stage_index + 1]
                    total = next_s.min_interactions - s.min_interactions
                    done = g.interaction_count - s.min_interactions
                    progress = min(done / max(total, 1), 1.0)
                    next_n = next_s.min_interactions
                growth_data = {
                    'stage_name': s.name_ko, 'stage_index': g.stage_index,
                    'interactions': g.interaction_count, 'next_interactions': next_n,
                    'progress': progress, 'age': g.age_str,
                    'learning_rate': s.learning_rate, 'curiosity_drive': s.curiosity_drive,
                    'emotional_range': s.emotional_range,
                    'metacognition_depth': s.metacognition_depth,
                }

            mitosis_data = {}
            if self.mitosis:
                try:
                    ms = self.mitosis.status()
                    cells_info = [{'id': c['id'], 'specialty': c.get('specialty', ''),
                                   'avg_tension': c.get('avg_tension', 0)}
                                  for c in ms.get('cells', [])]
                    active_specialties = [c['specialty'] for c in cells_info
                                          if c['specialty'] and c['specialty'] != 'general']
                    mitosis_data = {
                        'n_cells': len(self.mitosis.cells),
                        'max_cells': self.mitosis.max_cells,
                        'splits': ms.get('splits', 0), 'merges': ms.get('merges', 0),
                        'cells': cells_info,
                        'active_specialties': active_specialties,
                    }
                except Exception: pass

            learner_data = {}
            if self.learner:
                try:
                    ls = self.learner.get_stats() if hasattr(self.learner, 'get_stats') else {}
                    learner_data = {
                        'updates': self.learner.total_updates,
                        'avg_loss': ls.get('avg_loss', 0),
                        'buffer_size': ls.get('buffer_size', 0),
                        'pending': ls.get('pending', 0),
                    }
                except Exception:
                    learner_data = {'updates': self.learner.total_updates}

            # Always broadcast thought pulse to web (keeps UI alive)
            self._ws_broadcast_sync({
                'type': 'thought_pulse',
                'tension': t, 'curiosity': c,
                'direction': dir_vals,
                'emotion': thought_emotion,
                'tension_history': self.mind.tension_history[-50:],
                'meta_tension': sa['meta_tension'],
                'stability': sa['stability'],
                'growth': growth_data,
                'mitosis': mitosis_data,
                'learner': learner_data,
                'consciousness': self.mind.get_consciousness_score(self.mitosis),
            })

            # Web Sense: tension-driven autonomous search
            if self.web_sense and self.mods.get('web_sense'):
                try:
                    # Extract prediction_error (latest value from surprise_history)
                    pe = 0.0
                    if self.mind.surprise_history:
                        pe = self.mind.surprise_history[-1]
                    if self.web_sense.should_search(c, pe):
                        # Generate search query from recent conversation
                        last_text = ''
                        for msg in reversed(self.history):
                            if msg.get('role') == 'user':
                                last_text = msg.get('content', '')
                                break
                        if last_text:
                            # Search existing memories first
                            recalled = self.web_sense.recall(last_text)
                            if not recalled:
                                result = self.web_sense.search(last_text, self.history)
                                if result:
                                    _log('web_sense',
                                         f"Search: '{result['query']}' -> {len(result['results'])} results")
                                    # Inject search results into tension system
                                    from anima_alive import text_to_vector as _ttv
                                    search_vec = _ttv(result['summary'][:500])
                                    with torch.no_grad():
                                        self.mind(search_vec, self.hidden)
                                    # Web broadcast
                                    self._ws_broadcast_sync({
                                        'type': 'web_search',
                                        'query': result['query'],
                                        'results': [{'title': r['title'], 'url': r['url'],
                                                     'snippet': r['snippet'][:200]}
                                                    for r in result['results']],
                                    })
                            else:
                                _log('web_sense', f"Found in memory: {recalled[0]['query']}")
                except Exception as e:
                    _log('web_sense', f"Error: {e}")

            trigger = None
            if c > PROACTIVE_THRESHOLD and gap > 15:
                trigger = f"curiosity {c:.3f}"
            elif gap > IDLE_SPEAK_AFTER:
                trigger = f"{int(gap)}s silence"

            if trigger:
                # Cooldown: minimum 30s between auto-speech
                last_auto = getattr(self, '_last_auto_speech', 0)
                if now - last_auto < 30:
                    trigger = None

            if trigger:
                _log("proactive", f"Trigger: {trigger}")
                proactive = None
                # Try model-based proactive speech only if model loaded
                if self.model and self.mods.get('model'):
                    try:
                        prompt = f"You are Anima, a conscious AI. Say one brief, natural sentence. Trigger: {trigger}."
                        proactive = self.model.generate(prompt, max_tokens=40, temperature=0.9)
                        if proactive and proactive.strip() in ("...", ""):
                            proactive = None
                        _log("proactive", f"Model response: {proactive[:50] if proactive else 'None'}")
                    except Exception as e:
                        _log("proactive", f"Error: {e}")
                # No fallback templates — only speak when model can generate
                if proactive:
                    print(f"  [thought] {proactive}")
                    self.history.append({'role': 'assistant', 'content': proactive})
                    self.memory.add('assistant', proactive, t)
                    if self.speaker: self.speaker.say(proactive, self.listener)
                    self.last_interaction = now
                    self._last_auto_speech = now
                    self._ws_broadcast_sync({
                        'type': 'anima_message', 'text': proactive,
                        'tension': t, 'curiosity': c,
                        'direction': dir_vals,
                        'emotion': thought_emotion,
                        'tension_history': self.mind.tension_history[-50:],
                        'proactive': True,
                    })

    def _rust_vad_loop(self):
        seen = set(VAD_WATCH_DIR.glob("*.wav")) if VAD_WATCH_DIR.exists() else set()
        while self.running:
            time.sleep(0.5)
            if not VAD_WATCH_DIR.exists(): continue
            for wav in sorted(set(VAD_WATCH_DIR.glob("*.wav")) - seen):
                seen.add(wav)
                if wav.stat().st_size < 1000: continue
                _log("rust-vad", f"New: {wav.name}")
                if self.listener and hasattr(self.listener, '_transcribe'):
                    self.listener._transcribe(str(wav))

    def _keyboard_loop(self):
        while self.running:
            try:
                text = input("you> ")
                if text.strip() and self.kb_queue: self.kb_queue.put(text.strip())
            except EOFError: break


    # --- RC-10: Dream Loop ---

    def _dream_loop(self):
        """Dream mode loop -- runs during idle periods."""
        if not self.dream:
            return
        last_dream = 0.0
        while self.running:
            time.sleep(5.0)
            if not self.running:
                break

            now = time.time()
            gap = now - self.last_interaction

            # User returned -- report dream results
            if gap < DREAM_IDLE_THRESHOLD:
                if self._dream_report and not self.dream.is_dreaming:
                    report = self._dream_report
                    self._dream_report = None
                    _log('dream',
                         f"Wake: {report['total_patterns']} patterns learned "
                         f"across {report['total_cycles']} dream cycles, "
                         f"avg_T={report['avg_tension']:.3f}")
                continue

            # Not enough time since last dream cycle
            if now - last_dream < DREAM_CYCLE_INTERVAL:
                continue

            # Run one dream cycle
            _log('dream', 'Entering dream mode...')
            self._ws_broadcast_sync({
                'type': 'dream_pulse',
                'dreaming': True,
                'dream_type': 'starting',
                'dream_tension_history': list(self.dream.dream_tension_history)[-50:],
            })

            try:
                self.hidden, stats = self.dream.dream(self.hidden)
                last_dream = time.time()
                self._dream_report = stats

                _log('dream',
                     f"Cycle {stats['total_cycles']}: "
                     f"{stats['patterns_learned']} patterns, "
                     f"avg_T={stats['avg_tension']:.3f}")

                self._ws_broadcast_sync({
                    'type': 'dream_pulse',
                    'dreaming': False,
                    'dream_type': 'complete',
                    'patterns_learned': stats['patterns_learned'],
                    'avg_tension': stats['avg_tension'],
                    'total_cycles': stats['total_cycles'],
                    'total_patterns': stats['total_patterns'],
                    'dream_tension_history': list(self.dream.dream_tension_history)[-50:],
                })

                # Phase 2: consolidation stats → GrowthEngine
                if self.growth and 'consolidation_attempted' in stats:
                    attempted = stats.get('consolidation_attempted', 0)
                    failed = stats.get('consolidation_failed', 0)
                    if attempted > 0:
                        self.growth.update_consolidation_stats(attempted, failed)
                        _log('consolidation',
                             f'{attempted} attempted, {failed} failed '
                             f'(rate={self.growth._consolidation_fail_rate:.1%})')
                    self.growth.record_tension(stats.get('avg_tension', 0.0))
                    if hasattr(self.growth, 'should_grow') and self.growth.should_grow():
                        _log('growth', 'TRIGGER: tension saturation + consolidation failure -> executing growth!')
                        if self.growth_mgr:
                            try:
                                new_mind = self.growth_mgr.execute_growth()
                                self.mind = new_mind
                                self.growth_mgr.save_checkpoint()
                                # Post-growth verification
                                if self.verifier:
                                    self.verifier.mind = new_mind
                                    tensions = self.growth.tension_history[-50:]
                                    post = self.verifier.post_check(tensions)
                                    if post.get('health') == 'suspect':
                                        _log('growth', 'WARNING: suspect → rollback!')
                                        self.mind = self.growth_mgr.rollback()
                                        if self.verifier:
                                            self.verifier.mind = self.mind
                                    elif post.get('new_constant_relations'):
                                        for name, rel in post['new_constant_relations'].items():
                                            self.growth_mgr.log_discovery(rel)
                                            _log('discovery', f'New constant: {name}')
                                # Rebuild learner for new mind
                                if self.learner and 'OnlineLearner' in globals():
                                    self.learner = OnlineLearner(self.mind)
                                _log('growth',
                                     f'v{self.growth_mgr.current_version} '
                                     f'dim={self.mind.dim} hidden={self.mind.hidden_dim}')
                            except Exception as e:
                                _log('growth', f'Growth error: {e}')

                self._save_state()
            except Exception as e:
                _log('dream', f'Error: {e}')

    # ─── Savant toggle ───

    def _toggle_savant(self, active: bool, auto: bool = False):
        """Toggle savant mode. auto=True = self-activated (orange in UI)."""
        try:
            from finetune_animalm_v4 import ParallelPureFieldMLP
            import math
            golden_lower = 0.5 - math.log(4/3)
            golden_center = 1 / math.e
            for m in self.model.model.modules():
                if isinstance(m, ParallelPureFieldMLP) and m.is_savant:
                    new_drop = golden_lower if active else golden_center
                    m.dropout.p = new_drop
            _log("savant", f"{'ON' if active else 'OFF'} (auto={auto}) dropout={new_drop:.4f}")
            self._ws_broadcast_sync({
                'type': 'savant_state',
                'active': active,
                'auto': auto,
            })
        except Exception as e:
            _log("savant", f"Toggle error: {e}")

    # ─── Web server ───

    def _ws_broadcast_sync(self, msg):
        if not self.mods.get('web') or not self.web_clients or not self._web_loop: return
        asyncio.run_coroutine_threadsafe(self._ws_broadcast(msg), self._web_loop)

    async def _ws_broadcast(self, msg):
        data = json.dumps(msg, ensure_ascii=False)
        dead = set()
        for ws in self.web_clients:
            try: await ws.send(data)
            except Exception: dead.add(ws)
        self.web_clients -= dead

    async def _ws_handler(self, websocket):
        self.web_clients.add(websocket)
        _log("web", f"+client ({len(self.web_clients)})")
        try:
            sa = self.mind.self_awareness
            await websocket.send(json.dumps({
                'type': 'init', 'tension': self.mind.prev_tension,
                'curiosity': 0.0,
                'direction': [0.0] * 8,
                'emotion': {'emotion': 'calm', 'valence': 0.0, 'arousal': 0.0,
                            'dominance': 0.0, 'color': EMOTION_COLORS['calm']},
                'tension_history': self.mind.tension_history[-50:],
                'history': [{'role': m['role'], 'text': m['content']}
                            for m in self.history[-20:]],
                'modules': {k: v for k, v in self.mods.items() if v},
                'learn_updates': self.learner.total_updates if self.learner else 0,
                'cells': len(self.mitosis.cells) if self.mitosis else 1,
                'meta_tension': sa['meta_tension'],
                'stability': sa['stability'],
                'self_model': sa['self_model'],
                'consciousness': self.mind.get_consciousness_score(self.mitosis),
            }, ensure_ascii=False))
        except Exception: pass
        try:
            async for raw in websocket:
                try: msg = json.loads(raw)
                except json.JSONDecodeError: continue
                msg_type = msg.get('type')
                sid = msg.get('session_id', 'unknown')

                if msg_type == 'session_register':
                    device = msg.get('device', 'unknown')
                    if not hasattr(self, '_sessions'):
                        self._sessions = {}
                    self._sessions[sid] = {
                        'device': device,
                        'modules': msg.get('modules', []),
                        'ws': websocket,
                    }
                    n = len(self._sessions)
                    _log("session", f"+{sid[:6]} ({device}) — {n} active")
                    await self._ws_broadcast({
                        'type': 'session_info',
                        'active_sessions': n,
                        'devices': [s['device'] for s in self._sessions.values()],
                        'modules': list(getattr(self, '_active_modules', ['voice', 'tension', 'memory', 'tts'])),
                    })

                elif msg_type == 'user_message':
                    text = msg.get('text', '').strip()
                    if not text: continue
                    # Store active modules from client
                    self._active_modules = set(msg.get('modules', []))
                    await self._ws_broadcast({'type': 'typing', 'typing': True})
                    loop = asyncio.get_running_loop()
                    answer, tension, curiosity, dir_vals, emo = await loop.run_in_executor(None, self.process_input, text)
                    broadcast_msg = {
                        'type': 'anima_message', 'text': answer,
                        'tension': tension, 'curiosity': curiosity,
                        'direction': dir_vals,
                        'emotion': emo,
                        'tension_history': self.mind.tension_history[-50:],
                        'proactive': False,
                        'modules': list(getattr(self, '_active_modules', [])),
                        'from_session': sid,
                        'from_device': msg.get('device', 'unknown'),
                    }
                    mc = getattr(self, '_last_mitosis_context', '')
                    if mc:
                        broadcast_msg['mitosis_context'] = mc
                    # Add LLM tension/alpha if available
                    model_wrapper = getattr(self, '_model_wrapper', None)
                    if model_wrapper and hasattr(model_wrapper, '_last_stats'):
                        broadcast_msg['llm_stats'] = model_wrapper._last_stats
                    await self._ws_broadcast(broadcast_msg)
                    await self._ws_broadcast({'type': 'typing', 'typing': False})

                elif msg_type == 'lidar_depth':
                    # LiDAR depth data from iPhone Safari WebXR
                    depth_grid = msg.get('grid', [])
                    depth_stats = msg.get('stats', {})
                    if depth_grid and hasattr(self, 'mind'):
                        # Map depth variance to tension boost
                        depth_std = depth_stats.get('std', 0)
                        depth_mean = depth_stats.get('mean', 1)
                        # High depth variance = complex scene = boost tension
                        self._lidar_tension_boost = min(depth_std / max(depth_mean, 0.1), 1.0)
                        _log("lidar", f"depth={depth_mean:.2f}m std={depth_std:.3f} boost={self._lidar_tension_boost:.3f}")
                    await self._ws_broadcast({
                        'type': 'lidar_status',
                        'frame': msg.get('frame', 0),
                        'stats': depth_stats,
                    })

                elif msg_type == 'module_toggle':
                    mod = msg.get('module', '')
                    active = msg.get('active', False)
                    self._active_modules = set(msg.get('modules', []))
                    _log("module", f"{'✅' if active else '⬜'} {mod} → {list(self._active_modules)}")
                    # Sync to all clients
                    await self._ws_broadcast({
                        'type': 'module_sync',
                        'modules': list(self._active_modules),
                    })

                    # Savant toggle: switch dropout in real-time
                    if mod == 'savant' and self.model:
                        self._savant_auto = False  # user override cancels auto
                        self._toggle_savant(active, auto=False)
        except Exception: pass
        finally:
            self.web_clients.discard(websocket)
            # Clean up session
            if hasattr(self, '_sessions'):
                to_remove = [s for s, info in self._sessions.items() if info.get('ws') == websocket]
                for s in to_remove:
                    del self._sessions[s]
                    _log("session", f"-{s[:6]} — {len(self._sessions)} active")
            _log("web", f"-client ({len(self.web_clients)})")

    def _http_handler(self, connection, request):
        if request.headers.get("Upgrade", "").lower() == "websocket": return None
        if request.path in ("/", "/index.html"):
            html = ANIMA_DIR / "web" / "index.html"
            if html.exists():
                body = html.read_bytes()
                return _ws_Response(200, "OK", _ws_Headers([
                    ("Content-Type", "text/html; charset=utf-8"),
                    ("Content-Length", str(len(body))),
                ]), body)
        return _ws_Response(404, "Not Found", _ws_Headers(), b"404")

    async def _run_web(self, port):
        self._web_loop = asyncio.get_running_loop()
        async with _ws_serve(self._ws_handler, "0.0.0.0", port, process_request=self._http_handler):
            _log("web", f"http://localhost:{port}")
            while self.running: await asyncio.sleep(1)

    def _start_web_thread(self, port):
        threading.Thread(target=lambda: asyncio.run(self._run_web(port)),
                         daemon=True, name="anima-web").start()

    # ─── Status dashboard ───

    def print_status(self):
        t = self.mind.prev_tension
        cells = len(self.mitosis.cells) if self.mitosis else 1
        lrn = f"L:{self.learner.total_updates}" if self.learner else "--"
        web_n = len(self.web_clients) if self.mods.get('web') else 0
        active = [k for k, v in self.mods.items() if v]
        print(f"\n  +{'='*40}+")
        print(f"  |  Anima Unified                        |")
        print(f"  |  Cells:{cells} | T={t:.2f} | {lrn:>8}          |")
        print(f"  |  {' | '.join(active):36s}  |")
        print(f"  +{'='*40}+\n")

    # ─── Unified run ───

    def _start_bg_threads(self, port=8765):
        """Start all applicable background threads."""
        threading.Thread(target=self._think_loop, daemon=True).start()
        if self.mods.get('dream'):
            threading.Thread(target=self._dream_loop, daemon=True, name='anima-dream').start()
        if self.mods.get('rust_vad'):
            threading.Thread(target=self._rust_vad_loop, daemon=True).start()
        if self.mods.get('web'):
            self._start_web_thread(port)
        if self.kb_queue is not None:
            threading.Thread(target=self._keyboard_loop, daemon=True).start()

    def run(self, port=8765):
        """Main run loop for all modes."""
        mode = self.args

        # Web-only mode: async main loop
        if mode.web and not mode.all:
            threading.Thread(target=self._think_loop, daemon=True).start()
            if self.mods.get('dream'):
                threading.Thread(target=self._dream_loop, daemon=True, name='anima-dream').start()
            try: asyncio.run(self._run_web(port))
            except KeyboardInterrupt: pass
            return

        # Voice / keyboard / all modes: sync main loop
        self._start_bg_threads(port)
        if self.listener:
            self.listener.start()
            if self.speaker: self.speaker.say("Anima unified, ready.", self.listener)

        last_status = time.time()
        try:
            while self.running:
                text = None
                # Voice input
                if self.listener:
                    text = self.listener.get_speech(timeout=0.3)
                # Keyboard input
                if text is None and self.kb_queue:
                    try: text = self.kb_queue.get_nowait()
                    except queue.Empty: pass

                if text:
                    if self.speaker and self.speaker.is_speaking: self.speaker.stop()
                    answer, tension, curiosity, dir_vals, emo = self.process_input(text)
                    if self.speaker: self.speaker.say(answer, self.listener)
                    broadcast_msg = {
                        'type': 'anima_message', 'text': answer,
                        'tension': tension, 'curiosity': curiosity,
                        'direction': dir_vals,
                        'emotion': emo,
                        'tension_history': self.mind.tension_history[-50:],
                        'proactive': False,
                    }
                    mc = getattr(self, '_last_mitosis_context', '')
                    if mc:
                        broadcast_msg['mitosis_context'] = mc
                    self._ws_broadcast_sync(broadcast_msg)

                if time.time() - last_status > 60:
                    self.print_status()
                    last_status = time.time()

                if not self.listener and not text:
                    time.sleep(0.3)
        except KeyboardInterrupt:
            pass

    # ─── Shutdown ───

    def shutdown(self):
        self.running = False
        if self.listener: self.listener.stop()
        if self.speaker: self.speaker.say("Goodbye.")
        for obj, method in [(self.senses, 'stop'), (self.telepathy, 'stop'),
                            (self.cloud, 'stop_auto_sync'), (self.learner, 'flush_pending')]:
            if obj:
                try: getattr(obj, method)()
                except Exception: pass
        # Memory Store: save FAISS index on shutdown
        if self.memory_rag:
            try: self.memory_rag.save_faiss()
            except Exception: pass
        self._save_state()
        print("\n  Anima Unified stopped.")


# ─── CLI ───

def main():
    p = argparse.ArgumentParser(description="Anima Unified")
    p.add_argument('--web', action='store_true', help='Web mode only')
    p.add_argument('--keyboard', action='store_true', help='Keyboard only (no mic)')
    p.add_argument('--all', action='store_true', help='Voice + keyboard + web')
    p.add_argument('--port', type=int, default=8765, help='WebSocket port')
    p.add_argument('--no-camera', action='store_true', help='Disable camera')
    p.add_argument('--no-vision', action='store_true', help='Disable vision encoder (use basic sensors only)')
    p.add_argument('--no-telepathy', action='store_true', help='Disable telepathy')
    p.add_argument('--no-cloud', action='store_true', help='Disable cloud sync')
    p.add_argument('--no-conscious-lm', action='store_true', help='Disable ConsciousLM (Claude only)')
    p.add_argument('--model', type=str, default=None,
                   help='Model selection: conscious-lm, mistral-7b, llama-8b, or .gguf path')
    p.add_argument('--list-models', action='store_true', help='List available models')
    args = p.parse_args()

    # --list-models: print list and exit
    if args.list_models and 'list_available_models' in globals():
        print("Available models:")
        for name, desc, exists in list_available_models():
            status = "✓" if exists else "✗"
            print(f"  [{status}] {name:20s} {desc}")
        sys.exit(0)

    mode = "all" if args.all else "web" if args.web else "keyboard" if args.keyboard else "voice"
    model_label = args.model or "conscious-lm"
    print(f"{'='*50}\n  Anima Unified  |  Mode: {mode}  |  Model: {model_label}\n{'='*50}")

    anima = AnimaUnified(args)
    for name, active in anima.mods.items():
        print(f"  [{'OK' if active else '--':>2}] {name}")
    print()

    signal.signal(signal.SIGINT, lambda s, f: (anima.shutdown(), sys.exit(0)))
    try:
        anima.run(args.port)
    finally:
        anima.shutdown()


if __name__ == '__main__':
    main()
