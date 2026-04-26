"""Streamlit frontend for J.A.R.V.I.S - Personal Voice Assistant.

Run with::

    streamlit run frontend/app.py
"""
from __future__ import annotations

import sys
import uuid
from pathlib import Path
from urllib.parse import quote

# Make ``import config`` work when launched via ``streamlit run frontend/app.py``.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import requests  # noqa: E402
import streamlit as st  # noqa: E402

from config import settings  # noqa: E402

st.set_page_config(
    page_title="J.A.R.V.I.S - Voice Assistant",
    page_icon="🤖",
    layout="centered",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------

if "session_id" not in st.session_state:
    st.session_state.session_id = uuid.uuid4().hex[:12]

if "messages" not in st.session_state:
    # Each message: {"role": "user"|"assistant", "content": str, "audio": bytes|None}
    st.session_state.messages = []

if "tts_enabled" not in st.session_state:
    st.session_state.tts_enabled = True

if "last_audio_id" not in st.session_state:
    st.session_state.last_audio_id = None


# ---------------------------------------------------------------------------
# Backend helpers
# ---------------------------------------------------------------------------


def _backend_alive() -> tuple[bool, str]:
    try:
        r = requests.get(settings.health_endpoint, timeout=3)
        if r.ok:
            data = r.json()
            model = data.get('model', 'J.A.R.V.I.S')
            return True, f"✓ Connected • {model}"
        return False, f"Backend responded with {r.status_code}"
    except requests.RequestException as exc:
        return False, f"Backend unreachable: {exc}"


def _send_message(text: str) -> str:
    payload = {"message": text, "session_id": st.session_state.session_id}
    try:
        r = requests.post(settings.chat_endpoint, json=payload, timeout=120)
    except requests.RequestException as exc:
        return f"⚠️ Could not reach backend: {exc}"
    if not r.ok:
        try:
            detail = r.json().get("detail", r.text)
        except ValueError:
            detail = r.text
        return f"⚠️ Backend error ({r.status_code}): {detail}"
    return r.json().get("reply", "(empty reply)")


def _transcribe(audio_bytes: bytes, filename: str) -> str:
    url = f"{settings.backend_url.rstrip('/')}/voice/transcribe"
    try:
        r = requests.post(
            url,
            files={"file": (filename, audio_bytes, "audio/wav")},
            timeout=120,
        )
    except requests.RequestException as exc:
        return f"⚠️ Could not reach backend: {exc}"
    if not r.ok:
        try:
            detail = r.json().get("detail", r.text)
        except ValueError:
            detail = r.text
        return f"⚠️ Transcription error ({r.status_code}): {detail}"
    return (r.json().get("text") or "").strip()


def _synthesize(text: str) -> bytes | None:
    url = f"{settings.backend_url.rstrip('/')}/voice/speak?text={quote(text)}"
    try:
        r = requests.get(url, timeout=120)
        if r.ok and r.content:
            return r.content
    except requests.RequestException:
        pass
    return None


def _clear_history() -> None:
    try:
        requests.delete(
            f"{settings.backend_url.rstrip('/')}/history/{st.session_state.session_id}",
            timeout=5,
        )
    except requests.RequestException:
        pass
    st.session_state.messages = []
    st.session_state.last_audio_id = None


def _handle_user_turn(text: str) -> None:
    """Append the user message, get a reply, optionally synthesise speech."""
    text = (text or "").strip()
    if not text:
        return
    st.session_state.messages.append({"role": "user", "content": text, "audio": None})
    reply = _send_message(text)
    audio = _synthesize(reply) if st.session_state.tts_enabled else None
    st.session_state.messages.append({"role": "assistant", "content": reply, "audio": audio})


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------

st.title("🤖 J.A.R.V.I.S")
st.caption("Just A Rather Very Intelligent System")

alive, status = _backend_alive()
(st.success if alive else st.error)(status)

with st.sidebar:
    st.subheader("⚙️ Assistant")
    st.metric("Model", "J.A.R.V.I.S (Mistral)")
    st.caption(f"Session: `{st.session_state.session_id}`")
    
    st.session_state.tts_enabled = st.toggle(
        "🔊 Speak replies", value=st.session_state.tts_enabled
    )
    if st.button("🔄 New conversation", use_container_width=True):
        _clear_history()
        st.session_state.session_id = uuid.uuid4().hex[:12]
        st.rerun()

    st.divider()
    st.subheader("💡 Example commands")
    st.caption(
        "• *open chrome*\n"
        "• *open youtube.com*\n"
        "• *create a file called notes.txt*\n"
        "• *what time is it in Tokyo?*\n"
        "• *write hello world to a file*"
    )

# Render existing transcript
for msg in st.session_state.messages:
    role_label = "You" if msg["role"] == "user" else "J.A.R.V.I.S"
    with st.chat_message(msg["role"], avatar="👤" if msg["role"] == "user" else "🤖"):
        st.markdown(msg["content"])
        if msg["role"] == "assistant" and msg.get("audio"):
            st.audio(msg["audio"], format="audio/mp3")

st.divider()

# ---- Voice input ---------------------------------------------------------
st.caption("🎤 Record a voice command")
_audio_input_fn = getattr(st, "audio_input", None) or getattr(
    st, "experimental_audio_input", None
)
audio_value = (
    _audio_input_fn("Hold to record, release to send", label_visibility="collapsed")
    if _audio_input_fn is not None
    else None
)
if _audio_input_fn is None:
    st.info(
        "Voice input requires Streamlit ≥ 1.31. Upgrade with "
        "`pip install -U streamlit` to record from the browser."
    )
if audio_value is not None:
    audio_bytes = audio_value.getvalue()
    audio_id = f"{len(audio_bytes)}-{hash(audio_bytes[:1024])}"
    if audio_id != st.session_state.last_audio_id:
        st.session_state.last_audio_id = audio_id
        with st.spinner("🎙️ Transcribing…"):
            transcript = _transcribe(audio_bytes, "voice.wav")
        if transcript and not transcript.startswith("⚠️"):
            with st.spinner("🤔 Thinking…"):
                _handle_user_turn(transcript)
            st.rerun()
        elif transcript:
            st.error(transcript)

# ---- Text input ----------------------------------------------------------
prompt = st.chat_input("Chat with J.A.R.V.I.S")
if prompt:
    with st.spinner("🤔 Thinking…"):
        _handle_user_turn(prompt)
    st.rerun()