from __future__ import annotations
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class TagOut(BaseModel):
    id: int
    name: str
    model_config = {"from_attributes": True}


class SegmentOut(BaseModel):
    id: int
    segment_index: int
    start_time: float
    end_time: float
    text: str
    model_config = {"from_attributes": True}


class MediaSummary(BaseModel):
    id: str
    filename: str
    original_filename: str
    file_type: str
    mime_type: Optional[str]
    file_size: Optional[int]
    duration: Optional[float]
    origin_date: Optional[datetime]
    upload_date: datetime
    transcription_status: str
    tags: list[TagOut]
    model_config = {"from_attributes": True}


class MediaDetail(MediaSummary):
    transcript_segments: list[SegmentOut]


class ClipOut(BaseModel):
    id: str
    media_id: str
    title: str
    start_time: float
    end_time: float
    file_path: Optional[str]
    created_at: datetime
    model_config = {"from_attributes": True}


class ClipCreate(BaseModel):
    media_id: str
    title: str
    start_time: float
    end_time: float
