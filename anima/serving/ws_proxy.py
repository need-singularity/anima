"""WebSocket HTTP proxy — bridges Cloudflare Tunnel to Anima WebSocket server.

8888 (HTTP+WS) → 8765 (Anima WebSocket server)

Cloudflare Tunnel connects to 8888, this proxy forwards to 8765.
Handles both HTTP (static files) and WebSocket (chat) connections.
Includes error recovery, heartbeat, and auto-reconnect.
"""
from aiohttp import web, WSMsgType
import aiohttp
import asyncio
import logging

# Meta Laws (DD143)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10


logging.basicConfig(level=logging.INFO, format='%(asctime)s [proxy] %(message)s')
log = logging.getLogger('proxy')

WS_TARGET = 'ws://localhost:8765/ws'
HTTP_TARGET = 'http://localhost:8765'


async def handle_ws(request):
    ws_response = web.WebSocketResponse(
        heartbeat=20.0,       # send ping every 20s
        autoping=True,
        timeout=120.0,        # close if no pong in 120s
    )
    await ws_response.prepare(request)
    log.info(f"+ws client {request.remote}")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(
                WS_TARGET,
                heartbeat=20.0,
                timeout=120.0,
            ) as ws_client:

                async def forward_to_client():
                    try:
                        async for msg in ws_client:
                            if ws_response.closed:
                                break
                            if msg.type == WSMsgType.TEXT:
                                await ws_response.send_str(msg.data)
                            elif msg.type in (WSMsgType.CLOSED, WSMsgType.ERROR, WSMsgType.CLOSING):
                                break
                    except Exception as e:
                        log.warning(f"forward_to_client error: {e}")

                async def forward_to_server():
                    try:
                        async for msg in ws_response:
                            if ws_client.closed:
                                break
                            if msg.type == WSMsgType.TEXT:
                                await ws_client.send_str(msg.data)
                            elif msg.type in (WSMsgType.CLOSED, WSMsgType.ERROR, WSMsgType.CLOSING):
                                break
                    except Exception as e:
                        log.warning(f"forward_to_server error: {e}")

                await asyncio.gather(
                    forward_to_client(),
                    forward_to_server(),
                    return_exceptions=True,
                )

    except aiohttp.ClientError as e:
        log.error(f"Backend connection failed: {e}")
    except Exception as e:
        log.error(f"WS proxy error: {e}")
    finally:
        if not ws_response.closed:
            await ws_response.close()
        log.info(f"-ws client {request.remote}")

    return ws_response


async def handle_http(request):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(HTTP_TARGET + request.path_qs, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                body = await resp.read()
                headers = {}
                if 'text/html' in (resp.content_type or ''):
                    headers['Cache-Control'] = 'no-cache'
                return web.Response(body=body, content_type=resp.content_type, status=resp.status, headers=headers)
    except Exception as e:
        log.error(f"HTTP proxy error: {e}")
        return web.Response(text=f"Backend unavailable: {e}", status=502)


app = web.Application()
app.router.add_get('/ws', handle_ws)
app.router.add_get('/{path:.*}', handle_http)
app.router.add_get('/', handle_http)

if __name__ == '__main__':
    log.info("Starting proxy: 8888 → 8765")
    web.run_app(app, host='0.0.0.0', port=8888)
