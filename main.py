from __future__ import annotations
import asyncio
from classifier.audio_classifier import Classifier
from receiver.fm_streamer import Streamer
from utils.config import DEFAULT_FREQ, DEFAULT_GAIN

async def main() -> None:
    streamer = Streamer(freq=DEFAULT_FREQ, gain=float(DEFAULT_GAIN), play_audio=True)
    classifier = Classifier()

    streamer_task = asyncio.create_task(streamer.start())
    classifier_task = asyncio.create_task(classifier.run())

    try:
        await asyncio.gather(streamer_task,  classifier_task)
    except KeyboardInterrupt:
        print("\n[Main] KeyboardInterrupt, shutting down...")
        await streamer.stop()
        classifier_task.cancel()
    finally:
        await asyncio.sleep(0.1)
        print("[Main] Cleanup complete.")

if __name__ == "__main__":
    asyncio.run(main())
