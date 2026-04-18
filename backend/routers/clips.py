from __future__ import annotations
import logging
from pathlib import Path
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from database import get_db
from models import Clip, MediaItem
from schemas import ClipCreate, ClipOut
from services.clips import extract_clip
from services.storage import clip_output_path

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/clips", tags=["clips"])


def _do_extract(clip_id: str, input_path: str, output_path: str, start: float, end: float):
    db = None
    try:
        from database import SessionLocal
        db = SessionLocal()
        clip = db.get(Clip, clip_id)
        if not clip:
            return
        extract_clip(input_path, str(output_path), start, end)
        clip.file_path = str(output_path)
        db.commit()
        logger.info("Clip ready: %s", output_path)
    except Exception as exc:
        logger.exception("Clip extraction failed for %s", clip_id)
        if db:
            db.rollback()
    finally:
        if db:
            db.close()


@router.post("", response_model=ClipOut, status_code=status.HTTP_202_ACCEPTED)
def create_clip(
    payload: ClipCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    item = db.get(MediaItem, payload.media_id)
    if not item:
        raise HTTPException(404, "Media not found.")
    if payload.end_time <= payload.start_time:
        raise HTTPException(400, "end_time must be after start_time.")

    ext = Path(item.file_path).suffix.lower() or ".mp4"
    clip = Clip(
        media_id=payload.media_id,
        title=payload.title,
        start_time=payload.start_time,
        end_time=payload.end_time,
    )
    db.add(clip)
    db.commit()
    db.refresh(clip)

    out_path = clip_output_path(clip.id, ext)
    background_tasks.add_task(_do_extract, clip.id, item.file_path, str(out_path), payload.start_time, payload.end_time)
    return clip


@router.get("", response_model=list[ClipOut])
def list_clips(media_id: str | None = None, db: Session = Depends(get_db)):
    q = db.query(Clip).order_by(Clip.created_at.desc())
    if media_id:
        q = q.filter(Clip.media_id == media_id)
    return q.all()


@router.get("/{clip_id}", response_model=ClipOut)
def get_clip(clip_id: str, db: Session = Depends(get_db)):
    clip = db.get(Clip, clip_id)
    if not clip:
        raise HTTPException(404, "Clip not found.")
    return clip


@router.get("/{clip_id}/download")
def download_clip(clip_id: str, db: Session = Depends(get_db)):
    clip = db.get(Clip, clip_id)
    if not clip:
        raise HTTPException(404, "Clip not found.")
    if not clip.file_path or not Path(clip.file_path).exists():
        raise HTTPException(425, "Clip is still being processed.")
    filename = f"{clip.title}{Path(clip.file_path).suffix}"
    return FileResponse(clip.file_path, filename=filename)


@router.delete("/{clip_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_clip(clip_id: str, db: Session = Depends(get_db)):
    clip = db.get(Clip, clip_id)
    if not clip:
        raise HTTPException(404, "Clip not found.")
    if clip.file_path:
        Path(clip.file_path).unlink(missing_ok=True)
    db.delete(clip)
    db.commit()
