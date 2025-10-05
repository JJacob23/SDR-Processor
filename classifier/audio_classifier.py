from __future__ import annotations

import asyncio
import json
from typing import Optional, Tuple
import numpy as np
import redis.asyncio as aioredis
import torch
from utils.constants import (
    CHUNK_DURATION_S,
    HOP_SIZE,
    INVERSE_LABELS,
    N_MELS,
    SAMPLE_RATE,
    WINDOW_SIZE,
    CHANNEL_AUDIO,
    CHANNEL_CLASSIFIER,
)
from utils.config import REDIS_URL
from utils.audio_utils import (
    ensure_tensor,
    mono,
    normalize_duration,
    waveform_to_mel_spectrogram,
)
from .model import AudioCNN

class Classifier:
    """
    Pulls small waveform batches from an redis broadcast, runs classification
    over 10s windows, and publishes classifiation.
    """
    def __init__(
        self,
        redis_url: str = REDIS_URL,
        audio_channel: str = CHANNEL_AUDIO,
        state_channel: str = CHANNEL_CLASSIFIER,
        device: Optional[torch.device] = None,
    ) -> None:
        self.redis_url = redis_url
        self.audio_channel = audio_channel
        self.state_channel = state_channel
        self.redis: Optional[aioredis.Redis] = None
        self.pubsub: Optional[aioredis.client.PubSub] = None
        self.buffer = np.zeros(0, dtype=np.float32)
        self.chunk_samples = int(SAMPLE_RATE * CHUNK_DURATION_S)
        self.device = device or torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = AudioCNN()
        self.model.to(self.device)
        self.model.eval()
        print("[Classifier] Model ready…")

    async def connect(self) -> None:
        """Connect to Redis and subscribe to the audio channel."""
        self.redis = aioredis.from_url(self.redis_url)
        self.pubsub = self.redis.pubsub()
        await self.pubsub.subscribe(self.audio_channel)
        print(f"[Classifier] Subscribed to channel '{self.audio_channel}'")

    async def run(self) -> None:
        """Consume float32 batches and classify on full 10 s buffers."""
        await self.connect()
        assert self.pubsub is not None
        try:
            async for message in self.pubsub.listen():
                if message["type"] != "message":
                    continue

                batch = np.frombuffer(message["data"], dtype=np.float32)
                self.buffer = np.concatenate((self.buffer, batch))

                # Keep only the most recent 10 s
                if self.buffer.size > self.chunk_samples:
                    self.buffer = self.buffer[-self.chunk_samples :]

                if self.buffer.size == self.chunk_samples:
                    pred, probs = self.classify(self.buffer)
                    label = INVERSE_LABELS[pred]
                    print(f"[Classifier] {label} (p={probs})")
                    payload = json.dumps({"label": label, "probs": probs.tolist()})
                    assert self.redis is not None
                    await self.redis.publish(self.state_channel, payload)
                    self.buffer = np.zeros(0, dtype=np.float32)
        except asyncio.CancelledError:
            print("[Classifier] Stopping classifier…")
        finally:
            if self.pubsub is not None:
                await self.pubsub.unsubscribe(self.audio_channel)
            if self.redis is not None:
                await self.redis.close()


    def classify(self, waveform):
        """
        Run model inference on a 1D numpy waveform.
        """
        waveform = ensure_tensor(waveform)
        waveform = mono(waveform)
        waveform = normalize_duration(waveform, SAMPLE_RATE, CHUNK_DURATION_S)
        mel_spectrogram = waveform_to_mel_spectrogram(waveform, SAMPLE_RATE, N_MELS, WINDOW_SIZE, HOP_SIZE)
        mel_spectrogram = mel_spectrogram.unsqueeze(0).to(self.device)
        with torch.no_grad():
            logits = self.model(mel_spectrogram)
            probs = torch.softmax(logits, dim=1).squeeze().cpu().numpy()
            pred = int(np.argmax(probs))
        return pred, probs
