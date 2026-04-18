# Media Library

A private team media library for audio and video files — search, transcribe, watch, and extract clips.

## Features

- Upload audio and video files (MP4, MOV, MP3, WAV, FLAC, and more)
- Auto-transcription via OpenAI Whisper (runs locally)
- Search by filename, transcript text, tags, origin date, or upload date
- Synchronized transcript viewer — click any line to jump to that point
- Clip extraction: mark start/end in the transcript, extract with FFmpeg
- Dark UI built with React + Tailwind CSS

## Requirements

- Python 3.10+
- Node.js 18+
- FFmpeg (for clip extraction)
- ~1 GB disk for Whisper base model

## Quick Start

```bash
chmod +x setup.sh && ./setup.sh
```

Then in two terminals:

```bash
# Terminal 1 — backend
cd backend && source .venv/bin/activate && uvicorn main:app --reload

# Terminal 2 — frontend dev server
cd frontend && npm run dev
```

Open http://localhost:5173

## Configuration

| Env var | Default | Description |
|---|---|---|
| `UPLOAD_DIR` | `./uploads` | Where uploaded files are stored |
| `CLIPS_DIR` | `./clips` | Where extracted clips are stored |
| `DATABASE_URL` | `sqlite:///./media_library.db` | Database connection string |

## Architecture

```
backend/         FastAPI app
  main.py        Entry point, mounts routes
  models.py      SQLAlchemy ORM models
  database.py    DB session + init (SQLite + FTS5)
  schemas.py     Pydantic response schemas
  routers/
    media.py     Upload, list, serve files
    search.py    Full-text + metadata search
    clips.py     Clip creation and download
  services/
    storage.py   File I/O helpers
    transcription.py  Whisper in thread pool
    clips.py     FFmpeg wrapper

frontend/        React + TypeScript + Vite
  src/
    components/
      LibraryPage      Grid view with search/filter
      MediaPage        Player + transcript layout
      MediaPlayer      HTML5 video/audio with controls
      TranscriptPanel  Synced transcript + clip editor
      UploadModal      Drag-and-drop upload form
      SearchFilters    Date range + tag filters
```
