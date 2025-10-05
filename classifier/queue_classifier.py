
import torch
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))) #Run as module later, but this lets me test the file directly for now.
from utils.constants import MODEL_PATH, SAMPLE_RATE, N_MELS, WINDOW_SIZE, HOP_SIZE, CHUNK_DURATION_S, INVERSE_LABELS
from utils.audio_utils import (
    ensure_tensor,
    mono,
    normalize_duration,
    waveform_to_mel_spectrogram,
)
from classifier.model import AudioCNN
import asyncio
import numpy as np

class QueueClassifier:
    """
    Pulls small waveform batches from an async queue and runs classification
    over 10s windows.
    """
    def __init__(self, queue: asyncio.Queue, device=None, chunk_seconds=CHUNK_DURATION_S):
        self.queue = queue
        self.buffer = np.zeros(0, dtype=np.float32)
        self.chunk_samples = int(SAMPLE_RATE * chunk_seconds)
        self.device = device or torch.device("cuda" if torch.cuda.is_available() else "cpu")

        self.model = AudioCNN()
        self.model.load_state_dict(torch.load(MODEL_PATH, map_location=self.device))
        self.model.to(self.device)
        self.model.eval()
        print("[Classifier] Model Ready...")

    async def run(self):
        """
        Continuously consume float batches from queue and classify when enough accumulates.
        """
        try:
            while True:
                samples = await self.queue.get()
                if samples is None:
                    break

                self.buffer = np.concatenate((self.buffer, samples))

                if len(self.buffer) > self.chunk_samples:
                    self.buffer = self.buffer[-self.chunk_samples:]

                if len(self.buffer) == self.chunk_samples:
                    pred, probs = self.classify(self.buffer)
                    label = INVERSE_LABELS[pred]
                    print(f"[Classifier] {label}  (p={probs})")
                    self.buffer = np.zeros(0, dtype=np.float32)

        except asyncio.CancelledError:
            print("[Classifier] Stopping Classifier...")
            pass

    def classify(self, waveform):
        """
        Run model inference on a 1D numpy waveform.
        """
        waveform = ensure_tensor(waveform)
        waveform = mono(waveform)
        waveform = normalize_duration(waveform, SAMPLE_RATE, CHUNK_DURATION_S)
        mel_spectrogram = waveform_to_mel_spectrogram(waveform, SAMPLE_RATE, N_MELS, WINDOW_SIZE, HOP_SIZE)
        mel_spectrogram = mel_spectrogram.unsqueeze(0).to(self.device)
        with torch.no_grad():
            logits = self.model(mel_spectrogram)
            probs = torch.softmax(logits, dim=1).squeeze().cpu().numpy()
            pred = int(np.argmax(probs))
        return pred, probs
