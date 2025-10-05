import redis.asyncio as aioredis
import asyncio
import numpy as np
from gnuradio import blocks
import sys, os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))) #Run as module later, but this lets me test the file directly for now.
from utils.constants import RAW_SAMPLE_RATE, BATCH_MS

from receiver.fm_receiver import FMRx

class Streamer:
    """
    Streams 100ms batches of demodulated FM audio samples into an redis broadcast.
    """

    def __init__(self, freq, gain, play_audio=False, redis_url="redis://localhost:6379", channel="audio_stream"):
        self.freq = freq
        self.gain = gain
        self.play_audio = play_audio
        self.rx = None
        self.running = False
        self.redis_url = redis_url
        self.channel = channel
        self.redis = None


    async def start(self):
        """Start the FM receiver and begin pushing audio batches."""
        self.running = True
        self.redis = aioredis.from_url(self.redis_url, decode_responses=False)
        self.rx = FMRx(freq=self.freq,
                        gain=self.gain,
                        outfile=None,
                        play_audio=self.play_audio)
        audio_source = blocks.vector_sink_f()
        self.rx.connect(self.rx.deemph, audio_source)
        self.rx.start()
        print(f"[Streamer] Streaming audio @ {RAW_SAMPLE_RATE} Hz, {BATCH_MS}ms batches")

        batch_size = int(RAW_SAMPLE_RATE * BATCH_MS / 1000)
        buffer = np.zeros(0, dtype=np.float32)

        try:
            while self.running:
                samples = np.array(audio_source.data(), dtype=np.float32)
                audio_source.reset()

                if len(samples) == 0:
                    await asyncio.sleep(0.01)
                    continue

                buffer = np.concatenate((buffer, samples))

                while len(buffer) >= batch_size:
                    batch, buffer = buffer[:batch_size], buffer[batch_size:]
                    await self.redis.publish(self.channel,batch.tobytes())
                    

        except asyncio.CancelledError:
            pass
        finally:
            self.rx.stop()
            self.rx.wait()
            if self.redis:
                await self.redis.close()
            print("[Streamer] Streamer stopped")

    async def stop(self):
        self.running = False
        await asyncio.sleep(0.1)
