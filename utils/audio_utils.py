'''
Functions for processing wav audio
'''


import torch
import torchaudio
import numpy as np

def ensure_tensor(waveform, dtype=torch.float32):
    """
    Converts incoming waveform to a 2D torch tensor [1, samples].
    Accepts list, numpy array, or bytes.
    """
    if isinstance(waveform, torch.Tensor):
        return waveform

    if isinstance(waveform, bytes):
        # Assume float32 PCM bytes
        waveform = np.frombuffer(waveform, dtype=np.float32)

    if isinstance(waveform, np.ndarray):
        waveform = torch.from_numpy(waveform)

    # Ensure 2D: [channels, samples]
    if waveform.dim() == 1:
        waveform = waveform.unsqueeze(0)

    return waveform.to(dtype)

def mono(waveform: torch.Tensor) -> torch.Tensor:
    """
    Converts multi-channel audio to mono by averaging channels.
    waveform: [channels, samples]
    returns: [1, samples]
    """
    if waveform.shape[0] > 1:
        waveform = waveform.mean(dim=0, keepdim=True)
    return waveform


def resample(waveform: torch.Tensor, orig_sr: int, target_sr: int) -> torch.Tensor:
    """
    Resample waveform to target sampling rate.
    """
    if orig_sr != target_sr:
        waveform = torchaudio.functional.resample(waveform, orig_sr, target_sr)
    return waveform


def normalize_duration(waveform: torch.Tensor, sr: int, target_duration: float) -> torch.Tensor:
    """
    Pad or trim waveform to be exactly target_duration seconds.
    """
    target_len = int(sr * target_duration)
    cur_len = waveform.shape[1]

    if cur_len > target_len:
        # Trim excess
        waveform = waveform[:, :target_len]
    elif cur_len < target_len:
        # Pad with zeros at the end
        pad = target_len - cur_len
        waveform = torch.nn.functional.pad(waveform, (0, pad))
    return waveform


def waveform_to_mel_spectrogram(waveform: torch.Tensor, sr: int, n_mels: int, window_size: int, hop_size: int) -> torch.Tensor:
    """
    Convert waveform → log-mel spectrogram tensor.
    Returns tensor shape [1, n_mels, time_frames].
    """
    # Take fft into WINDOW_SIZE frequency bins
    # Push those into N_MELS bands
    # Do this for ever HOP_SIZE for the entire chunk to build the spectrogram
    # So the finished spectrogram is N_MELS high and (samples/HOP_SIZE) wide.
    mel_spectrogram = torchaudio.transforms.MelSpectrogram(
        sample_rate=sr,
        n_fft=window_size,
        hop_length=hop_size,
        n_mels=n_mels
    )(waveform)

    # Power data becomes sparse when normalized.
    # squash to decibels for more meaningful differences. 
    mel_spectrogram = torchaudio.transforms.AmplitudeToDB()(mel_spectrogram)
    return mel_spectrogram

def load_and_process_wav(path: str, target_sr: int, n_mels: int, window_size: int, hop_size: int, target_duration: float = 10.0) -> torch.Tensor:
    """
    Full preprocessing pipeline:
    - Load wav
    - Resample
    - Convert to mono
    - Pad/trim to exact duration
    - Convert to log-mel spectrogram
    Returns: torch.Tensor [1, n_mels, time_frames]
    """
    waveform, sr = torchaudio.load(path)
    waveform = mono(waveform)
    waveform = resample(waveform, sr, target_sr)
    waveform = normalize_duration(waveform, target_sr, target_duration)
    mel_spec = waveform_to_mel_spectrogram(waveform, target_sr, n_mels, window_size, hop_size)
    return mel_spec
