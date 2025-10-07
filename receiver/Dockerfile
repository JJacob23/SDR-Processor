FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive TZ=Etc/UTC
RUN apt-get update && \
    apt-get install -y tzdata gnuradio gr-osmosdr python3 python3-pip && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY receiver/ receiver/
COPY utils/ utils/
COPY controller/ controller/
COPY classifier/ classifier/
COPY main.py .

RUN pip install --no-cache-dir redis numpy soundfile fastapi torch torchaudio
ENV PYTHONPATH=/app
ENV RAW_SAMPLE_RATE=48000 REDIS_HOST=redis

CMD ["python3", "main.py"]

