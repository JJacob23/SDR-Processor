# SDR-Processor

## Overview
SDR-Processor combines a GNU Radio based FM receiver with a PyTorch classifier. Audio is captured from an RTL-SDR, downsampled, and streamed through Redis where a classifier consumes 10-second windows to distinguish songs from advertisements.

## Environment Setup
- Conda environment described in `environment.yml`.
- Hardware: RTL-SDR with the NooElec R820T running on arch.
- Services: a Redis instance reachable at `redis://localhost:6379`

## Repository Layout
- `receiver/redis_receiver.py`: GNU Radio flowgraph wrapper that publishes 100 ms audio batches to Redis.
- `classifier/redis_classifier.py`: Redis subscriber that buffers audio, produces mel spectrograms, and runs the CNN.
- `classifier/model.py`: The CNN definition/training loop.
- `classifier/data_parser.py`: Generates labeled 10 s chunks from long-form WAV recordings.
- `utils/`: Shared constants and audio preprocessing helpers.
- `data/`: label CSVs, generated chunks, and orignal wav files..
- `models/`: Saved PyTorch weights (`current_model.pt`).

## Typical Workflow
1. Record FM audio with `receiver/fm_recorder.py` or your own GNU Radio flow.
2. Generate labeled training data via `classifier/data_parser.py` (expects CSV labels in `data/wav_labels`).
3. Train the CNN with `classifier/model.py` to refresh `models/current_model.pt`.
4. Run the Rx/Classifier with: 
  `python main.py`
5. Run the FastApi bridge with 
  `uvicorn controller.controller:app --reload`


## Testing and Tuning
- Quick sanity check an RTL-SDR tuning with:
  `rtl_fm -f 101.1M -M wbfm -s 200000 -r 48000 -g 25 -E deemp -F 9 - | ffplay -f s16le -ar 48000 -`
- Run the raw receiver directly with:
  `python receiver/fm_recorder.py [-h for options]`

## TODO
- Errors are still thrown on interrupt, improve graceful stopping
- Prettier UI
- Retraining
- Station swapping logic
- Containerization

- Station quick references:
  - 98.700e6 -> WMZQ country (clear)
  - 101.1e6 -> DC variety (intermittent)
  - 100.304e6 -> classic rock (clear)

