from __future__ import annotations
import logging
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from dateutil.parser import parse as parse_date

from database import get_db
from models import MediaItem, Tag
from schemas import MediaDetail, MediaSummary
from services.storage import get_file_type, is_allowed, save_upload, delete_file
from services.transcription import enqueue_transcription

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/media", tags=["media"])


def _get_or_create_tags(db: Session, names: list[str]) -> list[Tag]:
    tags = []
    for name in names:
        name = name.strip().lower()
        if not name:
            continue
        tag = db.query(Tag).filter(Tag.name == name).first()
        if not tag:
            tag = Tag(name=name)
            db.add(tag)
        tags.append(tag)
    return tags


@router.post("/upload", response_model=MediaSummary, status_code=status.HTTP_201_CREATED)
async def upload_media(
    file: UploadFile = File(...),
    origin_date: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),  # comma-separated
    db: Session = Depends(get_db),
):
    if not is_allowed(file.filename):
        raise HTTPException(400, "Unsupported file type.")

    stored_name, file_path, file_size = await save_upload(file)
    file_type = get_file_type(file.filename, file.content_type)

    parsed_origin = None
    if origin_date:
        try:
            parsed_origin = parse_date(origin_date).replace(tzinfo=timezone.utc)
        except Exception:
            raise HTTPException(400, "Invalid origin_date format.")

    tag_names = [t for t in (tags or "").split(",") if t.strip()]
    tag_objs = _get_or_create_tags(db, tag_names)

    item = MediaItem(
        filename=stored_name,
        original_filename=file.filename,
        file_path=file_path,
        file_type=file_type,
        mime_type=file.content_type,
        file_size=file_size,
        origin_date=parsed_origin,
        tags=tag_objs,
    )
    db.add(item)
    db.commit()
    db.refresh(item)

    await enqueue_transcription(item.id, file_path)
    return item


@router.get("", response_model=list[MediaSummary])
def list_media(
    sort_by: str = "upload_date",
    sort_dir: str = "desc",
    file_type: Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = db.query(MediaItem)
    if file_type in ("audio", "video"):
        q = q.filter(MediaItem.file_type == file_type)

    sort_col = {
        "upload_date": MediaItem.upload_date,
        "origin_date": MediaItem.origin_date,
        "filename": MediaItem.original_filename,
        "duration": MediaItem.duration,
    }.get(sort_by, MediaItem.upload_date)

    q = q.order_by(sort_col.desc() if sort_dir == "desc" else sort_col.asc())
    return q.all()


@router.get("/{media_id}", response_model=MediaDetail)
def get_media(media_id: str, db: Session = Depends(get_db)):
    item = db.get(MediaItem, media_id)
    if not item:
        raise HTTPException(404, "Media not found.")
    return item


@router.patch("/{media_id}", response_model=MediaSummary)
def update_media(
    media_id: str,
    origin_date: Optional[str] = None,
    tags: Optional[str] = None,
    db: Session = Depends(get_db),
):
    item = db.get(MediaItem, media_id)
    if not item:
        raise HTTPException(404, "Media not found.")

    if origin_date is not None:
        try:
            item.origin_date = parse_date(origin_date).replace(tzinfo=timezone.utc)
        except Exception:
            raise HTTPException(400, "Invalid origin_date format.")

    if tags is not None:
        tag_names = [t for t in tags.split(",") if t.strip()]
        item.tags = _get_or_create_tags(db, tag_names)

    db.commit()
    db.refresh(item)
    return item


@router.delete("/{media_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_media(media_id: str, db: Session = Depends(get_db)):
    item = db.get(MediaItem, media_id)
    if not item:
        raise HTTPException(404, "Media not found.")
    delete_file(item.file_path)
    db.delete(item)
    db.commit()


@router.get("/{media_id}/file")
def serve_file(media_id: str, db: Session = Depends(get_db)):
    item = db.get(MediaItem, media_id)
    if not item:
        raise HTTPException(404, "Media not found.")
    return FileResponse(
        item.file_path,
        media_type=item.mime_type or "application/octet-stream",
        filename=item.original_filename,
    )
