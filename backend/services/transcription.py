import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy.orm import Session
from database import SessionLocal
from models import MediaItem, TranscriptSegment

logger = logging.getLogger(__name__)
_executor = ThreadPoolExecutor(max_workers=2)
_whisper_model = None
WHISPER_MODEL_SIZE = "base"


def _load_model():
    global _whisper_model
    if _whisper_model is None:
        import whisper
        logger.info("Loading Whisper model '%s'…", WHISPER_MODEL_SIZE)
        _whisper_model = whisper.load_model(WHISPER_MODEL_SIZE)
        logger.info("Whisper model loaded.")
    return _whisper_model


def _transcribe_sync(media_id: str, file_path: str):
    db: Session = SessionLocal()
    try:
        item = db.get(MediaItem, media_id)
        if not item:
            return
        item.transcription_status = "processing"
        db.commit()

        model = _load_model()
        result = model.transcribe(file_path, verbose=False)

        db.query(TranscriptSegment).filter(TranscriptSegment.media_id == media_id).delete()
        segments = []
        for i, seg in enumerate(result.get("segments", [])):
            segments.append(TranscriptSegment(
                media_id=media_id,
                segment_index=i,
                start_time=seg["start"],
                end_time=seg["end"],
                text=seg["text"].strip(),
            ))
        db.bulk_save_objects(segments)

        _index_fts(db, media_id, segments)

        item.transcription_status = "complete"
        db.commit()
        logger.info("Transcription complete for %s (%d segments)", media_id, len(segments))
    except Exception as exc:
        logger.exception("Transcription failed for %s", media_id)
        db.rollback()
        item = db.get(MediaItem, media_id)
        if item:
            item.transcription_status = "failed"
            item.transcription_error = str(exc)
            db.commit()
    finally:
        db.close()


def _index_fts(db: Session, media_id: str, segments: list[TranscriptSegment]):
    try:
        from sqlalchemy import text
        db.execute(text("DELETE FROM transcript_fts WHERE media_id = :mid"), {"mid": media_id})
        for seg in segments:
            db.execute(
                text("INSERT INTO transcript_fts(media_id, text, segment_id) VALUES (:mid, :txt, :sid)"),
                {"mid": media_id, "txt": seg.text, "sid": seg.segment_index},
            )
    except Exception:
        logger.warning("FTS indexing failed (non-fatal)", exc_info=True)


async def enqueue_transcription(media_id: str, file_path: str):
    loop = asyncio.get_event_loop()
    loop.run_in_executor(_executor, _transcribe_sync, media_id, file_path)
