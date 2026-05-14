"""Streamlit frontend for J.A.R.V.I.S - Personal Voice Assistant.

Run with::

    streamlit run frontend/app.py
"""
from __future__ import annotations

import re
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

if "voice_mode" not in st.session_state:
    st.session_state.voice_mode = True

if "recent_sessions" not in st.session_state:
    st.session_state.recent_sessions = []

if "last_audio_id" not in st.session_state:
    st.session_state.last_audio_id = None

if "voice_input_changed" not in st.session_state:
    st.session_state.voice_input_changed = False

if "greeting_played" not in st.session_state:
    st.session_state.greeting_played = False

if "is_listening" not in st.session_state:
    st.session_state.is_listening = True

if "is_speaking" not in st.session_state:
    st.session_state.is_speaking = False

if "pending_audio" not in st.session_state:
    st.session_state.pending_audio = None



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


def _clean_voice_text(text: str) -> str:
    cleaned = re.sub(r"https?://\S+", "", text)
    cleaned = re.sub(r"[#*`_>~-]+", " ", cleaned)
    cleaned = re.sub(r":\w+:", " ", cleaned)
    cleaned = re.sub(r"\s*\n\s*", " ", cleaned)
    cleaned = ''.join(c for c in cleaned if ord(c) < 128)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned or text


def _synthesize(text: str) -> bytes | None:
    text = _clean_voice_text(text)
    url = f"{settings.backend_url.rstrip('/')}/voice/speak?text={quote(text)}"
    try:
        r = requests.get(url, timeout=120)
        if r.ok and r.content:
            return r.content
    except requests.RequestException:
        pass
    return None


def _play_pending_audio() -> None:
    pending = st.session_state.pop("pending_audio", None)
    if pending:
        _play_audio(pending)


def _play_audio(audio_bytes: bytes) -> None:
    """Play audio bytes automatically without showing a visible audio player."""
    import base64
    import streamlit.components.v1 as components

    st.session_state.is_speaking = True
    audio_b64 = base64.b64encode(audio_bytes).decode()
    audio_html = f"""
        <audio id='jarvis-audio' autoplay playsinline style='display:none;'>
            <source src='data:audio/mpeg;base64,{audio_b64}' type='audio/mpeg'>
        </audio>
        <script>
            const audio = document.getElementById('jarvis-audio');
            if (audio) {{
                audio.play().catch(() => {{
                    console.warn('Autoplay prevented, audio will still be available.');
                }});
            }}
        </script>
    """
    components.html(audio_html, height=0, width=0)
    st.session_state.is_speaking = False


def _render_voice_circle() -> None:
    """Render the listening/speaking voice circle with optional halo animation."""
    halo_class = "halo-animate" if st.session_state.is_speaking else ""
    st.markdown(
        f"""
        <style>
            @keyframes halo-pulse {{
                0% {{ box-shadow: 0 0 0 0 rgba(133, 215, 255, 0.7); }}
                70% {{ box-shadow: 0 0 0 30px rgba(133, 215, 255, 0); }}
                100% {{ box-shadow: 0 0 0 0 rgba(133, 215, 255, 0); }}
            }}
            .halo-animate {{
                animation: halo-pulse 1.5s infinite;
            }}
        </style>
        <div style='display:flex;justify-content:center;margin-bottom:16px;'>
            <div class='{halo_class}' style='width:140px;height:140px;border-radius:70px;
            background:radial-gradient(circle, #85d7ff 0%, #2563eb 100%);
            display:flex;align-items:center;justify-content:center;color:#ffffff;
            font-size:48px;'>🎙️</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _play_greeting() -> None:
    """Play a random greeting message."""
    greetings = [
        "Hello sir, how can I assist you today?",
        "Good day, sir. What can I do for you?",
        "Greetings, sir. I'm ready to help.",
        "Hello, Dhanush. How may I be of service?",
    ]
    import random
    greeting = random.choice(greetings)
    audio = _synthesize(greeting)
    if audio:
        _play_audio(audio)
    st.session_state.greeting_played = True


def _fetch_sessions() -> list[dict]:
    try:
        r = requests.get(f"{settings.backend_url.rstrip('/')}/sessions", timeout=5)
        if r.ok:
            return r.json()
    except requests.RequestException:
        pass
    return []


def _load_session(session_id: str) -> None:
    st.session_state.session_id = session_id
    try:
        r = requests.get(
            f"{settings.backend_url.rstrip('/')}/history/{session_id}", timeout=10
        )
        if r.ok:
            payload = r.json()
            st.session_state.messages = [
                {"role": row["role"], "content": row["content"], "audio": None}
                for row in payload.get("messages", [])
            ]
        else:
            st.session_state.messages = []
    except requests.RequestException:
        st.session_state.messages = []
    st.session_state.last_audio_id = None


def _delete_session(session_id: str) -> None:
    try:
        requests.delete(
            f"{settings.backend_url.rstrip('/')}/sessions/{session_id}",
            timeout=10,
        )
    except requests.RequestException:
        pass


def _start_voice_mode() -> None:
    st.session_state.voice_mode = True
    st.session_state.tts_enabled = True


def _stop_voice_mode() -> None:
    st.session_state.voice_mode = False


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
    """Append the user message, get a reply, and queue speech for playback."""
    text = (text or "").strip()
    if not text:
        return
    st.session_state.messages.append({"role": "user", "content": text, "audio": None})
    reply = _send_message(text)
    audio = _synthesize(reply) if st.session_state.tts_enabled else None
    st.session_state.messages.append({"role": "assistant", "content": reply, "audio": audio})
    if st.session_state.voice_mode and audio:
        st.session_state.pending_audio = audio


def _on_voice_audio_change() -> None:
    """Mark that audio input has been updated by the user."""
    st.session_state.voice_input_changed = True


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
    if st.session_state.is_listening:
        if st.button("🎤 Stop listening", use_container_width=True):
            st.session_state.is_listening = False
            st.rerun()
    else:
        if st.button("🎙️ Start listening", use_container_width=True):
            st.session_state.is_listening = True
            st.rerun()

    if st.button("🔄 New conversation", use_container_width=True):
        _clear_history()
        st.session_state.session_id = uuid.uuid4().hex[:12]
        st.session_state.voice_mode = False
        st.session_state.recent_sessions = []
        st.rerun()

    st.divider()
    st.subheader("🕘 Recent sessions")
    if not st.session_state.recent_sessions:
        st.session_state.recent_sessions = _fetch_sessions()

    if st.session_state.recent_sessions:
        options = [
            f"{s['session_id']} — {s['last_time']}" for s in st.session_state.recent_sessions
        ]
        choice = st.selectbox("Select a previous session", options, key="session_select")
        selected = st.session_state.recent_sessions[options.index(choice)]["session_id"]
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Load selected session", use_container_width=True):
                _load_session(selected)
                st.rerun()
        with col2:
            if st.button("🗑️ Delete selected session", use_container_width=True):
                _delete_session(selected)
                st.session_state.recent_sessions = _fetch_sessions()
                if st.session_state.session_id == selected:
                    _clear_history()
                    st.session_state.session_id = uuid.uuid4().hex[:12]
                st.rerun()
    else:
        st.caption("No previous sessions found.")

    if st.button("🔃 Refresh sessions", use_container_width=True):
        st.session_state.recent_sessions = _fetch_sessions()
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
    with st.chat_message(msg["role"], avatar="👤" if msg["role"] == "user" else "🤖"):
        st.markdown(msg["content"])

st.divider()
_play_pending_audio()

if st.session_state.is_listening:
    _render_voice_circle()
    st.markdown("### Click the microphone to start speaking.")
    _audio_input_fn = getattr(st, "audio_input", None) or getattr(
        st, "experimental_audio_input", None
    )
    if _audio_input_fn is not None:
        audio_value = _audio_input_fn(
            "Speak naturally. Recording will auto-submit after 4 seconds of silence.",
            key="voice_audio_input",
            label_visibility="collapsed",
            on_change=_on_voice_audio_change,
        )
        if audio_value is not None:
            audio_bytes = audio_value.getvalue()
            audio_id = f"{len(audio_bytes)}-{hash(audio_bytes[:1024])}"
            if audio_id != st.session_state.last_audio_id:
                st.session_state.last_audio_id = audio_id
                st.session_state.voice_input_changed = False
                with st.spinner("🎙️ Transcribing…"):
                    transcript = _transcribe(audio_bytes, "voice.wav")
                if transcript and not transcript.startswith("⚠️"):
                    with st.spinner("🤔 Thinking…"):
                        _handle_user_turn(transcript)
                    st.rerun()
                elif transcript:
                    st.error(transcript)
    else:
        st.info(
            "Voice input requires Streamlit ≥ 1.31. Upgrade with `pip install -U streamlit` "
            "to record from the browser."
        )
else:
    st.caption("Type your message below and press Enter to chat.")

# ---- Text input ----------------------------------------------------------
prompt = st.chat_input("Chat with J.A.R.V.I.S")
if prompt:
    with st.spinner("🤔 Thinking…"):
        _handle_user_turn(prompt)
    st.rerun()
if alive and st.session_state.voice_mode and not st.session_state.greeting_played:
    if "greeting_played_flag" not in st.session_state:
        st.session_state.greeting_played_flag = False

    if not st.session_state.greeting_played_flag:
        _play_greeting()
        st.session_state.greeting_played_flag = True
        st.session_state.greeting_played = True
