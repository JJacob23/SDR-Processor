#Consider converting these to environmentals once dockerized.

import os
'''
Model Parameter notes:
Audio chunks from data_parser.py are 10s long wav files downsampled to 16kHz
A window size of 1024 samples at 16kHz = 64ms per frame
A hop size of 512 samples at 16kHz = 32ms overlap
Using 64 mel bands should give a good frequency resolution, try 128 if needed
Each 10s chunk will yield about 312.5 frames (10000ms / 32ms)
So each input tensor will be (1, 64, 313) after mel spectrogram and log scaling
'''
DATA_DIR = "data/chunks"
SAVE_DIR = "models"
MODEL_PATH = os.path.join(SAVE_DIR, "current_model.pt")
SAMPLE_RATE = 16000
RAW_SAMPLE_RATE = 48000
N_MELS = 64
WINDOW_SIZE = 1024
HOP_SIZE = 512
CHUNK_DURATION_S = 10



#Chunk based classifier just watches this dir for the current radio sample.
LIVE_DIR = "data/live"

#async queue batch size
BATCH_MS = 100


LABELS = {"song": 0, "ad": 1}
INVERSE_LABELS = {v: k for k, v in LABELS.items()}

REDIS_URL="redis://localhost:6379"

#Just for ease of prototyping
GAIN=25
FREQ=100.304e6
