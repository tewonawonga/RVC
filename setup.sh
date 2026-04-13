#!/usr/bin/env bash
# =============================================================================
# RVC Voice Conversion Web App — Setup Script
# Target:  NVIDIA GTX 1650 SUPER (4 GB VRAM)
# Python:  3.10
# CUDA:    11.8 (change CUDA_TAG below if using 12.1)
# =============================================================================
set -euo pipefail

CUDA_TAG="cu118"        # change to "cu121" for CUDA 12.1
TORCH_VER="2.0.1"
TORCHAUDIO_VER="2.0.2"
PYTHON_BIN="${PYTHON_BIN:-python3.10}"
VENV_DIR="${VENV_DIR:-.venv}"

# Colours
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()  { echo -e "${GREEN}[setup]${NC} $*"; }
warn()  { echo -e "${YELLOW}[warn] ${NC} $*"; }
error() { echo -e "${RED}[error]${NC} $*" >&2; exit 1; }

# ── 0. Pre-flight checks ──────────────────────────────────────────────────────
info "Checking Python version…"
PY_VER=$("$PYTHON_BIN" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null) \
  || error "Python 3.10 not found. Install it or set PYTHON_BIN=/path/to/python3.10"

[[ "$PY_VER" == "3.10" ]] || warn "Expected Python 3.10, got $PY_VER — proceeding but may encounter issues."

info "Python $PY_VER found at $(which "$PYTHON_BIN")"

# Check CUDA via nvidia-smi (works in WSL2 without nvcc installed)
if command -v nvidia-smi &>/dev/null; then
  GPU_NAME=$(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -1 || echo "Unknown GPU")
  info "NVIDIA GPU detected: $GPU_NAME — will install CUDA PyTorch ($CUDA_TAG)"
else
  warn "nvidia-smi not found — installing CPU-only PyTorch (slower, no GPU)."
  warn "If you have an NVIDIA GPU, install drivers on Windows and restart WSL."
  CUDA_TAG="cpu"
fi

# ── 1. Create virtual environment ─────────────────────────────────────────────
if [[ ! -d "$VENV_DIR" ]]; then
  info "Creating virtual environment in ./$VENV_DIR …"
  "$PYTHON_BIN" -m venv "$VENV_DIR"
else
  info "Virtual environment already exists at ./$VENV_DIR"
fi

# Activate
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"
info "Activated: $(which python) ($(python --version))"

# Upgrade pip / wheel / setuptools
pip install --quiet --upgrade pip wheel setuptools

# ── 2. Install PyTorch with CUDA support ─────────────────────────────────────
info "Installing PyTorch $TORCH_VER ($CUDA_TAG) …"
if [[ "$CUDA_TAG" == "cpu" ]]; then
  pip install torch=="${TORCH_VER}" torchaudio=="${TORCHAUDIO_VER}" \
    --extra-index-url https://download.pytorch.org/whl/cpu
else
  pip install torch=="${TORCH_VER}+${CUDA_TAG}" torchaudio=="${TORCHAUDIO_VER}+${CUDA_TAG}" \
    --extra-index-url "https://download.pytorch.org/whl/${CUDA_TAG}"
fi

# ── 3. Install faiss (GPU preferred, CPU fallback) ────────────────────────────
info "Installing faiss …"
if [[ "$CUDA_TAG" != "cpu" ]]; then
  pip install faiss-gpu==1.7.4 2>/dev/null \
    || { warn "faiss-gpu install failed, installing faiss-cpu instead"; pip install faiss-cpu==1.7.4; }
else
  pip install faiss-cpu==1.7.4
fi

# ── 4. Install remaining requirements ────────────────────────────────────────
info "Installing Python requirements …"
# Exclude comments and packages already installed above (torch, torchaudio, faiss)
grep -v -E '^\s*#|^torch|^torchaudio|^faiss' requirements.txt \
  | pip install -r /dev/stdin

# ── 5. Install RMVPE dependencies ────────────────────────────────────────────
info "Installing RMVPE …"
pip install "git+https://github.com/yxlllc/RMVPE.git" 2>/dev/null \
  || warn "RMVPE install failed — harvest pitch extractor will be used as fallback."

# ── 6. Install pyworld for harvest pitch fallback ─────────────────────────────
info "Installing pyworld …"
pip install pyworld==0.3.4 2>/dev/null \
  || warn "pyworld install failed — pitch extraction may be limited."

# ── 7. Create required directories ───────────────────────────────────────────
info "Creating application directories …"
mkdir -p models uploads outputs static

# ── 8. Download RVC + HuBERT models ──────────────────────────────────────────
info "Downloading model files …"
python download_models.py

# ── 9. Pre-cache HuBERT from HuggingFace ─────────────────────────────────────
info "Pre-downloading HuBERT from HuggingFace (this is cached for future runs) …"
python - <<'PYEOF'
from transformers import HubertModel, Wav2Vec2FeatureExtractor
print("  Fetching facebook/hubert-base-ls960 …")
Wav2Vec2FeatureExtractor.from_pretrained("facebook/hubert-base-ls960")
HubertModel.from_pretrained("facebook/hubert-base-ls960", output_hidden_states=True)
print("  HuBERT cached.")
PYEOF

# ── 10. Final summary ─────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   Setup complete!                                ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════╝${NC}"
echo ""
echo "  Activate the environment:  source .venv/bin/activate"
echo "  Start the server:          python app.py"
echo "  Open in browser:           http://localhost:7860"
echo ""
echo "  GPU optimisation notes for GTX 1650 SUPER (4 GB VRAM):"
echo "    · Float16 (half) precision is enabled automatically on CUDA"
echo "    · Audio is processed in 15-second chunks to bound VRAM usage"
echo "    · GPU cache is cleared after each chunk"
echo ""
