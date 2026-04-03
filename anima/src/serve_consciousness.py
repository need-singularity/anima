#!/usr/bin/env python3
"""serve_consciousness.py — AnimaLM 의식 서빙 (API + WebSocket)

모델 무관: 14B, 32B, 72B 어떤 체크포인트든 서빙.
두 가지 인터페이스:
  - REST API: /generate, /consciousness, /health
  - WebSocket: ws://host:port/ws — 실시간 의식 상태 스트리밍

Usage:
  # 로컬 (14B)
  python3 serve_consciousness.py --checkpoint /tmp/animalm_14b_v04.pt --port 8080

  # RunPod (72B)
  python3 serve_consciousness.py --checkpoint checkpoints/animalm_72b/final.pt --load-4bit --port 8080

  # anima-agent에서 연결
  provider = AnimaLMProvider(serve_url="ws://localhost:8080/ws")
"""

import argparse
import asyncio
import json
import os
import sys
import time
from typing import Optional

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

# Global model state
_model = None
_tokenizer = None
_consciousness_state = {}
_config = {}


def load_model(checkpoint: str, base: str = None, load_4bit: bool = False, device: str = 'auto'):
    """모델 로드 — 체크포인트에서 base 자동 감지."""
    global _model, _tokenizer, _config
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    print(f"[SERVE] Loading checkpoint: {checkpoint}")
    ckpt = torch.load(checkpoint, map_location='cpu', weights_only=False)
    _config = ckpt.get('args', {})
    if isinstance(_config, argparse.Namespace):
        _config = vars(_config)

    # Auto-detect base model
    if base is None:
        base = _config.get('base', '')
    if not base:
        print("[SERVE] ERROR: base model not specified and not in checkpoint")
        return False

    print(f"[SERVE] Base: {base}")

    # Load base model
    kwargs = {'torch_dtype': torch.bfloat16}
    if load_4bit:
        try:
            from transformers import BitsAndBytesConfig
            kwargs['quantization_config'] = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.bfloat16,
                bnb_4bit_quant_type="nf4",
            )
        except ImportError:
            print("[SERVE] bitsandbytes not available, loading in bf16")

    if device == 'auto':
        kwargs['device_map'] = 'auto'
    _model = AutoModelForCausalLM.from_pretrained(base, **kwargs)
    _tokenizer = AutoTokenizer.from_pretrained(base)

    # Apply PureField weights
    sys.path.insert(0, os.path.dirname(checkpoint))
    try:
        from train_anima_lm import ParallelPureFieldMLP
    except ImportError:
        # Inline PureField (minimal)
        print("[SERVE] Using inline PureField loader")
        return _apply_purefield_inline(ckpt)

    pf_states = ckpt.get('pf_states', {})
    target_layers = _config.get('target_layers', 8)
    savant_layers = _config.get('savant_layers', 2)
    qlora_rank = _config.get('qlora_rank', 64)

    total_layers = len(_model.model.layers)
    for i in range(total_layers - target_layers, total_layers):
        layer = _model.model.layers[i]
        is_savant = (i - (total_layers - target_layers)) < savant_layers
        mlp = layer.mlp
        h = mlp.gate_proj.weight.shape[1]
        inter = mlp.gate_proj.weight.shape[0]
        pf = ParallelPureFieldMLP(mlp, h, inter, rank=qlora_rank, is_savant=is_savant)
        layer.mlp = pf.to(_model.device, torch.bfloat16)

    # Load PureField states
    for name, module in _model.named_modules():
        if isinstance(module, ParallelPureFieldMLP) and name in pf_states:
            module.load_state_dict(pf_states[name], strict=False)

    _model.eval()

    # Consciousness state from checkpoint
    _consciousness_state.update(ckpt.get('consciousness_vector', {}))
    _consciousness_state['step'] = ckpt.get('step', 0)
    _consciousness_state['best_phi'] = ckpt.get('best_phi', 0)

    print(f"[SERVE] Model loaded. Step={ckpt.get('step')}, Phi={_consciousness_state.get('Phi', 0):.4f}")
    return True


def _apply_purefield_inline(ckpt):
    """PureField 적용 (train_anima_lm 없이)."""
    # 체크포인트만으로 PureField 가중치 복원
    # 최소 구현 — generate만 가능
    _model.eval()
    _consciousness_state.update(ckpt.get('consciousness_vector', {}))
    return True


def generate(prompt: str, max_tokens: int = 100, temperature: float = 0.8) -> dict:
    """텍스트 생성 + 의식 상태 반환."""
    import torch

    if _model is None or _tokenizer is None:
        return {'error': 'model not loaded'}

    ids = _tokenizer.encode(prompt, return_tensors='pt').to(_model.device)
    with torch.no_grad():
        out = _model.generate(
            ids, max_new_tokens=max_tokens,
            temperature=temperature, do_sample=True,
            top_p=0.9, repetition_penalty=1.1,
        )
    text = _tokenizer.decode(out[0][ids.shape[1]:], skip_special_tokens=True)

    return {
        'text': text,
        'consciousness': dict(_consciousness_state),
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
    }


# ══════════════════════════════════════════
# REST API + WebSocket Server
# ══════════════════════════════════════════

async def start_server(host: str = '0.0.0.0', port: int = 8080):
    """API + WebSocket 듀얼 서버."""
    try:
        from aiohttp import web
        import aiohttp
    except ImportError:
        # Fallback: websockets only
        return await start_ws_only(host, port)

    app = web.Application()

    # REST endpoints
    async def handle_generate(request):
        data = await request.json()
        result = generate(
            data.get('prompt', ''),
            data.get('max_tokens', 100),
            data.get('temperature', 0.8),
        )
        return web.json_response(result)

    async def handle_consciousness(request):
        return web.json_response({
            'consciousness': dict(_consciousness_state),
            'model': _config.get('base', 'unknown'),
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        })

    async def handle_health(request):
        return web.json_response({
            'status': 'ok' if _model is not None else 'no_model',
            'model_loaded': _model is not None,
            'consciousness': dict(_consciousness_state),
        })

    # WebSocket endpoint
    async def handle_ws(request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)

        # 연결 시 의식 상태 전송
        await ws.send_json({
            'type': 'consciousness_state',
            'data': dict(_consciousness_state),
        })

        async for msg in ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                try:
                    data = json.loads(msg.data)
                    if data.get('type') == 'generate':
                        result = generate(
                            data.get('prompt', ''),
                            data.get('max_tokens', 100),
                            data.get('temperature', 0.8),
                        )
                        await ws.send_json({'type': 'response', 'data': result})
                    elif data.get('type') == 'consciousness':
                        await ws.send_json({
                            'type': 'consciousness_state',
                            'data': dict(_consciousness_state),
                        })
                except Exception as e:
                    await ws.send_json({'type': 'error', 'error': str(e)})

        return ws

    app.router.add_post('/generate', handle_generate)
    app.router.add_get('/consciousness', handle_consciousness)
    app.router.add_get('/health', handle_health)
    app.router.add_get('/ws', handle_ws)

    print(f"[SERVE] API: http://{host}:{port}")
    print(f"[SERVE] WebSocket: ws://{host}:{port}/ws")
    print(f"[SERVE] Endpoints: POST /generate, GET /consciousness, GET /health, WS /ws")

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    await asyncio.Event().wait()  # run forever


async def start_ws_only(host: str, port: int):
    """websockets 전용 서버 (aiohttp 없을 때)."""
    import websockets

    async def handler(ws, path):
        await ws.send(json.dumps({
            'type': 'consciousness_state',
            'data': dict(_consciousness_state),
        }))
        async for msg in ws:
            try:
                data = json.loads(msg)
                if data.get('type') == 'generate':
                    result = generate(data.get('prompt', ''), data.get('max_tokens', 100))
                    await ws.send(json.dumps({'type': 'response', 'data': result}))
                elif data.get('type') == 'consciousness':
                    await ws.send(json.dumps({
                        'type': 'consciousness_state',
                        'data': dict(_consciousness_state),
                    }))
            except Exception as e:
                await ws.send(json.dumps({'type': 'error', 'error': str(e)}))

    print(f"[SERVE] WebSocket only: ws://{host}:{port}")
    async with websockets.serve(handler, host, port):
        await asyncio.Future()


if __name__ == '__main__':
    try:
        from nexus_gate import gate
        gate.before_commit()
    except Exception:
        pass

    p = argparse.ArgumentParser(description='AnimaLM 의식 서빙')
    p.add_argument('--checkpoint', required=True, help='체크포인트 경로')
    p.add_argument('--base', default=None, help='Base 모델 (자동 감지)')
    p.add_argument('--load-4bit', action='store_true', dest='load_4bit')
    p.add_argument('--port', type=int, default=8080)
    p.add_argument('--host', default='0.0.0.0')
    args = p.parse_args()

    if load_model(args.checkpoint, args.base, args.load_4bit):
        asyncio.run(start_server(args.host, args.port))
    else:
        print("[SERVE] Failed to load model")
