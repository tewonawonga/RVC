from __future__ import annotations
from datetime import timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from dateutil.parser import parse as parse_date

from database import get_db
from models import MediaItem, Tag
from schemas import MediaSummary

router = APIRouter(prefix="/api/search", tags=["search"])


@router.get("", response_model=list[MediaSummary])
def search(
    q: Optional[str] = None,
    tags: Optional[str] = None,
    origin_from: Optional[str] = None,
    origin_to: Optional[str] = None,
    upload_from: Optional[str] = None,
    upload_to: Optional[str] = None,
    file_type: Optional[str] = None,
    sort_by: str = "upload_date",
    sort_dir: str = "desc",
    db: Session = Depends(get_db),
):
    query = db.query(MediaItem)

    if file_type in ("audio", "video"):
        query = query.filter(MediaItem.file_type == file_type)

    if origin_from:
        try:
            dt = parse_date(origin_from).replace(tzinfo=timezone.utc)
            query = query.filter(MediaItem.origin_date >= dt)
        except Exception:
            raise HTTPException(400, "Invalid origin_from.")

    if origin_to:
        try:
            dt = parse_date(origin_to).replace(tzinfo=timezone.utc)
            query = query.filter(MediaItem.origin_date <= dt)
        except Exception:
            raise HTTPException(400, "Invalid origin_to.")

    if upload_from:
        try:
            dt = parse_date(upload_from).replace(tzinfo=timezone.utc)
            query = query.filter(MediaItem.upload_date >= dt)
        except Exception:
            raise HTTPException(400, "Invalid upload_from.")

    if upload_to:
        try:
            dt = parse_date(upload_to).replace(tzinfo=timezone.utc)
            query = query.filter(MediaItem.upload_date <= dt)
        except Exception:
            raise HTTPException(400, "Invalid upload_to.")

    if tags:
        tag_list = [t.strip().lower() for t in tags.split(",") if t.strip()]
        for tag_name in tag_list:
            query = query.filter(MediaItem.tags.any(Tag.name == tag_name))

    # Text search: filename + transcript FTS
    if q:
        q_lower = f"%{q.lower()}%"
        from sqlalchemy import text as sa_text
        fts_ids = db.execute(
            sa_text("SELECT DISTINCT media_id FROM transcript_fts WHERE text MATCH :q"),
            {"q": q},
        ).scalars().all()

        query = query.filter(
            or_(
                MediaItem.original_filename.ilike(q_lower),
                MediaItem.id.in_(fts_ids),
            )
        )

    sort_col = {
        "upload_date": MediaItem.upload_date,
        "origin_date": MediaItem.origin_date,
        "filename": MediaItem.original_filename,
        "duration": MediaItem.duration,
    }.get(sort_by, MediaItem.upload_date)

    query = query.order_by(sort_col.desc() if sort_dir == "desc" else sort_col.asc())
    return query.all()


@router.get("/tags", response_model=list[str])
def list_tags(db: Session = Depends(get_db)):
    return [t.name for t in db.query(Tag).order_by(Tag.name).all()]
