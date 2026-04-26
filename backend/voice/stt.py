"""Speech-to-text powered by faster-whisper.

The model is loaded lazily on first use and the synchronous ``transcribe``
call is dispatched to a thread pool so the FastAPI event loop is never
blocked. The returned text is the full concatenated transcript.
"""
from __future__ import annotations

import asyncio
import os
import tempfile
from functools import lru_cache
from typing import Optional

from config import settings


@lru_cache(maxsize=1)
def _load_model():
    """Import and instantiate the whisper model on first use."""
    # Imported here so the FastAPI startup is not slowed down by a heavy
    # native library when STT is never actually used.
    from faster_whisper import WhisperModel  # type: ignore

    return WhisperModel(
        settings.whisper_model,
        device=settings.whisper_device,
        compute_type=settings.whisper_compute_type,
    )


def _transcribe_blocking(audio_path: str, language: Optional[str]) -> str:
    model = _load_model()
    segments, _info = model.transcribe(
        audio_path,
        language=language,
        vad_filter=True,
        beam_size=5,
    )
    return " ".join(segment.text.strip() for segment in segments).strip()


async def transcribe_file(audio_path: str, language: Optional[str] = None) -> str:
    """Transcribe an audio file asynchronously.

    Parameters
    ----------
    audio_path:
        Path to a wav/mp3/m4a/ogg/flac file readable by ffmpeg.
    language:
        Optional ISO-639-1 language hint (e.g. ``"en"``). ``None`` triggers
        auto-detection.
    """
    if not audio_path or not os.path.exists(audio_path):
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        None, _transcribe_blocking, audio_path, language
    )


async def transcribe_bytes(
    audio_bytes: bytes, suffix: str = ".wav", language: Optional[str] = None
) -> str:
    """Transcribe raw audio bytes by spilling them to a temp file first."""
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as fh:
        fh.write(audio_bytes)
        tmp_path = fh.name
    try:
        return await transcribe_file(tmp_path, language=language)
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
