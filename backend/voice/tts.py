"""Text-to-speech powered by edge-tts (fully async)."""
from __future__ import annotations

import os
import tempfile
from typing import AsyncIterator, Optional

import edge_tts

from config import settings


async def stream_speech(
    text: str, voice: Optional[str] = None
) -> AsyncIterator[bytes]:
    """Yield MP3 audio chunks for ``text`` as they are produced."""
    if not text or not text.strip():
        return
    communicator = edge_tts.Communicate(text=text, voice=voice or settings.tts_voice)
    async for chunk in communicator.stream():
        if chunk.get("type") == "audio":
            yield chunk["data"]


async def synthesize_to_file(
    text: str,
    out_path: Optional[str] = None,
    voice: Optional[str] = None,
) -> str:
    """Synthesise ``text`` to an MP3 file and return its path."""
    if not text or not text.strip():
        raise ValueError("text must not be empty")

    if out_path is None:
        fd, out_path = tempfile.mkstemp(suffix=".mp3", prefix="tts_")
        os.close(fd)

    communicator = edge_tts.Communicate(text=text, voice=voice or settings.tts_voice)
    await communicator.save(out_path)
    return out_path


async def synthesize_to_bytes(text: str, voice: Optional[str] = None) -> bytes:
    """Synthesise ``text`` and return the full MP3 payload in memory."""
    chunks: list[bytes] = []
    async for chunk in stream_speech(text, voice=voice):
        chunks.append(chunk)
    return b"".join(chunks)
