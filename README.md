# SDR-Processor

## Overview
SDR-Processor combines a GNU Radio based FM receiver with a PyTorch classifier that distinguishes songs from advertisements in 10-second audio chunks.

## Environment
- Conda environment described in environment.yml.
- Hardware: RTL-SDR with the NooElec R820T running on arch.

## Repository Layout
- receiver/: GNU Radio flowgraph wrappers for tuning, recording, and streaming.
- classifier/: Dataset tooling, CNN model definition, and inference scripts..
- utils/: Shared constants and audio preprocessing helpers.
- data/: Raw WAV captures, label CSVs, generated chunks, and live-capture directory.
- models/: Saved PyTorch weights (current_model.pt).

## Typical Workflow
1. Record FM audio with receiver/fm_recorder.py or stream live chunks with receiver/fm_chunk_streamer.py.
2. Generate labeled 10 s chunks via classifier/data_parser.py (expects CSV labels in data/wav_labels).
3. Train the CNN with classifier/model.py to refresh models/current_model.pt.
4. Classify new chunks using classifier/chunk_classifier.py, which watches data/live and prints song/ad predictions.
5. Websocket UI can be ran with uvicorn controller.controller:app --reload. Its currenty laggy

## Testing and Tuning
- Quick sanity check an RTL-SDR tuning with:
  rtl_fm -f 101.1M -M wbfm -s 200000 -r 48000 -g 25 -E deemp -F 9 - | ffplay -f s16le -ar 48000 -
- Run the receiver directly with:
  python receiver/fm_recorder.py [-h for options]

## Development Notes
- Lag reports on UI because classifier and audio streams sip from the same queue. Ill fix this later with a real broker.
- Station quick references:
  - 98.700e6 -> WMZQ country (clear)
  - 101.1e6 -> DC variety (intermittent)
  - 100.304e6 -> classic rock (clear)
