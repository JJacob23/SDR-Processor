FROM python:3.11-slim
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libsndfile1 ffmpeg git && rm -rf /var/lib/apt/lists/*

RUN pip install torch
RUN pip install --no-cache-dir fastapi "uvicorn[standard]" redis numpy soundfile

COPY controller/ controller/
COPY classifier/ classifier/
COPY utils/ utils/
COPY models/ models/
COPY ui/dist ui/dist 
COPY ui.html ui/ui.html

# Simple UI
COPY ui.html /app/static/ui.html
# React UI
COPY ui/dist /app/static/react

EXPOSE 8000
ENV REDIS_HOST=redis PYTHONUNBUFFERED=1

CMD ["uvicorn", "controller.controller:app", "--host", "0.0.0.0", "--port", "8000"]

