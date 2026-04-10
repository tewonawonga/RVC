"""
Download required model files for the RVC voice conversion app.

Models downloaded:
  1. hubert_base.pt  — fairseq HuBERT (content encoder)
  2. rmvpe.pt        — RMVPE pitch extractor
  3. rvc_model.pth   — Pretrained RVC v2 voice model (ryansano/rvc-pretrained)
"""

import hashlib
import os
import sys
from pathlib import Path

MODELS_DIR = Path(__file__).parent / "models"
MODELS_DIR.mkdir(exist_ok=True)


def download_file(url: str, dest: Path, expected_md5: str = None):
    """Download url to dest with a progress bar, optionally verify MD5."""
    import urllib.request

    if dest.exists():
        if expected_md5:
            md5 = hashlib.md5(dest.read_bytes()).hexdigest()
            if md5 == expected_md5:
                print(f"  [skip] {dest.name} already present and verified.")
                return
            else:
                print(f"  [re-download] {dest.name} MD5 mismatch, re-downloading…")
        else:
            print(f"  [skip] {dest.name} already present.")
            return

    print(f"  Downloading {dest.name} …")
    tmp = dest.with_suffix(".tmp")

    def reporthook(block, block_size, total):
        done = block * block_size
        if total > 0:
            pct = min(100, done * 100 // total)
            mb_done = done / 1e6
            mb_total = total / 1e6
            print(f"\r    {pct:3d}%  {mb_done:.1f}/{mb_total:.1f} MB", end="", flush=True)

    try:
        urllib.request.urlretrieve(url, tmp, reporthook)
        print()
        tmp.rename(dest)
    except Exception as e:
        tmp.unlink(missing_ok=True)
        raise RuntimeError(f"Failed to download {url}: {e}") from e

    if expected_md5:
        md5 = hashlib.md5(dest.read_bytes()).hexdigest()
        if md5 != expected_md5:
            dest.unlink()
            raise RuntimeError(f"MD5 mismatch for {dest.name} (got {md5}, expected {expected_md5})")


def download_hf(repo_id: str, filename: str, dest: Path, revision: str = "main"):
    """Download a file from Hugging Face Hub."""
    try:
        from huggingface_hub import hf_hub_download
        if dest.exists():
            print(f"  [skip] {dest.name} already present.")
            return
        print(f"  Downloading {filename} from {repo_id} …")
        local = hf_hub_download(repo_id=repo_id, filename=filename, revision=revision)
        import shutil
        shutil.copy(local, dest)
        print(f"  Saved to {dest}")
    except Exception as e:
        raise RuntimeError(f"HuggingFace download failed for {repo_id}/{filename}: {e}") from e


# ──────────────────────────────────────────────────────────────────────────────
# Model download specs
# ──────────────────────────────────────────────────────────────────────────────

HUBERT_URL = (
    "https://huggingface.co/lj1995/VoiceConversionWebUI/resolve/main/hubert_base.pt"
)
RMVPE_URL = (
    "https://huggingface.co/lj1995/VoiceConversionWebUI/resolve/main/rmvpe.pt"
)
# Pretrained RVC v2 model (40k, nsff0) hosted on HuggingFace
RVC_MODEL_HF_REPO = "lj1995/VoiceConversionWebUI"
RVC_MODEL_HF_FILE = "pretrained_v2/f0G40k.pth"


def main():
    print("=" * 60)
    print("RVC Model Downloader")
    print("=" * 60)

    # 1. HuBERT
    print("\n[1/3] HuBERT base model (fairseq)")
    download_file(HUBERT_URL, MODELS_DIR / "hubert_base.pt")

    # 2. RMVPE pitch extractor
    print("\n[2/3] RMVPE pitch extractor")
    download_file(RMVPE_URL, MODELS_DIR / "rmvpe.pt")

    # 3. RVC pretrained model
    print("\n[3/3] RVC pretrained v2 model (f0G40k)")
    dest = MODELS_DIR / "rvc_model.pth"
    if dest.exists():
        print(f"  [skip] {dest.name} already present.")
    else:
        try:
            download_hf(RVC_MODEL_HF_REPO, RVC_MODEL_HF_FILE, dest)
        except Exception as e:
            # Fallback: direct URL
            fallback_url = (
                "https://huggingface.co/lj1995/VoiceConversionWebUI/resolve/main/"
                "pretrained_v2/f0G40k.pth"
            )
            print(f"  HF Hub download failed ({e}), trying direct URL…")
            download_file(fallback_url, dest)

    print("\n" + "=" * 60)
    print("All models downloaded successfully.")
    print(f"  Models directory: {MODELS_DIR.resolve()}")
    print("=" * 60)
    print("\nYou can now start the server:")
    print("  python app.py")
    print("  — or —")
    print("  uvicorn app:app --host 0.0.0.0 --port 7860\n")


if __name__ == "__main__":
    main()
