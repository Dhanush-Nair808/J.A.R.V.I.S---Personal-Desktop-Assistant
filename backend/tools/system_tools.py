"""Safe, validated desktop tools exposed to the LangChain agent."""
from __future__ import annotations

import asyncio
import platform
import re
import shutil
import subprocess
import webbrowser
import calendar
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from langchain_core.tools import tool
from config import settings

# ---------------------------------------------------------------------------
# Allow-lists & validation helpers
# ---------------------------------------------------------------------------

_APP_ALIASES: dict[str, dict[str, str]] = {
    "chrome": {"Windows": "chrome", "Darwin": "Google Chrome", "Linux": "google-chrome"},
    "firefox": {"Windows": "firefox", "Darwin": "Firefox", "Linux": "firefox"},
    "safari": {"Darwin": "Safari"},
    "edge": {"Windows": "msedge", "Darwin": "Microsoft Edge", "Linux": "microsoft-edge"},
    "notepad": {"Windows": "notepad"},
    "textedit": {"Darwin": "TextEdit"},
    "calculator": {"Windows": "calc", "Darwin": "Calculator", "Linux": "gnome-calculator"},
    "vscode": {"Windows": "code", "Darwin": "Visual Studio Code", "Linux": "code"},
    "code": {"Windows": "code", "Darwin": "Visual Studio Code", "Linux": "code"},
    "terminal": {"Windows": "cmd", "Darwin": "Terminal", "Linux": "gnome-terminal"},
    "spotify": {"Windows": "spotify", "Darwin": "Spotify", "Linux": "spotify"},
    "explorer": {"Windows": "explorer"},
    "finder": {"Darwin": "Finder"},
    "steam": {"Windows": "steam://open/main", "Darwin": "Steam", "Linux": "steam"},
    "apex legends": {
        "Windows": "steam://rungameid/1172470",
        "Darwin": "Apex Legends",
        "Linux": "steam steam://rungameid/1172470",
    },
    "microsoft store": {"Windows": "start ms-windows-store:"},
    "ms word": {"Windows": "winword", "Darwin": "Microsoft Word"},
    "word": {"Windows": "winword", "Darwin": "Microsoft Word"},
    "ms excel": {"Windows": "excel", "Darwin": "Microsoft Excel"},
    "ms powerpoint": {"Windows": "powerpnt", "Darwin": "Microsoft PowerPoint"}
}

_APP_NAME_RE = re.compile(r"^[A-Za-z0-9 _.\-]{1,40}$")

def _resolve_app(app_name: str) -> str | None:
    key = app_name.strip().lower()
    mapping = _APP_ALIASES.get(key)
    return mapping.get(platform.system()) if mapping else None

# ---------------------------------------------------------------------------
# Blocking Implementations (Run in Executor)
# ---------------------------------------------------------------------------

def _launch_app_blocking(resolved: str) -> str:
    system = platform.system()
    try:
        if system == "Darwin":
            subprocess.Popen(["open", "-a", resolved])
        elif system == "Windows":
            subprocess.Popen(["cmd", "/c", "start", "", resolved], shell=False)
        else:
            if shutil.which(resolved) is None: return f"App '{resolved}' not found."
            subprocess.Popen([resolved])
        return f"Launched '{resolved}'."
    except Exception as exc:
        return f"Failed to launch '{resolved}': {exc}"

def _send_email_blocking(recipient: str, subject: str, body: str) -> str:
    try:
        if not all([settings.smtp_email, settings.smtp_password, settings.smtp_server]):
            return "SMTP settings are incomplete in config."
        
        msg = MIMEMultipart()
        msg['From'], msg['To'], msg['Subject'] = settings.smtp_email, recipient, subject
        msg.attach(MIMEText(body, 'plain'))
        
        with smtplib.SMTP(settings.smtp_server, settings.smtp_port) as server:
            server.starttls()
            server.login(settings.smtp_email, settings.smtp_password)
            server.send_message(msg)
        return f"✓ Email sent to {recipient}"
    except Exception as e:
        return f"✗ Failed to send email: {str(e)}"

def _file_io_blocking(full_path: str, content: str, mode: str) -> str:
    try:
        path = Path(full_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, mode, encoding='utf-8') as f:
            f.write(content)
        return f"✓ File operation successful: {full_path}"
    except Exception as e:
        return f"✗ File error: {str(e)}"

# ---------------------------------------------------------------------------
# LangChain Tools
# ---------------------------------------------------------------------------

@tool
async def open_app(app_name: str) -> str:
    """Open a desktop application. Supported: chrome, word, steam, apex legends, etc."""
    if not isinstance(app_name, str) or not _APP_NAME_RE.match(app_name.strip()):
        return "Invalid app name."
    resolved = _resolve_app(app_name)
    if not resolved: return f"'{app_name}' is not in the allow-list."
    return await asyncio.get_running_loop().run_in_executor(None, _launch_app_blocking, resolved)

@tool
async def open_website(url: str) -> str:
    """Open a URL in the user's default web browser."""
    candidate = url if "://" in url else f"https://{url}"
    webbrowser.open(candidate)
    return f"Opened {candidate}"

@tool
async def get_current_datetime() -> str:
    """Returns the current local date and time. Use for 'what time is it' or 'what is today'."""
    return datetime.now().strftime('%A, %B %d, %Y %I:%M %p')

@tool
async def get_calendar_view(year: int = None, month: int = None) -> str:
    """Generates a text calendar for a specific month or year."""
    now = datetime.now()
    y, m = year or now.year, month or now.month
    return f"Calendar for {calendar.month_name[m]} {y}:\n\n{calendar.month(y, m)}"

@tool
async def send_email(recipient: str, subject: str, body: str) -> str:
    """Send an email to a recipient."""
    return await asyncio.get_running_loop().run_in_executor(None, _send_email_blocking, recipient, subject, body)

@tool
async def create_file(file_path: str, content: str = "") -> str:
    """Create a new file at the specified path with optional content."""
    return await asyncio.get_running_loop().run_in_executor(None, _file_io_blocking, file_path, content, 'w')

@tool
async def write_to_file(file_path: str, content: str, append: bool = False) -> str:
    """Write or append text to an existing file."""
    mode = 'a' if append else 'w'
    return await asyncio.get_running_loop().run_in_executor(None, _file_io_blocking, file_path, content, mode)

# Final export list for the agent
ALL_TOOLS = [
    open_app, 
    open_website, 
    get_current_datetime, 
    get_calendar_view, 
    send_email, 
    create_file, 
    write_to_file
]
