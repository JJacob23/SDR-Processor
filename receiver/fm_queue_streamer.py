import asyncio
import numpy as np
from gnuradio import gr, blocks
from fm_receiver import FMRx
import sys, os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))) #Run as module later, but this lets me test the file directly for now.
from utils.constants import RAW_SAMPLE_RATE, BATCH_MS


class QueueStreamer:
    """
    Streams 100ms batches of demodulated FM audio samples into an async queue.
    """

    def __init__(self, freq, gain, play_audio=False):
        self.freq = freq
        self.gain = gain
        self.play_audio = play_audio
        self.queue = asyncio.Queue(maxsize=50)
        self.rx = None
        self.running = False

    async def start(self):
        """Start the FM receiver and begin pushing audio batches."""
        self.running = True
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
                    try:
                        await self.queue.put(batch)
                    except asyncio.QueueFull:
                        print("[Streamer] Queue full — dropping batch")

        except asyncio.CancelledError:
            pass
        finally:
            self.rx.stop()
            self.rx.wait()
            print("[Streamer] Streamer stopped")

    async def stop(self):
        self.running = False
        await self.queue.put(None) # Let consumers know its stopping
        await asyncio.sleep(0.1)

    def get_queue(self):
        """Return the asyncio queue for consumers."""
        return self.queue
