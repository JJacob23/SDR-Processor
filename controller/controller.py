import asyncio
import redis.asyncio as aioredis
import json
import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))) #Run as module later, but this lets me test the file directly for now.
from receiver.fm_queue_streamer import QueueStreamer
from classifier.queue_classifier import QueueClassifier
from utils.constants import FREQ,GAIN,BATCH_MS,INVERSE_LABELS,REDIS_URL

app = FastAPI()
app.add_middleware(#Stops browser security error
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

audio_subscribers = set()
state_subscribers = set()

async def broadcast_audio(data: bytes):
    """Send 100ms audio PCM chunks to all connected audio websocket clients."""
    if not audio_subscribers:
        return
    stale = []
    for ws in audio_subscribers:
        try:
            await ws.send_bytes(data)
        except WebSocketDisconnect:
            stale.append(ws)
    for ws in stale:
        audio_subscribers.remove(ws)

async def broadcast_state(payload: dict):
    """Send classifier updates as JSON to all connected classifier websocket clients."""
    if not state_subscribers:
        return
    msg=json.dumps(payload)
    print(payload)
    stale = []
    for ws in state_subscribers:
        try:
            await ws.send_text(msg)
        except WebSocketDisconnect:
            stale.append(ws)
    for ws in stale:
        state_subscribers.remove(ws)


async def redis_audio_listener():
    """Subscribe to the Redis audio channel and forward to WebSocket clients."""
    redis = aioredis.from_url(REDIS_URL)
    pubsub = redis.pubsub()
    await pubsub.subscribe("audio_stream")
    print(f"[Controller] Listening on Redis channel: audio_stream")

    try:
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue
            await broadcast_audio(message["data"])
    except asyncio.CancelledError:
        print("[Controller] Audio listener stopped.")
    finally:
        await pubsub.unsubscribe("audio_stream")
        await redis.close()

async def redis_state_listener():
    """Subscribe to the Redis state channel and forward to WebSocket clients."""
    redis = aioredis.from_url(REDIS_URL)
    pubsub = redis.pubsub()
    await pubsub.subscribe("state_stream")
    print(f"[Controller] Listening on Redis channel: state_stream")

    try:
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue
            payload = json.loads(message["data"])
            await broadcast_state(payload)
    except asyncio.CancelledError:
        print("[Controller] State listener stopped.")
    finally:
        await pubsub.unsubscribe("state_stream")
        await redis.close()

@app.websocket("/ws/audio")
async def audio_ws(ws: WebSocket):
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
async def state_ws(ws: WebSocket):
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
