import time
import torch
import torchaudio
import os

from model import AudioCNN
from model import SAMPLE_RATE, N_MELS, WINDOW_SIZE, HOP_SIZE, MODEL_PATH


#Currently model just watches this dir for the current radio sample.
#Swap to a message queue later.
LIVE_DIR = "data/live"



#Get working for now, Separate out audio processing into utils later. 
def predict(wav_path, model, device):
    waveform, sr = torchaudio.load(wav_path)

    # Resample + mono
    if sr != SAMPLE_RATE:
        waveform = torchaudio.functional.resample(waveform, sr, SAMPLE_RATE)
    if waveform.shape[0] > 1:
        waveform = waveform.mean(dim=0, keepdim=True)

    mel_spec = torchaudio.transforms.MelSpectrogram(
        sample_rate=SAMPLE_RATE,
        n_fft=WINDOW_SIZE,
        hop_length=HOP_SIZE,
        n_mels=N_MELS
    )(waveform)
    mel_spec = torchaudio.transforms.AmplitudeToDB()(mel_spec)
    mel_spec = mel_spec.unsqueeze(0).to(device)  # adds batch size 1 to start of spectrogram

    with torch.no_grad():
        logits = model(mel_spec)
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

            #Probably pull this definition out to somewhere centralized.
            label = "song" if pred == 0 else "ad"
            print(f"{fname}: {label} (P={probs})")
            seen.add(fname)

        time.sleep(2)

if __name__ == "__main__":
    main()
