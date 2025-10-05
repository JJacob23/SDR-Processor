import asyncio
from receiver.fm_queue_streamer import QueueStreamer
from classifier.queue_classifier import QueueClassifier


async def main():
    streamer = QueueStreamer(freq=100.304e6, gain=25, play_audio=True)
    classifier = QueueClassifier(streamer.get_queue())

    streamer_task = asyncio.create_task(streamer.start())
    classifier_task = asyncio.create_task(classifier.run())

    try:
        await asyncio.gather(streamer_task, classifier_task)
    except KeyboardInterrupt:
        print("\n[Main] KeyboardInterrupt, shutting down...")
        await streamer.stop()
        classifier_task.cancel()
    finally:
        await asyncio.sleep(0.1)
        print("[Main] Cleanup complete.")

if __name__ == "__main__":
    asyncio.run(main())
