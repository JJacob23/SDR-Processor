import asyncio
from receiver.fm_streamer import Streamer
from classifier.classifier import Classifier
from utils.constants import FREQ

async def main():
    streamer = Streamer(freq=FREQ, gain=25, play_audio=True)
    classifier = Classifier()
    streamer_task = asyncio.create_task(streamer.start())
    classifier_connect_task = asyncio.create_task(classifier.connect())
    classifier_run_task = asyncio.create_task(classifier.run())
    try:
        await asyncio.gather(streamer_task, classifier_connect_task, classifier_run_task)
    except KeyboardInterrupt:
        print("\n[Main] KeyboardInterrupt, shutting down...")
        await streamer.stop()
        classifier_task.cancel()
    finally:
        await asyncio.sleep(0.1)
        print("[Main] Cleanup complete.")

if __name__ == "__main__":
    asyncio.run(main())
