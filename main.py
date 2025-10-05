import asyncio
from receiver.fm_queue_streamer import QueueStreamer
from classifier.queue_classifier import QueueClassifier
from utils.constants import FREQ

async def main():
    streamer = QueueStreamer(freq=FREQ, gain=25, play_audio=True)
    classifier = QueueClassifier()
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
