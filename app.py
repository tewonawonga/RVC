"""
RVC Voice Conversion Web Application
FastAPI backend — optimised for GTX 1650 SUPER (4 GB VRAM)
"""

import gc
import logging
import os
import threading
import uuid
from pathlib import Path
from typing import Dict

import torch
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Paths & configuration
# ──────────────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
UPLOADS_DIR = BASE_DIR / "uploads"
OUTPUTS_DIR = BASE_DIR / "outputs"
MODELS_DIR = BASE_DIR / "models"
STATIC_DIR = BASE_DIR / "static"

for d in (UPLOADS_DIR, OUTPUTS_DIR, MODELS_DIR):
    d.mkdir(exist_ok=True)

HUBERT_PATH = MODELS_DIR / "hubert_base.pt"
RMVPE_PATH = MODELS_DIR / "rmvpe.pt"
RVC_MODEL_PATH = MODELS_DIR / "rvc_model.pth"

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
IS_HALF = (DEVICE == "cuda")

# ──────────────────────────────────────────────────────────────────────────────
# Job state
# ──────────────────────────────────────────────────────────────────────────────
# job_id -> {"status": "pending"|"running"|"done"|"error", "message": str, "output": str|None}
jobs: Dict[str, dict] = {}
jobs_lock = threading.Lock()

# ──────────────────────────────────────────────────────────────────────────────
# Lazy model loader (avoids loading at startup if models not yet downloaded)
# ──────────────────────────────────────────────────────────────────────────────
_rvc: "RVCInference | None" = None
_rvc_lock = threading.Lock()


def get_rvc():
    global _rvc
    with _rvc_lock:
        if _rvc is not None:
            return _rvc
        if not RVC_MODEL_PATH.exists():
            raise RuntimeError(
                "RVC model not found. Run `python download_models.py` first."
            )
        if not HUBERT_PATH.exists():
            raise RuntimeError(
                "HuBERT model not found. Run `python download_models.py` first."
            )
        from rvc_infer import RVCInference
        _rvc = RVCInference(
            model_path=str(RVC_MODEL_PATH),
            hubert_path=str(HUBERT_PATH),
            rmvpe_path=str(RMVPE_PATH) if RMVPE_PATH.exists() else None,
            device=DEVICE,
            is_half=IS_HALF,
        )
        return _rvc


# ──────────────────────────────────────────────────────────────────────────────
# Background worker
# ──────────────────────────────────────────────────────────────────────────────

def _run_conversion(
    job_id: str,
    source_path: str,
    reference_path: str,
    pitch_shift: int,
    index_ratio: float,
):
    with jobs_lock:
        jobs[job_id]["status"] = "running"
        jobs[job_id]["message"] = "Converting…"

    output_path = str(OUTPUTS_DIR / f"{job_id}.wav")
    try:
        rvc = get_rvc()
        rvc.convert(
            source_audio_path=source_path,
            reference_audio_path=reference_path,
            output_path=output_path,
            pitch_shift=pitch_shift,
            index_ratio=index_ratio,
        )
        with jobs_lock:
            jobs[job_id]["status"] = "done"
            jobs[job_id]["message"] = "Conversion complete."
            jobs[job_id]["output"] = output_path
    except Exception as exc:
        logger.exception("Job %s failed", job_id)
        with jobs_lock:
            jobs[job_id]["status"] = "error"
            jobs[job_id]["message"] = str(exc)
    finally:
        # Clean up uploaded files
        for p in (source_path, reference_path):
            try:
                os.remove(p)
            except OSError:
                pass
        # Release GPU memory
        if DEVICE == "cuda":
            torch.cuda.empty_cache()
        gc.collect()


# ──────────────────────────────────────────────────────────────────────────────
# FastAPI app
# ──────────────────────────────────────────────────────────────────────────────
app = FastAPI(title="RVC Voice Conversion", version="1.0.0")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", response_class=HTMLResponse)
async def root():
    html_path = STATIC_DIR / "index.html"
    return HTMLResponse(content=html_path.read_text(), status_code=200)


@app.post("/api/convert")
async def api_convert(
    voiceover: UploadFile = File(..., description="Dry voiceover recording"),
    reference: UploadFile = File(..., description="Reference voice recording"),
    pitch_shift: int = Form(default=0, description="Pitch shift in semitones (-12 to +12)"),
    index_ratio: float = Form(default=0.75, description="Reference blend ratio (0–1)"),
):
    """Upload files and start an asynchronous voice conversion job."""
    # Validate pitch
    if not -24 <= pitch_shift <= 24:
        raise HTTPException(status_code=422, detail="pitch_shift must be between -24 and 24")
    if not 0.0 <= index_ratio <= 1.0:
        raise HTTPException(status_code=422, detail="index_ratio must be between 0 and 1")

    job_id = str(uuid.uuid4())

    # Save uploads
    src_path = str(UPLOADS_DIR / f"{job_id}_source{Path(voiceover.filename).suffix or '.wav'}")
    ref_path = str(UPLOADS_DIR / f"{job_id}_reference{Path(reference.filename).suffix or '.wav'}")

    with open(src_path, "wb") as f:
        f.write(await voiceover.read())
    with open(ref_path, "wb") as f:
        f.write(await reference.read())

    with jobs_lock:
        jobs[job_id] = {"status": "pending", "message": "Queued", "output": None}

    # Run in background thread so the HTTP response returns immediately
    t = threading.Thread(
        target=_run_conversion,
        args=(job_id, src_path, ref_path, pitch_shift, index_ratio),
        daemon=True,
    )
    t.start()

    return {"job_id": job_id, "status": "pending"}


@app.get("/api/status/{job_id}")
async def api_status(job_id: str):
    """Poll conversion job status."""
    with jobs_lock:
        job = jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"job_id": job_id, **job}


@app.get("/api/download/{job_id}")
async def api_download(job_id: str):
    """Download the converted audio file."""
    with jobs_lock:
        job = jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if job["status"] != "done":
        raise HTTPException(status_code=400, detail="Job not complete yet")
    output_path = job["output"]
    if not output_path or not os.path.exists(output_path):
        raise HTTPException(status_code=404, detail="Output file not found")
    return FileResponse(
        path=output_path,
        media_type="audio/wav",
        filename=f"converted_{job_id}.wav",
    )


@app.get("/api/health")
async def health():
    cuda_available = torch.cuda.is_available()
    vram_info = {}
    if cuda_available:
        dev = torch.cuda.current_device()
        total = torch.cuda.get_device_properties(dev).total_memory
        reserved = torch.cuda.memory_reserved(dev)
        allocated = torch.cuda.memory_allocated(dev)
        vram_info = {
            "device": torch.cuda.get_device_name(dev),
            "total_gb": round(total / 1e9, 2),
            "allocated_gb": round(allocated / 1e9, 2),
            "reserved_gb": round(reserved / 1e9, 2),
        }
    models_ready = RVC_MODEL_PATH.exists() and HUBERT_PATH.exists()
    return {
        "status": "ok",
        "device": DEVICE,
        "cuda": cuda_available,
        "vram": vram_info,
        "models_ready": models_ready,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=7860, reload=False, workers=1)
