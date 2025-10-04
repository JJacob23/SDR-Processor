import os
import glob
import torch
import torch.nn as nn
import torch.optim as optim
import torchaudio
import random
from torch.utils.data import Dataset, DataLoader, WeightedRandomSampler, random_split

'''
Parameter notes:
Audio chunks from data_parser.py are 10s long wav files downsampled to 16kHz
A window size of 1024 samples at 16kHz = 64ms per frame
A hop size of 512 samples at 16kHz = 32ms overlap
Using 64 mel bands should give a good frequency resolution, try 128 if needed
Each 10s chunk will yield about 312.5 frames (10000ms / 32ms)
So each input tensor will be (1, 64, 313) after mel spectrogram and log scaling
'''
DATA_DIR = "data/chunks"
SAVE_DIR = "models"
MODEL_PATH = os.path.join(SAVE_DIR, "current_model.pt")
SAMPLE_RATE = 16000
N_MELS = 64
WINDOW_SIZE = 1024
HOP_SIZE = 512


class AudioDataset(Dataset):
    def __init__(self, data_dir=DATA_DIR):
        '''
        Load all the data in data_dir and label it based on its dir.
        '''
        self.samples = []
        self.labels = {"song": 0, "ad": 1} 

        #Make tuples of every chunk path and its label.
        for label in self.labels:
            files = glob.glob(os.path.join(data_dir, label, "*.wav"))
            for f in files:
                self.samples.append((f, self.labels[label]))

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        path, label = self.samples[idx]
        waveform, sr = torchaudio.load(path)

        # Make sure chunks match expected sample rate
        if sr != SAMPLE_RATE:
            waveform = torchaudio.functional.resample(waveform, sr, SAMPLE_RATE)

        # Make sure audio is in mono
        if waveform.shape[0] > 1:
            waveform = waveform.mean(dim=0, keepdim=True)

        # Take fft into WINDOW_SIZE frequency bins
        # Push those into N_MELS bands
        # Do this for ever HOP_SIZE for the entire chunk to build the spectrogram
        # So the finished spectrogram is N_MELS high and (samples/HOP_SIZE) wide.
        mel_spectrogram = torchaudio.transforms.MelSpectrogram(
            sample_rate=SAMPLE_RATE,
            n_fft=WINDOW_SIZE,
            hop_length=HOP_SIZE,
            n_mels=N_MELS
        )(waveform)

        # Power data becomes sparse when normalized.
        # squash to decibels for more meaningful differences. 
        mel_spectrogram = torchaudio.transforms.AmplitudeToDB()(mel_spectrogram)

        return mel_spectrogram, label


def make_dataloaders(data_dir=DATA_DIR, batch_size=32, seed=100):
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


    train_loader = DataLoader(train_set, batch_size, sampler)
    val_loader   = DataLoader(val_set, batch_size, shuffle=False)
    test_loader  = DataLoader(test_set, batch_size, shuffle=False)

    print(f"Total: {n_total} | Train: {n_train}, Val: {n_val}, Test: {n_test}")
    print(f"Class counts (train): {class_counts}")
    
    return train_loader, val_loader, test_loader


class AudioCNN(nn.Module):
    def __init__(self, n_mels=64, n_classes=2):
        super(AudioCNN, self).__init__()

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

    def forward(self, x):
        '''
        Called by nn.model.train()
        '''
        #data comes in as [Batch size, 1 channel(mono sound), n_mels frequencies, 10s of data 512-hop at 16kHz -> 312 frames]
        x = self.cnn(x) # Leaves as [B, 64 filters, 1 pooled freq, 1 pooled time] after global avg pool
        x = x.view(x.size(0), -1)  # Flatten to [B, 64] (64 filter activations * average value at frequency * average value over time)
        return self.feed_forward(x)  # Returns logits [B, 2], leave as logits untill inferences to avoid vanishing gradient.  
        
def train(model, train_loader, val_loader, device, epochs=10, lr=1e-3):
    '''
    Consider implementing early stopping later if I can automatically generate more training data. 
    '''
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=lr)

    model.to(device)

    for epoch in range(1, epochs + 1):
        model.train()
        total_loss, correct, total = 0, 0, 0

        for mel, label in train_loader:
            mel, label = mel.to(device), label.to(device)
            optimizer.zero_grad()
            out = model(mel)
            loss = criterion(out, label)
            loss.backward()
            optimizer.step()

            total_loss += loss.item()
            _, pred = out.max(1)
            correct += (pred == label).sum().item()
            total += label.size(0)

        train_acc = correct / total

        val_acc = evaluate(model, val_loader, device)
        print(f"Epoch {epoch}: "
              f"Train Loss={total_loss/len(train_loader):.4f}, "
              f"Train Acc={train_acc:.3f}, Val Acc={val_acc:.3f}")

    return model

def evaluate(model, loader, device):
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


def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    train_loader, val_loader, test_loader = make_dataloaders()

    #Evaluate old model on current test set data
    model = AudioCNN()
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
        print("Accuracy improved from {prev_accuracy} to {new_accuracy}")
        print("Saving over old model.")
    else:
        print("Accuracy did NOT improve from {prev_accuracy} to {new_accuracy}")
        print("Keeping old model.")


if __name__ == "__main__":
    main()
