"""FastAPI entrypoint for the desktop voice assistant.

Run with::

    uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000

All endpoints are async. Heavy / blocking work (subprocess, faster-whisper,
file IO) is dispatched to the default executor via ``run_in_executor``.
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

# Ensure ``import config`` works when running as ``uvicorn backend.main:app``
# from the project root.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import FastAPI, File, Form, HTTPException, UploadFile  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import StreamingResponse  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402

from config import settings  # noqa: E402

from .agent import run_agent  # noqa: E402
from .memory import memory  # noqa: E402
from .voice.stt import transcribe_bytes  # noqa: E402
from .voice.tts import stream_speech  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("voice-assistant")

app = FastAPI(title="Personal Voice Assistant", version="1.0.0")

# Streamlit runs on its own port; allow it to call us during local dev.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    session_id: str = Field(default="default", max_length=64)


class ChatResponse(BaseModel):
    reply: str
    session_id: str


class HistoryResponse(BaseModel):
    session_id: str
    messages: list[dict]


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "model": settings.mistral_model,
        "has_api_key": bool(settings.mistral_api_key),
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    try:
        reply = await run_agent(req.session_id, req.message)
    except RuntimeError as exc:
        # Most commonly: missing GOOGLE_API_KEY.
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        log.exception("Agent invocation failed")
        raise HTTPException(status_code=500, detail=f"Agent error: {exc}") from exc
    return ChatResponse(reply=reply, session_id=req.session_id)


@app.get("/history/{session_id}", response_model=HistoryResponse)
async def history(session_id: str) -> HistoryResponse:
    msgs = [
        {"role": getattr(m, "type", "unknown"), "content": m.content}
        for m in memory.history(session_id)
    ]
    return HistoryResponse(session_id=session_id, messages=msgs)


@app.delete("/history/{session_id}")
async def clear_history(session_id: str) -> dict:
    memory.clear(session_id)
    return {"status": "cleared", "session_id": session_id}


@app.post("/voice/transcribe")
async def transcribe(
    file: UploadFile = File(...),
    language: str | None = Form(default=None),
) -> dict:
    """Accept an audio upload and return the transcribed text."""
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty audio upload.")
    suffix = Path(file.filename or "audio.wav").suffix or ".wav"
    try:
        text = await transcribe_bytes(data, suffix=suffix, language=language)
    except Exception as exc:  # noqa: BLE001
        log.exception("STT failed")
        raise HTTPException(status_code=500, detail=f"STT error: {exc}") from exc
    return {"text": text}


@app.get("/voice/speak")
async def speak(text: str, voice: str | None = None) -> StreamingResponse:
    """Stream an MP3 of the synthesised speech for ``text``."""
    if not text.strip():
        raise HTTPException(status_code=400, detail="text query param is required.")

    async def generator():
        try:
            async for chunk in stream_speech(text, voice=voice):
                yield chunk
        except Exception as exc:  # noqa: BLE001
            log.exception("TTS failed")
            raise HTTPException(status_code=500, detail=f"TTS error: {exc}") from exc

    return StreamingResponse(generator(), media_type="audio/mpeg")
