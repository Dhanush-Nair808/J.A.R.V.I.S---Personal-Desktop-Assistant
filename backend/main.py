"""FastAPI entrypoint for the desktop voice assistant.

Run with::
    uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import FastAPI, File, Form, HTTPException, UploadFile, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from config import settings

from .agent import run_agent
from .memory import memory
from . import memory_sql
from .voice.stt import transcribe_bytes
from .voice.tts import stream_speech
 

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("voice-assistant")

app = FastAPI(title="Personal Voice Assistant", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ====================== YOUR ORIGINAL SCHEMAS & ROUTES (Unchanged) ======================
class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    session_id: str = Field(default="default", max_length=64)

class ChatResponse(BaseModel):
    reply: str
    session_id: str

class HistoryResponse(BaseModel):
    session_id: str
    messages: list[dict]

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
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        log.exception("Agent invocation failed")
        raise HTTPException(status_code=500, detail=f"Agent error: {exc}") from exc
    return ChatResponse(reply=reply, session_id=req.session_id)

@app.get("/sessions")
async def sessions() -> list[dict]:
    rows = memory_sql.list_sessions()
    return [
        {"session_id": row[0], "last_time": row[1]} for row in rows
    ]

@app.get("/history/{session_id}", response_model=HistoryResponse)
async def history(session_id: str) -> HistoryResponse:
    rows = memory_sql.get_full_history(session_id)
    msgs = [{"role": role, "content": content} for role, content in rows]
    return HistoryResponse(session_id=session_id, messages=msgs)

@app.delete("/history/{session_id}")
async def clear_history(session_id: str) -> dict:
    memory.clear(session_id)
    memory_sql.delete_session(session_id)
    return {"status": "cleared", "session_id": session_id}

@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str) -> dict:
    memory.clear(session_id)
    memory_sql.delete_session(session_id)
    return {"status": "deleted", "session_id": session_id}

@app.post("/voice/transcribe")
async def transcribe(
    file: UploadFile = File(...),
    language: str | None = Form(default=None),
) -> dict:
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty audio upload.")
    suffix = Path(file.filename or "audio.wav").suffix or ".wav"
    try:
        text = await transcribe_bytes(data, suffix=suffix, language=language)
    except Exception as exc:
        log.exception("STT failed")
        raise HTTPException(status_code=500, detail=f"STT error: {exc}") from exc
    return {"text": text}

@app.get("/voice/speak")
async def speak(text: str, voice: str | None = None) -> StreamingResponse:
    if not text.strip():
        raise HTTPException(status_code=400, detail="text query param is required.")

    async def generator():
        try:
            async for chunk in stream_speech(text, voice=voice):
                yield chunk
        except Exception as exc:
            log.exception("TTS failed")
            raise HTTPException(status_code=500, detail=f"TTS error: {exc}") from exc

    return StreamingResponse(generator(), media_type="audio/mpeg")

# # ====================== NEW: WebSocket for Always Listening ======================
# @app.websocket("/voice/ws/{session_id}")
# async def voice_websocket_endpoint(websocket: WebSocket, session_id: str):
#     await manager.connect(websocket, session_id)
#     await manager.handle_voice_stream(websocket, session_id)
# # =================================================================================
