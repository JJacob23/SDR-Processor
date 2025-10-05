from pathlib import Path

# Project paths
BASE_DIR: Path = Path(__file__).resolve().parent.parent
DATA_DIR: Path = BASE_DIR / "data" / "chunks"
SAVE_DIR: Path = BASE_DIR / "models"
MODEL_PATH: Path = SAVE_DIR / "current_model.pt"


'''
Model Parameter notes:
Audio chunks from data_parser.py are 10s long wav files downsampled to 16kHz
A window size of 1024 samples at 16kHz = 64ms per frame
A hop size of 512 samples at 16kHz = 32ms overlap
Using 64 mel bands should give a good frequency resolution, try 128 if needed
Each 10s chunk will yield about 312.5 frames (10000ms / 32ms)
So each input tensor will be (1, 64, 313) after mel spectrogram and log scaling
'''
SAMPLE_RATE: int = 16000
RAW_SAMPLE_RATE: int = 48000
N_MELS: int = 64
WINDOW_SIZE: int = 1024
HOP_SIZE: int = 512
CHUNK_DURATION_S: float = 10.0

#Model hyperparameters
N_CLASSES: int = 2
EPOCHS: int = 10
LR: float = 1e-3


# Stream batching
BATCH_MS: int = 100

# Class Labels
LABELS: dict[str, int] = {"song": 0, "ad": 1}
INVERSE_LABELS: dict[int, str] = {v: k for k, v in LABELS.items()}

# Redis channel names (static strings used across the app)
CHANNEL_AUDIO: str = "audio_stream"
CHANNEL_CLASSIFIER: str = "classifier_stream"
CHANNEL_STATE: str = "state_stream"