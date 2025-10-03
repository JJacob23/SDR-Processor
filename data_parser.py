import os
import librosa
import soundfile as sf
import pandas as pd
import numpy as np

WAV_DIR = "data/wav"
LABEL_DIR = "data/wav_labels"
OUT_DIR = "data/chunks"
WINDOW_S = 10.0
HOP_S = 5.0 #overlap 5s
SAMPLE_RATE = 16000 #Downsample from 48kHz to 16kHz

os.makedirs(os.path.join(OUT_DIR, "song"), exist_ok=True)
os.makedirs(os.path.join(OUT_DIR, "ad"), exist_ok=True)

def load_labels(csv_path):
    """
    Parse label CSV: start,end,type
    Returns list of (start_sec, end_sec, type)
    """
    labels = []
    df = pd.read_csv(csv_path)
    for _, row in df.iterrows():
        start = sum(float(x) * 60 ** i for i, x in enumerate(reversed(row["start"].split(":"))))
        end = sum(float(x) * 60 ** i for i, x in enumerate(reversed(row["end"].split(":"))))
        labels.append((start, end, row["type"]))
    return labels


def label_for_window(start, end, labels):
    """
    This takes in a WINDOW_S sized segement of audio and a list of labels associated with it.
    It then assigns the label that has the most overlap with the segment.
    """
    overlaps = {"song": 0.0, "ad": 0.0}
    for seg_start, seg_end, seg_type in labels:
        # compute overlap
        overlap = max(0, min(end, seg_end) - max(start, seg_start))
        overlaps[seg_type] += overlap
    return max(overlaps, key=overlaps.get)

def process_file(wav_path, label_path):
    '''
    Segment a single WAV file into chunks with labels.
    '''
    base = os.path.splitext(os.path.basename(wav_path))[0]
    print(f"Processing {base}")


    # Load audio waveform into y as numpy array
    y, sr = librosa.load(wav_path, sr=SAMPLE_RATE, mono=True)
    labels = load_labels(label_path)
    total_duration = librosa.get_duration(y=y, sr=sr)
    i = 0
    for start in np.arange(0, total_duration - WINDOW_S, HOP_S):
        end = start + WINDOW_S
        chunk = y[int(start*sr):int(end*sr)]

        label = label_for_window(start, end, labels)
        out_path = os.path.join(OUT_DIR, label, f"{base}_{i:04d}.wav")

        sf.write(out_path, chunk, sr)
        print(f"Writing Chunk: {out_path} ({label})")
        i += 1

def main():
    '''
    Process all WAV files in WAV_DIR with corresponding labels in LABEL_DIR.
    '''
    for fname in os.listdir(WAV_DIR):
        if fname.endswith(".wav"):
            wav_path = os.path.join(WAV_DIR, fname)
            label_path = os.path.join(LABEL_DIR, fname.replace(".wav", ".csv"))
            if os.path.exists(label_path):
                process_file(wav_path, label_path)
            else:
                print(f"No label file for {fname}")

if __name__ == "__main__":
    main()