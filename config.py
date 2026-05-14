"""Application configuration loaded from environment variables."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent


@dataclass(frozen=True)
class Settings:
    """Centralised, immutable application settings."""
    google_api_key: str
    gemini_model: str
    mistral_api_key: str
    mistral_model: str
    backend_host: str
    backend_port: int
    backend_url: str
    whisper_model: str
    whisper_device: str
    whisper_compute_type: str
    tts_voice: str
    safe_root: Path
    
    # Email SMTP settings
    smtp_email: str
    smtp_password: str
    smtp_server: str
    smtp_port: int

    # Wake Word Listener Settings
    wakeword_enabled: bool
    wakeword_model: str
    wakeword_sensitivity: float
    terminate_word: str
    terminate_sensitivity: float
    project_root: Path

    @property
    def chat_endpoint(self) -> str:
        return f"{self.backend_url.rstrip('/')}/chat"

    @property
    def health_endpoint(self) -> str:
        return f"{self.backend_url.rstrip('/')}/health"


def _bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def get_settings() -> Settings:
    """Build a Settings object from the current environment."""
    api_key = os.getenv("GOOGLE_API_KEY", "").strip()
    host = os.getenv("BACKEND_HOST", "127.0.0.1")
    port = int(os.getenv("BACKEND_PORT", "8000"))
    backend_url = os.getenv("BACKEND_URL", f"http://{host}:{port}")
    
    safe_root = Path(os.getenv("SAFE_ROOT", str(PROJECT_ROOT / "workspace"))).resolve()
    safe_root.mkdir(parents=True, exist_ok=True)

    return Settings(
        google_api_key=api_key,
        gemini_model=os.getenv("GEMINI_MODEL", "models/gemini-2.0-flash-lite-001"),
        mistral_api_key=os.getenv("MISTRAL_API_KEY", "").strip(),
        mistral_model=os.getenv("MISTRAL_MODEL", "mistral-large-latest"),
        backend_host=host,
        backend_port=port,
        backend_url=backend_url,
        whisper_model=os.getenv("WHISPER_MODEL", "base"),
        whisper_device=os.getenv("WHISPER_DEVICE", "cpu"),
        whisper_compute_type=os.getenv("WHISPER_COMPUTE_TYPE", "int8"),
        tts_voice=os.getenv("TTS_VOICE", "en-US-AriaNeural"),
        safe_root=safe_root,
        
        # SMTP settings
        smtp_email=os.getenv("SMTP_EMAIL", ""),
        smtp_password=os.getenv("SMTP_PASSWORD", ""),
        smtp_server=os.getenv("SMTP_SERVER", "smtp.gmail.com"),
        smtp_port=int(os.getenv("SMTP_PORT", "587")),

        # Wake Word Settings
        wakeword_enabled=_bool(os.getenv("WAKEWORD_ENABLED"), True),
        wakeword_model=os.getenv("WAKEWORD_MODEL", "hey_jarvis"),
        wakeword_sensitivity=float(os.getenv("WAKEWORD_SENSITIVITY", 0.5)),
        terminate_word=os.getenv("TERMINATE_WORD", "alexa"),
        terminate_sensitivity=float(os.getenv("TERMINATE_SENSITIVITY", 0.5)),
        project_root=Path(os.getenv("PROJECT_ROOT", str(PROJECT_ROOT))),
    )


settings = get_settings()