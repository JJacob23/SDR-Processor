from __future__ import annotations
import asyncio
import json
import redis.asyncio as aioredis
from utils.constants import CHANNEL_STATE,CHANNEL_CLASSIFIER
from utils.config import REDIS_URL, DEFAULT_FREQ, DEFAULT_FREQ2

class StateMachine:
    """Finite state machine reacting to classifier output."""

    STATES = ["primary", "patience1", "patience2", "secondary"]
    MUSIC_LABEL = "song"
    AD_LABEL = "ad"

    def __init__(
        self,
        redis_url: str = REDIS_URL,
        state_channel: str = CHANNEL_STATE,
        classifier_channel: str= CHANNEL_CLASSIFIER,
        station_primary: float = DEFAULT_FREQ,
        station_secondary: float = DEFAULT_FREQ2
    ) -> None:
        self.redis_url = redis_url
        self.state_channel = state_channel
        self.classifier_channel = classifier_channel
        self.redis: aioredis.Redis | None = None
        self.pubsub: aioredis.client.PubSub | None = None
        self.state: str = "primary"
        self.station_primary: float = station_primary
        self.station_secondary: float = station_secondary
        self.current_station: float = station_primary

    async def connect(self) -> None:
        self.redis = aioredis.from_url(self.redis_url)
        self.pubsub = self.redis.pubsub()
        await self.pubsub.subscribe(self.classifier_channel)
        print(f"[FSM] Subscribed to classifier channel '{self.classifier_channel}'")

    async def run(self) -> None:
        """Main event loop — read classifier labels and update FSM."""
        await self.connect()
        assert self.pubsub is not None
        try:
            async for message in self.pubsub.listen():
                if message["type"] != "message":
                    continue
                payload = json.loads(message["data"])
                label = payload["label"]
                await self.handle_label(label)
        except asyncio.CancelledError:
            pass
        finally:
            if self.pubsub: await self.pubsub.unsubscribe(self.classifier_channel)
            if self.redis: await self.redis.close()

    async def handle_label(self, label: str) -> None:
        """State transition logic."""
        prev_state = self.state


        #Maybe define some graph structure for this later.
        if label == self.MUSIC_LABEL:
            if self.state == "patience1":
                self.state = "primary"
            elif self.state == "patience2":
                self.state = "secondary"
        elif label == self.AD_LABEL:
            if self.state == "primary":
                self.state = "patience1"
            elif self.state == "patience1":
                self.state = "secondary"
                self.current_station=self.station_secondary
            elif self.state == "secondary":
                self.state = "patience2"
            elif self.state == "patience2":
                self.state="primary"
                self.current_station=self.station_primary

        if prev_state != self.state:
            print(f"[FSM] Transition: {prev_state} → {self.state}")
            await self.broadcast_state()

    async def broadcast_state(self) -> None:
        """Publish updated FSM state for the UI."""
        if not self.redis:
            return
        payload = json.dumps({
            "state": self.state,
            "station": self.current_station
        })
        await self.redis.publish(CHANNEL_STATE, payload)

