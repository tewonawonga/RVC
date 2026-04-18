import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, Integer, DateTime, ForeignKey, Table, Text
from sqlalchemy.orm import relationship
from database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


media_tags = Table(
    "media_tags",
    Base.metadata,
    Column("media_id", String, ForeignKey("media_items.id", ondelete="CASCADE")),
    Column("tag_id", Integer, ForeignKey("tags.id", ondelete="CASCADE")),
)


class Tag(Base):
    __tablename__ = "tags"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    media_items = relationship("MediaItem", secondary=media_tags, back_populates="tags")


class MediaItem(Base):
    __tablename__ = "media_items"
    id = Column(String(36), primary_key=True, default=_uuid)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_type = Column(String(10), nullable=False)  # "audio" | "video"
    mime_type = Column(String(100))
    file_size = Column(Integer)
    duration = Column(Float, nullable=True)
    origin_date = Column(DateTime(timezone=True), nullable=True)
    upload_date = Column(DateTime(timezone=True), default=_now)
    transcription_status = Column(String(20), default="pending")  # pending|processing|complete|failed
    transcription_error = Column(Text, nullable=True)

    tags = relationship("Tag", secondary=media_tags, back_populates="media_items")
    transcript_segments = relationship(
        "TranscriptSegment", back_populates="media_item",
        cascade="all, delete-orphan", order_by="TranscriptSegment.segment_index"
    )
    clips = relationship("Clip", back_populates="media_item", cascade="all, delete-orphan")


class TranscriptSegment(Base):
    __tablename__ = "transcript_segments"
    id = Column(Integer, primary_key=True, autoincrement=True)
    media_id = Column(String(36), ForeignKey("media_items.id", ondelete="CASCADE"), nullable=False, index=True)
    segment_index = Column(Integer, nullable=False)
    start_time = Column(Float, nullable=False)
    end_time = Column(Float, nullable=False)
    text = Column(Text, nullable=False)
    media_item = relationship("MediaItem", back_populates="transcript_segments")


class Clip(Base):
    __tablename__ = "clips"
    id = Column(String(36), primary_key=True, default=_uuid)
    media_id = Column(String(36), ForeignKey("media_items.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    start_time = Column(Float, nullable=False)
    end_time = Column(Float, nullable=False)
    file_path = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now)
    media_item = relationship("MediaItem", back_populates="clips")
