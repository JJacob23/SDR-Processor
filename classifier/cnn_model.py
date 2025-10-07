from __future__ import annotations

from pathlib import Path
from typing import Iterable, Tuple
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, Dataset, WeightedRandomSampler, random_split
import glob
import os
import utils.audio_utils as audio_utils
from utils.constants import (
    CHUNK_DURATION_S,
    DATA_DIR,
    HOP_SIZE,
    LABELS,
    MODEL_PATH,
    N_MELS,
    SAMPLE_RATE,
    WINDOW_SIZE,
    N_CLASSES,
    EPOCHS,
    LR
)

class AudioDataset(Dataset):
    ''' Load all the data in data_dir and label it based on its dir.'''
    def __init__(self, data_dir: Path = DATA_DIR) -> None:
        self.samples: list[tuple[Path, int]] = []
        for label_name, label_idx in LABELS.items():
            files = glob.glob(os.path.join(str(data_dir / label_name), "*.wav"))
            for f in files:
                self.samples.append((Path(f), label_idx))


    def __len__(self) -> int:
        return len(self.samples)


    def __getitem__(self, idx: int):
        path, label = self.samples[idx]
        mel_spectrogram = audio_utils.load_and_process_wav(path,SAMPLE_RATE,N_MELS,WINDOW_SIZE,HOP_SIZE,CHUNK_DURATION_S)
        return mel_spectrogram, label


def make_dataloaders(
    data_dir: Path = DATA_DIR, batch_size: int = 32, seed: int = 100
    ) -> tuple[DataLoader, DataLoader, DataLoader]:
    
    dataset = AudioDataset(data_dir)

    # Make data splits
    n_total = len(dataset)
    n_train = int(0.80 * n_total)
    n_val = int(0.10 * n_total)
    n_test = n_total - n_train - n_val
    train_set, val_set, test_set = random_split(dataset, [n_train, n_val, n_test],
                                                generator=torch.Generator().manual_seed(seed))

    # Get ratio of song/add int dataset
    labels = [dataset.samples[i][1] for i in train_set.indices]
    class_counts = torch.bincount(torch.tensor(labels))
    class_weights = 1. / class_counts.float()

    # build a sample for torch to use those ratios in the dataloader. 
    sample_weights = [class_weights[label] for label in labels]
    sampler = WeightedRandomSampler(sample_weights, num_samples=len(sample_weights), replacement=True)

    train_loader = DataLoader(train_set, batch_size=batch_size, sampler=sampler)
    val_loader   = DataLoader(val_set, batch_size, shuffle=False)
    test_loader  = DataLoader(test_set, batch_size, shuffle=False)

    print(f"Total: {n_total} | Train: {n_train}, Val: {n_val}, Test: {n_test}")
    print(f"Class counts (train): {class_counts}")
    
    return train_loader, val_loader, test_loader


class AudioCNN(nn.Module):
    def __init__(self, n_classes: int = N_CLASSES) -> None:
        super().__init__()

        #data comes in as [Batch size, 1 channel(mono sound), n_mels frequencies, 10s of data 512-hop at 16kHz -> 312 frames]
        self.cnn = nn.Sequential(
            nn.Conv2d(1, 16, kernel_size=3, stride=1, padding=1), #Data is now [Batch size, 16 filter channels, n_mels, 312]
            nn.ReLU(),
            nn.MaxPool2d((2, 2)), #[Batch size, 16 filter channels, n_mels/2, 156s]

            nn.Conv2d(16, 32, kernel_size=3, stride=1, padding=1), #[Batch size, 32 filter channels, n_mels/2, 156]
            nn.ReLU(),
            nn.MaxPool2d((2, 2)), #[Batch size, 32 filter channels, n_mels/4, 78]

            nn.Conv2d(32, 64, kernel_size=3, stride=1, padding=1), #[Batch size, 64 filter channels, n_mels/4, 78]
            nn.ReLU(),
            nn.AdaptiveAvgPool2d((1, 1))   #data leaves as [Batch size, 64 filter channels, 1 average decibel, 1 average frame]
        )
        self.feed_forward = nn.Linear(64, n_classes)  #Makes results of 64 filters into n classes.

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        '''
        Called by nn.model.train()
        '''
        #data comes in as [Batch size, 1 channel(mono sound), n_mels frequencies, 10s of data 512-hop at 16kHz -> 312 frames]
        x = self.cnn(x) # Leaves as [B, 64 filters, 1 pooled freq, 1 pooled time] after global avg pool
        x = x.view(x.size(0), -1)  # Flatten to [B, 64] (64 filter activations * average value at frequency * average value over time)
        return self.feed_forward(x)  # Returns logits [B, 2], leave as logits untill inferences to avoid vanishing gradient.  
        
def train(
    model: nn.Module,
    train_loader: DataLoader,
    val_loader: DataLoader,
    device: torch.device,
    epochs: int = EPOCHS,
    lr: float = LR,
) -> nn.Module:
    '''
    Consider implementing early stopping later if I can automatically generate more training data. 
    '''
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=lr)

    model.to(device)

    for epoch in range(1, epochs + 1):
        model.train()
        total_loss, correct, total = 0.0, 0, 0

        for mel, label in train_loader:
            mel, label = mel.to(device), label.to(device)
            optimizer.zero_grad()
            out = model(mel)
            loss = criterion(out, label)
            loss.backward()
            optimizer.step()

            total_loss += loss.item()
            _, pred = out.max(1)
            correct += int((pred == label).sum().item())
            total += int(label.size(0))

        train_acc = correct / total if total else 0.0
        val_acc = evaluate(model, val_loader, device)
        print(f"Epoch {epoch}: "
              f"Train Loss={total_loss/len(train_loader):.4f}, "
              f"Train Acc={train_acc:.3f}, Val Acc={val_acc:.3f}")

    return model

def evaluate(model: nn.Module, loader: DataLoader, device: torch.device) -> float:
    model.eval()
    correct, total = 0, 0
    with torch.no_grad():
        for mel, label in loader:
            mel, label = mel.to(device), label.to(device)
            out = model(mel)
            _, pred = out.max(1)
            correct += (pred == label).sum().item()
            total += label.size(0)
    return correct / total if total > 0 else 0.0


def main() -> None:
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    train_loader, val_loader, test_loader = make_dataloaders()

    #Evaluate old model on current test set data

    model = AudioCNN()
    if os.path.exists(MODEL_PATH):
        model.load_state_dict(torch.load(MODEL_PATH, map_location=device))
    model.to(device)
    model.eval()
    prev_accuracy = evaluate(model, test_loader, device)
    print(f"prev acc = {prev_accuracy}")
    
    #Now make a new model on all current sets
    model = train(model, train_loader, val_loader, device, epochs=10, lr=1e-3)
    new_accuracy = evaluate(model, test_loader, device)


    # Compare and replace if improved
    if new_accuracy > prev_accuracy:
        torch.save(model.state_dict(), MODEL_PATH)
        print(f"Accuracy improved from {prev_accuracy} to {new_accuracy}")
        print("Saving over old model.")
    else:
        print(f"Accuracy did NOT improve from {prev_accuracy} to {new_accuracy}")
        print("Keeping old model.")


if __name__ == "__main__":
    main()
