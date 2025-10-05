from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable, List, Tuple

import librosa
import numpy as np
import pandas as pd
import soundfile as sf

WAV_DIR = Path("data/wav")
LABEL_DIR = Path("data/wav_labels")
OUT_DIR = Path("data/chunks")
WINDOW_S = 10.0
HOP_S = 5.0 #overlap 5s
SAMPLE_RATE = 16_000 #Downsample from 48kHz to 16kHz

(OUT_DIR / "song").mkdir(parents=True, exist_ok=True)
(OUT_DIR / "ad").mkdir(parents=True, exist_ok=True)

def _parse_time(ts: str) -> float:
    #only supports mm:ss or hh:mm:ss
    parts = list(map(float, ts.split(":")))
    if len(parts) == 2:
        m, s = parts
        return 60 * m + s
    h, m, s = parts
    return 3600 * h + 60 * m + s

def load_labels(csv_path: Path) -> list[tuple[float, float, str]]:
    """
    Parse label CSV: start,end,type
    Returns list of (start_sec, end_sec, type)
    """
    df = pd.read_csv(csv_path)
    labels: list[tuple[float, float, str]] = []
    for _, row in df.iterrows():
        start = _parse_time(str(row["start"]))
        end = _parse_time(str(row["end"]))
        labels.append((float(start), float(end), str(row["type"])) )
    return labels


def label_for_window(start: float, end: float, labels: list[tuple[float, float, str]]) -> str:
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

def process_file(wav_path: Path, label_path: Path) -> None:
    '''Segment a single WAV file into chunks with labels.'''
    base = wav_path.stem
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

def main() -> None:
    '''
    Process all WAV files in WAV_DIR with corresponding labels in LABEL_DIR.
    '''
    for wav in WAV_DIR.glob("*.wav"):
        csv = LABEL_DIR / (wav.stem + ".csv")
        if csv.exists():
            process_file(wav, csv)
        else:
            print(f"No label file for {wav.name}")

if __name__ == "__main__":
    main()