# RVC Voice Conversion Web App

A local web application that morphs a voiceover recording to match a reference voice using the RVC (Retrieval-based Voice Conversion) inference pipeline.

## Requirements

| Component | Version |
|-----------|---------|
| Python | 3.10 |
| CUDA | 11.8 or 12.1 |
| GPU | NVIDIA GTX 1650 SUPER (4 GB VRAM) or better |
| OS | Linux / Windows (WSL2) |

## Quick Start

```bash
# 1. Run the setup script (creates venv, installs deps, downloads models)
bash setup.sh

# 2. Activate the virtual environment
source .venv/bin/activate

# 3. Start the server
python app.py

# 4. Open in browser
# http://localhost:7860
```

## Manual Setup (step-by-step)

```bash
# Create and activate venv
python3.10 -m venv .venv
source .venv/bin/activate

# Install PyTorch for CUDA 11.8
pip install torch==2.0.1+cu118 torchaudio==2.0.2+cu118 \
  --extra-index-url https://download.pytorch.org/whl/cu118

# Install other dependencies
pip install -r requirements.txt

# Download models (~800 MB total)
python download_models.py

# Start the app
python app.py
```

For **CUDA 12.1**, change `cu118` to `cu121` everywhere above.

## How It Works

```
Voiceover audio  ──►  HuBERT features  ──►  FAISS blend  ──►  RVC Generator  ──►  Output
Reference voice  ──►  HuBERT features  ──►  FAISS index  ──┘
```

1. **HuBERT** extracts 256-dim content features from both source and reference audio.
2. A **FAISS index** is built from the reference voice features.
3. Each source feature vector is blended with its k-nearest neighbours in the reference index — this shifts the voice timbre toward the reference.
4. **RMVPE** (or harvest) extracts the fundamental frequency (F0 / pitch) of the source.
5. The blended features + pitch are decoded by the **RVC v2 Generator** (VITS-based NSF decoder) into a waveform at the target sample rate.

## VRAM Optimisations (GTX 1650 SUPER)

- Half precision (float16) on all model tensors
- Chunked audio processing (15-second windows with cross-fade)
- GPU cache cleared after every chunk
- Single-worker server to avoid concurrent GPU contention

## Project Structure

```
RVC/
├── app.py                # FastAPI server (REST API + static file serving)
├── rvc_infer.py          # Core inference pipeline
├── infer_pack/
│   ├── models.py         # SynthesizerTrnMs256NSFsid (VITS/NSF generator)
│   ├── modules.py        # ResBlock, WN, ResidualCouplingLayer, …
│   ├── attentions.py     # Multi-head attention, FFN, Encoder
│   └── commons.py        # Utility functions
├── static/
│   └── index.html        # Browser UI
├── models/               # Downloaded model files (gitignored)
├── uploads/              # Temporary upload storage (auto-cleaned)
├── outputs/              # Converted audio files
├── requirements.txt
├── setup.sh              # One-command setup
└── download_models.py    # Model downloader
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Web UI |
| `POST` | `/api/convert` | Upload files, start conversion job |
| `GET` | `/api/status/{job_id}` | Poll job status |
| `GET` | `/api/download/{job_id}` | Download converted WAV |
| `GET` | `/api/health` | GPU / model readiness check |

## Parameters

| Parameter | Range | Default | Description |
|-----------|-------|---------|-------------|
| `pitch_shift` | -24 to +24 | 0 | Semitone pitch shift applied before conversion |
| `index_ratio` | 0.0 – 1.0 | 0.75 | How strongly to blend reference voice features (1.0 = full reference) |
