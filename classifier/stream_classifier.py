import time
import torch
import os
import sys
from model import AudioCNN
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))) #Run as module later, but this lets me test the file directly for now.
from utils.constants import MODEL_PATH, SAMPLE_RATE, N_MELS, WINDOW_SIZE, HOP_SIZE, CHUNK_DURATION_S, LIVE_DIR, INVERSE_LABELS
import utils.audio_utils as audio_utils