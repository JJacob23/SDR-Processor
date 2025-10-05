import asyncio
import json
import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))) #Run as module later, but this lets me test the file directly for now.
from receiver.fm_queue_streamer import QueueStreamer
from classifier.queue_classifier import QueueClassifier
from utils.constants import FREQ,GAIN,BATCH_MS,INVERSE_LABELS

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

async def broadcast_audio(data: np.ndarray):
    """Send 100ms audio PCM chunks to all connected audio websocket clients."""
    if not audio_subscribers:
        return
    message = data.tobytes()
    stale = []
    for ws in audio_subscribers:
        try:
            await ws.send_bytes(message)
        except WebSocketDisconnect:
            stale.append(ws)
    for ws in stale:
        audio_subscribers.remove(ws)

async def broadcast_state(label: str, probs: np.ndarray):
    """Send classifier updates as JSON to all connected classifier websocket clients."""
    if not state_subscribers:
        return
    payload = json.dumps({"label": label, "probs": probs.tolist()})
    stale = []
    for ws in state_subscribers:
        try:
            await ws.send_text(payload)
        except WebSocketDisconnect:
            stale.append(ws)
    for ws in stale:
        state_subscribers.remove(ws)


async def streamer_task(streamer: QueueStreamer):
    """Continuously pull audio from FMRx and push to queue + websocket clients."""
    queue = streamer.get_queue()
    while True:
        samples = await queue.get()
        if samples is None:
            break
        await broadcast_audio(samples)
        await asyncio.sleep(0)  # cooperative yield


async def classifier_task(classifier: QueueClassifier):
    """Consume from queue, classify, broadcast."""
    while True:
        samples = await classifier.queue.get()
        if samples is None:
            break

        classifier.buffer = np.concatenate((classifier.buffer, samples))
        if len(classifier.buffer) > classifier.chunk_samples:
            classifier.buffer = classifier.buffer[-classifier.chunk_samples:]

        if len(classifier.buffer) == classifier.chunk_samples:
            pred, probs = classifier.classify(classifier.buffer)
            label = INVERSE_LABELS[pred]
            await broadcast_state(label, probs)
            classifier.buffer = np.zeros(0, dtype=np.float32)
        await asyncio.sleep(0.05)


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
    """
    Launch SDR streamer and classifier loops.
    Currently, this is gonna be laggy because they are both sipping from
    the same queue. I'll fix this once I move to a real broker.
    """
    print("[Server] Starting streamer/classifier...")
    streamer = QueueStreamer(freq=FREQ, gain=GAIN, play_audio=True)
    classifier = QueueClassifier(streamer.get_queue())

    asyncio.create_task(streamer.start())
    asyncio.create_task(streamer_task(streamer))
    asyncio.create_task(classifier_task(classifier))


