from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn
import asyncio
import logging
import os
from typing import List

from database import init_db
import api
from scheduler import scheduler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)
FRONTEND_DIST = os.path.join(PROJECT_ROOT, "frontend", "dist")


# ─── WebSocket 广播管理 ───────────────────────────────────

class ConnectionManager:
    def __init__(self):
        self.connections: List[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.connections.append(ws)

    def disconnect(self, ws: WebSocket):
        if ws in self.connections:
            self.connections.remove(ws)

    async def broadcast(self, message: dict):
        for ws in self.connections[:]:
            try:
                await ws.send_json(message)
            except Exception:
                self.connections.remove(ws)


manager = ConnectionManager()


# ─── App ──────────────────────────────────────────────────

app = FastAPI(title="量化交易Agent系统", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api.router, prefix="/api")


@app.on_event("startup")
async def on_startup():
    init_db()
    scheduler.set_broadcast(manager.broadcast)
    await scheduler.start()


@app.on_event("shutdown")
async def on_shutdown():
    await scheduler.stop()


# WebSocket端点 - 前端通过此连接接收实时推送
@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await manager.connect(ws)
    try:
        while True:
            await ws.receive_text()  # keep alive
    except WebSocketDisconnect:
        manager.disconnect(ws)


@app.get("/health")
async def health():
    from scheduler import is_trading_hours
    return {
        "status": "ok",
        "scheduler_running": scheduler.is_running,
        "market_open": is_trading_hours(),
    }


# 前端静态文件（生产模式）
if os.path.isdir(FRONTEND_DIST):
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
