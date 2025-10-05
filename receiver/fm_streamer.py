from __future__ import annotations

import asyncio
from typing import Optional
import numpy as np
import redis.asyncio as aioredis # type: ignore
from gnuradio import blocks # type: ignore
from utils.constants import BATCH_MS, RAW_SAMPLE_RATE, CHANNEL_AUDIO
from utils.config import REDIS_URL
from .fm_receiver import FMRx

class Streamer:
    """
    Streams 100ms batches of demodulated FM audio samples into an redis broadcast.
    """

    def __init__(
                self,
                freq: float,
                gain: float,
                play_audio: bool = False,
                redis_url: str = REDIS_URL,
                channel: str = CHANNEL_AUDIO,
    ) -> None:
        self.freq = freq
        self.gain = gain
        self.play_audio = play_audio
        self.redis_url = redis_url
        self.channel = channel


        self.rx: Optional[FMRx] = None # type: ignore
        self.running: bool = False # type: ignore
        self.redis: Optional[aioredis.Redis] = None # type: ignore

    async def start(self) -> None:
        """Start the FM receiver and publish audio batches."""
        self.running = True
        self.redis = aioredis.from_url(self.redis_url, decode_responses=False)
        self.rx = FMRx(freq=self.freq, gain=self.gain, outfile=None, play_audio=self.play_audio)


        audio_source = blocks.vector_sink_f()
        self.rx.connect(self.rx.deemph, audio_source)
        self.rx.start()
        print(f"[Streamer] Streaming audio @ {RAW_SAMPLE_RATE} Hz, {BATCH_MS} ms batches")


        batch_size = int(RAW_SAMPLE_RATE * BATCH_MS / 1000)
        buffer = np.zeros(0, dtype=np.float32)


        try:
            while self.running:
                samples = np.asarray(audio_source.data(), dtype=np.float32)
                audio_source.reset()

                if samples.size == 0:
                    await asyncio.sleep(0.01)
                    continue

                buffer = np.concatenate((buffer, samples))

                while buffer.size >= batch_size:
                    batch, buffer = buffer[:batch_size], buffer[batch_size:]
                    assert self.redis is not None
                    await self.redis.publish(self.channel, batch.tobytes())
        except asyncio.CancelledError:
            pass
        finally:
            if self.rx is not None:
                self.rx.stop(); self.rx.wait()
            if self.redis is not None:
                await self.redis.close()
            print("[Streamer] Streamer stopped")

    async def stop(self) -> None:
        """Signal the streaming loop to stop."""
        self.running = False
        await asyncio.sleep(0.05)