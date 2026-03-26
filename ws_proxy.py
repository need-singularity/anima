"""WebSocket HTTP proxy — bridges Cloudflare Tunnel to Anima WebSocket server.

8888 (HTTP+WS) → 8765 (Anima WebSocket server)

Cloudflare Tunnel connects to 8888, this proxy forwards to 8765.
Handles both HTTP (static files) and WebSocket (chat) connections.
"""
from aiohttp import web, WSMsgType
import aiohttp
import asyncio

WS_TARGET = 'ws://localhost:8765/ws'
HTTP_TARGET = 'http://localhost:8765'

async def handle_ws(request):
    ws_response = web.WebSocketResponse()
    await ws_response.prepare(request)
    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(WS_TARGET) as ws_client:
            async def forward_to_client():
                async for msg in ws_client:
                    if msg.type == WSMsgType.TEXT:
                        await ws_response.send_str(msg.data)
                    elif msg.type in (WSMsgType.CLOSED, WSMsgType.ERROR):
                        break
            async def forward_to_server():
                async for msg in ws_response:
                    if msg.type == WSMsgType.TEXT:
                        await ws_client.send_str(msg.data)
                    elif msg.type in (WSMsgType.CLOSED, WSMsgType.ERROR):
                        break
            await asyncio.gather(forward_to_client(), forward_to_server())
    return ws_response

async def handle_http(request):
    async with aiohttp.ClientSession() as session:
        async with session.get(HTTP_TARGET + request.path_qs) as resp:
            body = await resp.read()
            return web.Response(body=body, content_type=resp.content_type, status=resp.status)

app = web.Application()
app.router.add_get('/ws', handle_ws)
app.router.add_get('/{path:.*}', handle_http)
app.router.add_get('/', handle_http)

if __name__ == '__main__':
    web.run_app(app, host='0.0.0.0', port=8888)
