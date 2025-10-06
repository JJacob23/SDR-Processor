from __future__ import annotations
import asyncio
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
            data = json.loads(message["data"])
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
        await redis.aclose()
        print("[Main] Stopped monitoring state machine.")

async def main() -> None:
    streamer = Streamer(freq=DEFAULT_FREQ, gain=float(DEFAULT_GAIN), play_audio=True)
    classifier = Classifier()
    #state_machine = StateMachine(station_primary=DEFAULT_FREQ2, station_secondary=DEFAULT_FREQ)
    state_machine = StateMachine(station_primary=DEFAULT_FREQ, station_secondary=DEFAULT_FREQ2)

    streamer_task = asyncio.create_task(streamer.start())
    classifier_task = asyncio.create_task(classifier.run())
    state_machine_task = asyncio.create_task(state_machine.run())
    monitor_task = asyncio.create_task(monitor_state(streamer))

    try:
        await asyncio.gather(streamer_task,  classifier_task, state_machine_task, monitor_task)
    except KeyboardInterrupt:
        print("\n[Main] KeyboardInterrupt, shutting down...")
        await streamer.stop()
        for task in (streamer_task, classifier_task, state_machine_task, monitor_task):
            task.cancel()
    finally:
        await asyncio.sleep(0.1)
        print("[Main] Cleanup complete.")

if __name__ == "__main__":
    asyncio.run(main())
