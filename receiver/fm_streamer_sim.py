from __future__ import annotations
import asyncio
from typing import Optional, Dict
import numpy as np
import soundfile as sf
import redis.asyncio as aioredis  # type: ignore

from utils.constants import RAW_SAMPLE_RATE, BATCH_MS, CHANNEL_AUDIO

class StreamerSim:
    """
    Simulated FM audio streamer.
    Publishes 100 ms float32 PCM chunks to Redis CHANNEL_AUDIO, same as FMRx Streamer.
    Allows 'tune()' to swap between two preloaded WAVs (looping).
    """
    def __init__(
        self,
        station_files: Dict[float, str],
        init_freq: float,
        redis_url: str,
        channel: str = CHANNEL_AUDIO,
    ) -> None:
        """
        station_files: mapping from RF freq (Hz) -> path to WAV (any samplerate; will resample if needed)
        init_freq:     starting "tuned" frequency (Hz)
        redis_url:     redis://host:port
        """
        self.station_files = station_files
        self.freq = init_freq
        self.redis_url = redis_url
        self.channel = channel

        self.running = False
        self.redis: Optional[aioredis.Redis] = None

        # audio state
        self._buffers: Dict[float, np.ndarray] = {}
        self._pos_samples: int = 0  # cursor into current station buffer (wraps)
        self._batch_size = int(RAW_SAMPLE_RATE * BATCH_MS / 1000)

    async def _load_wav(self, path: str) -> np.ndarray:
        data, sr = sf.read(path, dtype="float32", always_2d=False)
        # mono
        if data.ndim == 2:
            data = data.mean(axis=1).astype(np.float32)
        # resample if needed
        if sr != RAW_SAMPLE_RATE:
            # polyphase resample using numpy (simple) or librosa/scipy if you prefer.
            # Here we do a quick/balanced approach via soundfile + numpy repeat/trim when close.
            # For accuracy, import resampy/librosa. To avoid extra deps, we’ll use a simple fallback:
            ratio = RAW_SAMPLE_RATE / sr
            new_len = int(round(len(data) * ratio))
            x_old = np.linspace(0.0, 1.0, num=len(data), endpoint=False, dtype=np.float32)
            x_new = np.linspace(0.0, 1.0, num=new_len, endpoint=False, dtype=np.float32)
            data = np.interp(x_new, x_old, data).astype(np.float32)
        return data

    async def start(self) -> None:
        """Begin publishing simulated audio; loop the current station WAV forever."""
        self.running = True
        self.redis = aioredis.from_url(self.redis_url, decode_responses=False)

        # Preload all station files (resampled to RAW_SAMPLE_RATE)
        for f_hz, path in self.station_files.items():
            self._buffers[f_hz] = await self._load_wav(path)

        self._pos_samples = 0
        print(f"[SimStreamer] Ready. Stations: {list(self.station_files.keys())}, start @ {self.freq/1e6:.3f} MHz")

        try:
            while self.running:
                buf = self._buffers[self.freq]
                end = self._pos_samples + self._batch_size

                if end <= len(buf):
                    batch = buf[self._pos_samples:end]
                    self._pos_samples = end
                else:
                    # wrap
                    first = buf[self._pos_samples:]
                    remain = end - len(buf)
                    second = buf[:remain]
                    batch = np.concatenate([first, second])
                    self._pos_samples = remain

                # publish
                assert self.redis is not None
                await self.redis.publish(self.channel, batch.astype(np.float32).tobytes())

                # pace roughly to realtime (100ms batches)
                await asyncio.sleep(BATCH_MS / 1000)
        except asyncio.CancelledError:
            pass
        finally:
            if self.redis is not None:
                await self.redis.close()
            print("[SimStreamer] Stopped.")

    async def tune(self, new_freq: float) -> None:
        """Swap to another station buffer and reset the cursor (or continue where you left off)."""
        if new_freq not in self._buffers:
            print(f"[SimStreamer] Unknown freq {new_freq}, staying on {self.freq/1e6:.3f} MHz")
            return
        self.freq = new_freq
        self._pos_samples = 0  # start station from the beginning (optional)
        print(f"[SimStreamer] Tuning to {new_freq/1e6:.3f} MHz")

    async def stop(self) -> None:
        self.running = False
        await asyncio.sleep(0.05)
