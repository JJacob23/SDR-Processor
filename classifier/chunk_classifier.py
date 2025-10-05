import time
import torch
import os
import sys
from model import AudioCNN
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))) #Run as module later, but this lets me test the file directly for now.
from utils.constants import MODEL_PATH, SAMPLE_RATE, N_MELS, WINDOW_SIZE, HOP_SIZE, CHUNK_DURATION_S, LIVE_DIR, INVERSE_LABELS
import utils.audio_utils as audio_utils

def predict(path, model, device):
    mel_spectrogram = audio_utils.load_and_process_wav(path,SAMPLE_RATE,N_MELS,WINDOW_SIZE,HOP_SIZE,CHUNK_DURATION_S)
    mel_spectrogram = mel_spectrogram.unsqueeze(0).to(device)  # adds batch size 1 to start of spectrogram

    with torch.no_grad():
        logits = model(mel_spectrogram)
        probs = torch.softmax(logits, dim=1)
        pred = torch.argmax(probs, dim=1).item()

    return pred, probs.squeeze().cpu().numpy()

def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = AudioCNN()
    model.load_state_dict(torch.load(MODEL_PATH, map_location=device))
    model.to(device)
    model.eval()
    print(f"Loaded model from {MODEL_PATH}")

    seen = set()

    while True:
        for fname in os.listdir(LIVE_DIR):
            if not fname.endswith(".wav") or fname in seen:
                continue

            path = os.path.join(LIVE_DIR, fname)
            pred, probs = predict(path, model, device)

            label = INVERSE_LABELS[pred]
            print(f"{fname}: {label} (P={probs})")
            seen.add(fname)

        time.sleep(2)

if __name__ == "__main__":
    main()
