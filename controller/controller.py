from __future__ import annotations

import asyncio
import json
from typing import Any, Set

import numpy as np
import redis.asyncio as aioredis
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware


from utils.config import REDIS_URL
from utils.constants import CHANNEL_AUDIO, CHANNEL_STATE

app = FastAPI()
app.add_middleware(#Stops browser security error
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

audio_subscribers: Set[WebSocket] = set()
state_subscribers: Set[WebSocket] = set()

async def broadcast_audio(data: bytes) -> None:
    """Send 100ms audio PCM chunks to all connected audio websocket clients."""
    if not audio_subscribers:
        return
    stale: list[WebSocket] = []
    for ws in audio_subscribers:
        try:
            await ws.send_bytes(data)
        except WebSocketDisconnect:
            stale.append(ws)
    for ws in stale:
        audio_subscribers.discard(ws)

async def broadcast_state(payload: dict[str, Any]) -> None:
    """Send classifier updates as JSON to all connected classifier websocket clients."""
    if not state_subscribers:
        return
    msg=json.dumps(payload)
    print(payload)
    stale: list[WebSocket] = []
    for ws in state_subscribers:
        try:
            await ws.send_text(msg)
        except WebSocketDisconnect:
            stale.append(ws)
    for ws in stale:
        state_subscribers.discard(ws)


async def redis_audio_listener() -> None:
    """Subscribe to the Redis audio channel and forward to WebSocket clients."""
    redis = aioredis.from_url(REDIS_URL)
    pubsub = redis.pubsub()
    await pubsub.subscribe(CHANNEL_AUDIO)
    print(f"[Controller] Listening on Redis channel: {CHANNEL_AUDIO}")

    try:
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue
            await broadcast_audio(message["data"])
    except asyncio.CancelledError:
        print("[Controller] Audio listener stopped.")
    finally:
        await pubsub.unsubscribe(CHANNEL_AUDIO)
        await redis.close()

async def redis_state_listener() -> None:
    """Subscribe to the Redis state channel and forward to WebSocket clients."""
    redis = aioredis.from_url(REDIS_URL)
    pubsub = redis.pubsub()
    await pubsub.subscribe(CHANNEL_STATE)
    print(f"[Controller] Listening on Redis channel: {CHANNEL_STATE}")
    try:
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue
            payload = json.loads(message["data"])
            await broadcast_state(payload)
    except asyncio.CancelledError:
        print("[Controller] State listener stopped.")
    finally:
        await pubsub.unsubscribe(CHANNEL_STATE)
        await redis.close()

@app.websocket("/ws/audio")
async def audio_ws(ws: WebSocket) -> None:
    await ws.accept()
    audio_subscribers.add(ws)
    print("[WebSocket] Audio client connected")
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        print("[WebSocket] Audio client disconnected")
        audio_subscribers.remove(ws)


@app.websocket("/ws/state")
async def state_ws(ws: WebSocket) -> None:
    await ws.accept()
    state_subscribers.add(ws)
    print("[WebSocket] State client connected")
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        print("[WebSocket] State client disconnected")
        state_subscribers.remove(ws)


@app.on_event("startup")
async def startup_event():
    print("[Controller] Starting streamer/classifier listeners...")
    app.audio_task = asyncio.create_task(redis_audio_listener())
    app.state_task = asyncio.create_task(redis_state_listener())

@app.on_event("shutdown")
async def shutdown_event():
    print("[Controller] Shutting down...")
    app.audio_task.cancel()
    app.state_task.cancel()
    await asyncio.sleep(0.1)
    print("[Controller] Shutdown complete...")
