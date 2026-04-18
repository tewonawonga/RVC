import os
import shutil
import uuid
from pathlib import Path
from fastapi import UploadFile

UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "./uploads"))
CLIPS_DIR = Path(os.getenv("CLIPS_DIR", "./clips"))

ALLOWED_AUDIO = {".mp3", ".wav", ".flac", ".ogg", ".m4a", ".aac", ".opus", ".weba"}
ALLOWED_VIDEO = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v", ".wmv", ".flv"}
ALLOWED_EXTENSIONS = ALLOWED_AUDIO | ALLOWED_VIDEO

AUDIO_MIME_PREFIXES = {"audio/"}
VIDEO_MIME_PREFIXES = {"video/"}


def ensure_dirs():
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    CLIPS_DIR.mkdir(parents=True, exist_ok=True)


def get_file_type(filename: str, mime_type: str) -> str:
    ext = Path(filename).suffix.lower()
    if ext in ALLOWED_VIDEO or (mime_type and mime_type.startswith("video/")):
        return "video"
    return "audio"


def is_allowed(filename: str) -> bool:
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS


async def save_upload(file: UploadFile) -> tuple[str, str, int]:
    """Save upload to disk. Returns (stored_filename, file_path, file_size)."""
    ensure_dirs()
    ext = Path(file.filename).suffix.lower()
    stored_name = f"{uuid.uuid4()}{ext}"
    dest = UPLOAD_DIR / stored_name
    size = 0
    with dest.open("wb") as out:
        while chunk := await file.read(1024 * 1024):
            out.write(chunk)
            size += len(chunk)
    return stored_name, str(dest), size


def delete_file(file_path: str):
    try:
        Path(file_path).unlink(missing_ok=True)
    except Exception:
        pass


def clip_output_path(clip_id: str, ext: str = ".mp4") -> Path:
    ensure_dirs()
    return CLIPS_DIR / f"{clip_id}{ext}"
