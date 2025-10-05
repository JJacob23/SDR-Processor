from __future__ import annotations
import os

# Network / services
REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")

# SDR defaults
DEFAULT_FREQ: float = float(os.getenv("SDR_FREQ", 100.304e6))
DEFAULT_GAIN: int = int(os.getenv("SDR_GAIN", 25))
DEFAULT_PPM: float = float(os.getenv("SDR_PPM", 0.0))