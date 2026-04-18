import subprocess
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def extract_clip(input_path: str, output_path: str, start: float, end: float) -> str:
    """Use ffmpeg to cut a segment. Returns output_path on success."""
    duration = end - start
    if duration <= 0:
        raise ValueError(f"Invalid clip range: {start} → {end}")

    ext = Path(output_path).suffix.lower()
    # For audio-only clips keep audio codec; for video use copy streams where possible.
    cmd = [
        "ffmpeg", "-y",
        "-ss", str(start),
        "-i", input_path,
        "-t", str(duration),
        "-c", "copy",        # stream copy is fast and lossless
        "-avoid_negative_ts", "make_zero",
        output_path,
    ]

    logger.info("Extracting clip: %s", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg error:\n{result.stderr}")
    return output_path
