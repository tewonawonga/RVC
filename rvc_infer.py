"""
RVC Inference Pipeline
Optimized for NVIDIA GTX 1650 SUPER (4GB VRAM), CUDA 11.8/12.1, Python 3.10
"""

import gc
import os
import logging
import traceback
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
import torch
import torch.nn.functional as F
import soundfile as sf
import librosa
import faiss
from scipy import signal

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────────────
MODELS_DIR = Path(__file__).parent / "models"
HUBERT_SAMPLE_RATE = 16000
HOP_SIZE = 160           # 10 ms at 16 kHz
FRAME_SIZE = 1024


# ──────────────────────────────────────────────────────────────────────────────
# Utility helpers
# ──────────────────────────────────────────────────────────────────────────────

def load_audio(path: str, sr: int = HUBERT_SAMPLE_RATE) -> np.ndarray:
    """Load audio and resample to target sample rate, return float32 mono."""
    audio, orig_sr = sf.read(path, always_2d=False)
    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    audio = audio.astype(np.float32)
    if orig_sr != sr:
        audio = librosa.resample(audio, orig_sr=orig_sr, target_sr=sr)
    # Normalise
    peak = np.abs(audio).max()
    if peak > 1e-5:
        audio = audio / peak * 0.95
    return audio


def pad_audio(audio: np.ndarray, sr: int, pad_seconds: float = 0.3) -> np.ndarray:
    pad = int(sr * pad_seconds)
    return np.pad(audio, (pad, pad), mode="reflect")


# ──────────────────────────────────────────────────────────────────────────────
# Pitch extraction (RMVPE or harvest fallback)
# ──────────────────────────────────────────────────────────────────────────────

class RMVPEPitchExtractor:
    """Wrapper around RMVPE for robust F0 extraction."""

    def __init__(self, model_path: str, device: str = "cuda", is_half: bool = True):
        from rmvpe import RMVPE  # installed by setup.sh
        self.model = RMVPE(model_path, is_half=is_half, device=device)

    def extract(self, audio: np.ndarray, sr: int, target_sr: int = HUBERT_SAMPLE_RATE) -> np.ndarray:
        if sr != target_sr:
            audio = librosa.resample(audio, orig_sr=sr, target_sr=target_sr)
        f0 = self.model.infer_from_audio(audio, thred=0.03)
        return f0  # shape (T,)


class HarvestPitchExtractor:
    """pyworld harvest fallback if RMVPE model is unavailable."""

    def extract(self, audio: np.ndarray, sr: int) -> np.ndarray:
        import pyworld
        audio64 = audio.astype(np.float64)
        f0, t = pyworld.harvest(audio64, sr, f0_ceil=1100.0, frame_period=10.0)
        f0 = pyworld.stonemask(audio64, f0, t, sr)
        return f0.astype(np.float32)


def f0_to_coarse(f0: np.ndarray) -> np.ndarray:
    """Quantise continuous F0 to 256 pitch bins used by the model."""
    f0_mel = 1127.0 * np.log(1.0 + f0 / 700.0)
    f0_mel_min = 1127.0 * np.log(1.0 + 50.0 / 700.0)
    f0_mel_max = 1127.0 * np.log(1.0 + 1100.0 / 700.0)
    f0_mel = np.clip(f0_mel, f0_mel_min, f0_mel_max)
    f0_coarse = np.round((f0_mel - f0_mel_min) * 254.0 / (f0_mel_max - f0_mel_min) + 1.0)
    f0_coarse = np.clip(f0_coarse, 1, 255).astype(np.int64)
    f0_coarse[f0 == 0] = 0
    return f0_coarse


# ──────────────────────────────────────────────────────────────────────────────
# HuBERT feature extractor
# ──────────────────────────────────────────────────────────────────────────────

class HubertFeatureExtractor:
    """
    Extracts 256-dim content features using HuBERT via HuggingFace transformers.
    No fairseq required. The final projection weights (768→256) are read directly
    from the fairseq checkpoint file without importing the fairseq library.
    """

    def __init__(self, model_path: str, device: str = "cuda", is_half: bool = True):
        import torch.nn as nn
        from transformers import HubertModel, Wav2Vec2FeatureExtractor

        self.device = device
        self.is_half = is_half

        # Base HuBERT model from HuggingFace (no fairseq needed)
        self.processor = Wav2Vec2FeatureExtractor.from_pretrained(
            "facebook/hubert-base-ls960"
        )
        self.model = HubertModel.from_pretrained(
            "facebook/hubert-base-ls960",
            output_hidden_states=True,
        )
        self.model.eval()

        # Extract only the final_proj weights from the fairseq checkpoint.
        # We only need two small tensors — no fairseq import required.
        ckpt = torch.load(model_path, map_location="cpu")
        state = ckpt.get("model", ckpt)
        proj_w = state["final_proj.weight"].float()   # shape (256, 768)
        proj_b = state["final_proj.bias"].float()     # shape (256,)

        self.proj = nn.Linear(768, 256, bias=True)
        self.proj.weight = nn.Parameter(proj_w)
        self.proj.bias   = nn.Parameter(proj_b)
        self.proj.eval()

        if is_half:
            self.model = self.model.half()
            self.proj  = self.proj.half()
        self.model = self.model.to(device)
        self.proj  = self.proj.to(device)

    @torch.no_grad()
    def extract(self, audio: np.ndarray) -> np.ndarray:
        """
        audio: float32 numpy array at 16 kHz
        returns: (T, 256) float32
        """
        inputs = self.processor(
            audio,
            sampling_rate=HUBERT_SAMPLE_RATE,
            return_tensors="pt",
            padding=True,
        )
        input_values = inputs.input_values
        if self.is_half:
            input_values = input_values.half()
        input_values = input_values.to(self.device)

        outputs = self.model(input_values, output_hidden_states=True)
        # Layer 9 matches original RVC's output_layer=9 from fairseq
        hidden = outputs.hidden_states[9]          # (1, T, 768)
        feats  = self.proj(hidden.squeeze(0))      # (T, 256)
        return feats.float().cpu().numpy()


# ──────────────────────────────────────────────────────────────────────────────
# FAISS index builder from reference audio
# ──────────────────────────────────────────────────────────────────────────────

class ReferenceIndex:
    """
    Builds a FAISS flat-L2 index from HuBERT features of the reference voice.
    During inference, source features are blended with their k-NN in the
    reference space — exactly the RVC retrieval mechanism.
    """

    def __init__(self, feature_dim: int = 256):
        self.dim = feature_dim
        self.index: Optional[faiss.Index] = None
        self.features: Optional[np.ndarray] = None

    def build(self, ref_features: np.ndarray):
        """ref_features: (N, dim) float32"""
        ref_features = ref_features.astype(np.float32)
        self.features = ref_features
        n = ref_features.shape[0]
        if n > 2000:
            # Use IVF for large indices
            quantizer = faiss.IndexFlatL2(self.dim)
            nlist = min(int(np.sqrt(n)), 128)
            self.index = faiss.IndexIVFFlat(quantizer, self.dim, nlist)
            self.index.train(ref_features)
            self.index.nprobe = min(32, nlist)
        else:
            self.index = faiss.IndexFlatL2(self.dim)
        self.index.add(ref_features)
        logger.info("Reference index built with %d vectors", n)

    def blend(self, src_features: np.ndarray, ratio: float = 0.75, k: int = 8) -> np.ndarray:
        """
        Blend source features with k-NN from reference.
        ratio=1.0 → 100 % reference, 0.0 → source unchanged.
        """
        if self.index is None or ratio == 0.0:
            return src_features
        src_f32 = src_features.astype(np.float32)
        _, indices = self.index.search(src_f32, k)
        blended = np.zeros_like(src_f32)
        for i, idx_row in enumerate(indices):
            nn_vecs = self.features[idx_row]
            blended[i] = nn_vecs.mean(axis=0)
        return src_f32 * (1.0 - ratio) + blended * ratio


# ──────────────────────────────────────────────────────────────────────────────
# Main inference class
# ──────────────────────────────────────────────────────────────────────────────

class RVCInference:
    """
    End-to-end RVC voice conversion pipeline.

    Parameters
    ----------
    model_path  : Path to the .pth RVC voice model
    hubert_path : Path to the HuBERT base model (fairseq checkpoint)
    rmvpe_path  : Path to the RMVPE pitch model (optional, falls back to harvest)
    device      : 'cuda' or 'cpu'
    is_half     : Use float16 for reduced VRAM (recommended on 4 GB cards)
    """

    def __init__(
        self,
        model_path: str,
        hubert_path: str,
        rmvpe_path: Optional[str] = None,
        device: str = "cuda",
        is_half: bool = True,
    ):
        self.device = device
        self.is_half = is_half and (device == "cuda")
        self.model_path = model_path

        logger.info("Loading HuBERT …")
        self.hubert = HubertFeatureExtractor(hubert_path, device=device, is_half=self.is_half)

        logger.info("Loading pitch extractor …")
        if rmvpe_path and os.path.exists(rmvpe_path):
            try:
                self.f0_extractor = RMVPEPitchExtractor(rmvpe_path, device=device, is_half=self.is_half)
                self._use_rmvpe = True
            except Exception as e:
                logger.warning("RMVPE load failed (%s), falling back to harvest", e)
                self.f0_extractor = HarvestPitchExtractor()
                self._use_rmvpe = False
        else:
            self.f0_extractor = HarvestPitchExtractor()
            self._use_rmvpe = False

        logger.info("Loading RVC model from %s …", model_path)
        self.tgt_sr, self.net_g, self.vc = self._load_rvc_model(model_path)
        logger.info("RVC model loaded. Target SR: %d Hz", self.tgt_sr)

    # ──────────────────────────────────────────────────────────────────────
    # Model loading
    # ──────────────────────────────────────────────────────────────────────

    def _load_rvc_model(self, model_path: str):
        from infer_pack.models import SynthesizerTrnMs256NSFsid
        cpt = torch.load(model_path, map_location="cpu")
        tgt_sr = cpt["config"][-1]
        cpt["config"][-3] = cpt["weight"]["emb_g.weight"].shape[0]  # n_spk
        if_f0 = cpt.get("f0", 1)
        version = cpt.get("version", "v1")
        cfg = cpt["config"]

        net_g = SynthesizerTrnMs256NSFsid(*cfg, is_half=self.is_half)
        net_g.eval()
        net_g.load_state_dict(cpt["weight"], strict=False)
        if self.is_half:
            net_g = net_g.half()
        net_g = net_g.to(self.device)

        # Build a thin VC wrapper dict so inference logic is self-contained
        vc_config = {"if_f0": if_f0, "version": version}
        return tgt_sr, net_g, vc_config

    # ──────────────────────────────────────────────────────────────────────
    # Feature extraction helpers
    # ──────────────────────────────────────────────────────────────────────

    def _extract_features(self, audio: np.ndarray) -> np.ndarray:
        """Return HuBERT features (T, 256)."""
        audio_padded = pad_audio(audio, HUBERT_SAMPLE_RATE)
        feats = self.hubert.extract(audio_padded)
        return feats

    def _extract_f0(self, audio: np.ndarray, pitch_shift: int = 0) -> Tuple[np.ndarray, np.ndarray]:
        """Return (f0_coarse, f0_fine) arrays."""
        if self._use_rmvpe:
            f0 = self.f0_extractor.extract(audio, HUBERT_SAMPLE_RATE)
        else:
            f0 = self.f0_extractor.extract(audio, HUBERT_SAMPLE_RATE)

        if pitch_shift != 0:
            f0 = f0 * (2 ** (pitch_shift / 12.0))

        f0_coarse = f0_to_coarse(f0)
        return f0_coarse, f0.astype(np.float32)

    # ──────────────────────────────────────────────────────────────────────
    # Reference voice processing
    # ──────────────────────────────────────────────────────────────────────

    def build_reference_index(self, reference_audio_path: str) -> ReferenceIndex:
        """Extract features from reference audio and build FAISS index."""
        logger.info("Building reference index from %s", reference_audio_path)
        ref_audio = load_audio(reference_audio_path, HUBERT_SAMPLE_RATE)
        ref_feats = self._extract_features(ref_audio)
        ref_index = ReferenceIndex(feature_dim=ref_feats.shape[1])
        ref_index.build(ref_feats)
        return ref_index

    # ──────────────────────────────────────────────────────────────────────
    # Chunked inference (keeps VRAM ≤ 4 GB)
    # ──────────────────────────────────────────────────────────────────────

    def _infer_chunk(
        self,
        feats: np.ndarray,
        f0_coarse: np.ndarray,
        f0_fine: np.ndarray,
        sid: int = 0,
    ) -> np.ndarray:
        """Run one chunk through the network. Returns waveform numpy array."""
        dtype = torch.float16 if self.is_half else torch.float32

        phone = torch.from_numpy(feats).to(dtype=dtype, device=self.device).unsqueeze(0)
        phone_len = torch.LongTensor([feats.shape[0]]).to(self.device)
        pitch = torch.LongTensor(f0_coarse).to(self.device).unsqueeze(0)
        pitchf = torch.FloatTensor(f0_fine).to(dtype=dtype, device=self.device).unsqueeze(0)
        sid_tensor = torch.LongTensor([sid]).to(self.device)

        with torch.no_grad():
            audio_out, _, _ = self.net_g.infer(phone, phone_len, pitch, pitchf, sid_tensor)
        audio_np = audio_out[0, 0].float().cpu().numpy()
        return audio_np

    # ──────────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────────

    def convert(
        self,
        source_audio_path: str,
        reference_audio_path: str,
        output_path: str,
        pitch_shift: int = 0,
        index_ratio: float = 0.75,
        sid: int = 0,
        chunk_seconds: float = 15.0,
    ) -> str:
        """
        Convert source audio to the reference voice.

        Parameters
        ----------
        source_audio_path   : Path to the dry voiceover (any format).
        reference_audio_path: Path to the reference voice clip.
        output_path         : Where to write the converted WAV.
        pitch_shift         : Semitones (+/- 12 is an octave).
        index_ratio         : 0–1. How strongly to blend reference features.
        sid                 : Speaker ID in the model (usually 0).
        chunk_seconds       : Audio chunk size to keep VRAM bounded.

        Returns
        -------
        output_path on success.
        """
        # ── 1. Load source audio ──────────────────────────────────────────
        src_audio = load_audio(source_audio_path, HUBERT_SAMPLE_RATE)
        total_len = len(src_audio)
        logger.info("Source audio: %.2f s  (%d samples @ %d Hz)", total_len / HUBERT_SAMPLE_RATE, total_len, HUBERT_SAMPLE_RATE)

        # ── 2. Build reference index ──────────────────────────────────────
        ref_index = self.build_reference_index(reference_audio_path)

        # ── 3. Process in chunks ──────────────────────────────────────────
        chunk_samples = int(chunk_seconds * HUBERT_SAMPLE_RATE)
        overlap = int(0.05 * HUBERT_SAMPLE_RATE)  # 50 ms overlap for cross-fade
        out_chunks = []

        pos = 0
        while pos < total_len:
            end = min(pos + chunk_samples, total_len)
            chunk_audio = src_audio[pos:end]

            # Extract features
            feats = self._extract_features(chunk_audio)

            # Blend with reference
            feats = ref_index.blend(feats, ratio=index_ratio)

            # Extract pitch
            f0_coarse, f0_fine = self._extract_f0(chunk_audio, pitch_shift)

            # Align lengths (HuBERT and F0 may differ by 1-2 frames)
            min_len = min(feats.shape[0], f0_coarse.shape[0])
            feats = feats[:min_len]
            f0_coarse = f0_coarse[:min_len]
            f0_fine = f0_fine[:min_len]

            # Run inference
            chunk_out = self._infer_chunk(feats, f0_coarse, f0_fine, sid)
            out_chunks.append(chunk_out)

            # Free GPU cache after each chunk
            if self.device == "cuda":
                torch.cuda.empty_cache()
            pos = end

        # ── 4. Concatenate and cross-fade ─────────────────────────────────
        audio_out = self._crossfade_concat(out_chunks, overlap_samples=overlap)

        # ── 5. Resample to target SR if needed ────────────────────────────
        if self.tgt_sr != HUBERT_SAMPLE_RATE:
            audio_out = librosa.resample(audio_out, orig_sr=HUBERT_SAMPLE_RATE, target_sr=self.tgt_sr)

        # ── 6. Write output ───────────────────────────────────────────────
        audio_out = np.clip(audio_out, -1.0, 1.0)
        sf.write(output_path, audio_out, self.tgt_sr, subtype="PCM_16")
        logger.info("Saved converted audio to %s", output_path)
        return output_path

    @staticmethod
    def _crossfade_concat(chunks: list, overlap_samples: int = 800) -> np.ndarray:
        if len(chunks) == 1:
            return chunks[0]
        result = chunks[0]
        fade_out = np.linspace(1.0, 0.0, overlap_samples)
        fade_in = np.linspace(0.0, 1.0, overlap_samples)
        for chunk in chunks[1:]:
            if len(result) >= overlap_samples and len(chunk) >= overlap_samples:
                result[-overlap_samples:] *= fade_out
                chunk_copy = chunk.copy()
                chunk_copy[:overlap_samples] *= fade_in
                result = np.concatenate([result[:-overlap_samples], result[-overlap_samples:] + chunk_copy[:overlap_samples], chunk_copy[overlap_samples:]])
            else:
                result = np.concatenate([result, chunk])
        return result
