from __future__ import annotations
import asyncio
import argparse
import redis.asyncio as aioredis
import json
from controller.state_machine import StateMachine
from classifier.cnn_classifier import Classifier
from receiver.fm_streamer import Streamer
from utils.config import DEFAULT_FREQ, DEFAULT_FREQ2, DEFAULT_GAIN, REDIS_URL
from utils.constants import CHANNEL_STATE

async def monitor_state(streamer: Streamer) -> None:
    """Subscribe to state machine channel and retune SDR when station changes."""
    redis = aioredis.from_url(REDIS_URL)
    pubsub = redis.pubsub()
    await pubsub.subscribe(CHANNEL_STATE)
    print(f"[Main] Listening for FSM state updates on '{CHANNEL_STATE}'")

    try:
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue
            data = json.loads(message["data"].decode("utf-8"))
            new_freq = data.get("station")
            state = data.get("state")

            #Avoid floating point precision errors
            if new_freq and abs(streamer.freq - new_freq) > 1.0:
                await streamer.tune(new_freq)
                print(f"[Main] FSM → state={state}, station={new_freq/1e6:.3f} MHz")
    except asyncio.CancelledError:
        pass
    finally:
        await pubsub.unsubscribe(CHANNEL_STATE)
        await redis.close()
        print("[Main] Stopped monitoring state machine.")


async def main(args) -> None:
    # Instantiate components with CLI args
    streamer = Streamer(
        freq=args.primary,
        gain=float(DEFAULT_GAIN),
        play_audio=not args.no_audio
    )
    classifier = Classifier()
    state_machine = StateMachine(
        station_primary=args.primary,
        station_secondary=args.secondary
    )

    # Tasks
    streamer_task = asyncio.create_task(streamer.start())
    classifier_task = asyncio.create_task(classifier.run())
    state_machine_task = asyncio.create_task(state_machine.run())
    monitor_task = asyncio.create_task(monitor_state(streamer))

    try:
        await asyncio.gather(
            streamer_task,
            classifier_task,
            state_machine_task,
            monitor_task
        )
    except KeyboardInterrupt:
        print("\n[Main] KeyboardInterrupt, shutting down...")
        await streamer.stop()
        for t in (streamer_task, classifier_task, state_machine_task, monitor_task):
            t.cancel()
    finally:
        await asyncio.sleep(0.1)
        print("[Main] Cleanup complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SDR Processor pipeline")
    parser.add_argument("--no-audio", action="store_true", help="Run without playing audio")
    parser.add_argument("--primary", type=float, default=DEFAULT_FREQ, help="Primary station frequency (Hz)")
    parser.add_argument("--secondary", type=float, default=DEFAULT_FREQ2, help="Secondary station frequency (Hz)")
    args = parser.parse_args()

    asyncio.run(main(args))
