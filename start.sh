#!/usr/bin/env bash
set -e

echo "Starting SDR-Processor"

# Start Redis if not running
if ! pgrep -x "redis-server" >/dev/null; then
  echo "Starting Redis..."
  redis-server --daemonize yes
else
  echo "Redis already running."
fi

echo "Starting FastAPI controller..."
uvicorn controller.controller:app --reload --port 8000 &
FASTAPI_PID=$!

# --- 3. Start main pipeline ---
echo "Starting streamer/classifier main..."

# Forward any CLI args (e.g., --no-audio, --primary, --secondary)
python -m main "$@"

# --- 4. Clean up ---
echo "Shutting down FastAPI controller..."
kill $FASTAPI_PID
echo "Done."
