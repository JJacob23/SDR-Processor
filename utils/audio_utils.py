from __future__ import annotations
from typing import Union
import numpy as np
import torch
import torchaudio

#Waveform can come in any of these shapes
ArrayLike = Union[np.ndarray, bytes, torch.Tensor]

'''
Functions for processing wav audio
'''
def ensure_tensor(waveform: ArrayLike) -> torch.Tensor:
    """
    Convert input (list/ndarray/bytes/tensor) to a 2D tensor [1, samples].
    Args:
        waveform: Audio as numpy array, bytes, or torch.Tensor.
    Returns:
        tensor with shape [channels, samples].
    """
    if isinstance(waveform, torch.Tensor):
        t = waveform
    elif isinstance(waveform, bytes):
        t = torch.from_numpy(np.frombuffer(waveform, dtype=np.float32))
    elif isinstance(waveform, np.ndarray):
        t = torch.from_numpy(waveform)
    else:
        t = torch.as_tensor(waveform)

    if t.dim() == 1:
        t = t.unsqueeze(0)
    return t.to(torch.float32)

def mono(waveform: torch.Tensor) -> torch.Tensor:
    """
    Converts multi-channel audio to mono by averaging channels.
    Args:
        waveform: [channels, samples]
    Returns:
        [1, samples]
    """
    if waveform.shape[0] > 1:
        waveform = waveform.mean(dim=0, keepdim=True)
    return waveform


def resample(waveform: torch.Tensor, orig_sr: int, target_sr: int) -> torch.Tensor:
    """
    Resample waveform to target sampling rate.
    Args:
        waveform: [channels, samples]
    Returns:
        [channels, samples]
    """
    if orig_sr != target_sr:
        waveform = torchaudio.functional.resample(waveform, orig_sr, target_sr)
    return waveform


def normalize_duration(waveform: torch.Tensor, sr: int, target_duration: float) -> torch.Tensor:
    """
    Pad or trim waveform to be exactly target_duration seconds.
    Args:
        waveform: [channels, samples]
        sr: Sample rate
        target_duration: Desired length in seconds
    Returns:
        [channels, samples]
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
    Convert waveform -> log-mel spectrogram tensor.
    Args:
        waveform: [channels, samples]
        sr: Sample rate
        n_mels: Number of mel frequency bands
        window_size: number of frequency bins from fft
        hop_size: step size through the audio sample
    Returns:
        [1, n_mels, time_frames].
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

def load_and_process_wav(path: str, target_sr: int, n_mels: int, window_size: int, hop_size: int, target_duration: float) -> torch.Tensor:
    """
    Full preprocessing pipeline:
    - Load wav
    - Resample
    - Convert to mono
    - Pad/trim to exact duration
    - Convert to log-mel spectrogram

    Args:
        path: location of .wav file to be converted to spectrogram
        target_sr: target sample rate
        n_mels: Number of mel frequency bands
        window_size: number of frequency bins from fft
        hop_size: step size through the audio sample
    Returns:
        torch.Tensor [1, n_mels, time_frames]
    """
    waveform, sr = torchaudio.load(path)
    waveform = mono(waveform)
    waveform = resample(waveform, sr, target_sr)
    waveform = normalize_duration(waveform, target_sr, target_duration)
    mel_spec = waveform_to_mel_spectrogram(waveform, target_sr, n_mels, window_size, hop_size)
    return mel_spec
