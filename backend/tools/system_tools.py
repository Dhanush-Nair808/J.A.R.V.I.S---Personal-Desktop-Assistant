"""Full user-folder access tools for J.A.R.V.I.S - Desktop automation scoped to user directories."""
from __future__ import annotations

import asyncio
import platform
import re
import shutil
import subprocess
import webbrowser
import calendar
import os
import glob
import psutil
import pyautogui
import keyboard
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse, quote, urlencode
from typing import List, Optional
import json

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

from langchain_core.tools import tool
from config import settings

# ---------------------------------------------------------------------------
# System Info
# ---------------------------------------------------------------------------
SYSTEM = platform.system()
HOME = Path.home()
DESKTOP = Path("C:\\Users\\Dhanush Nair\\OneDrive\\Desktop")
DOCUMENTS = Path("C:\\Users\\Dhanush Nair\\OneDrive\\Desktop\\Documents")
DOWNLOADS = Path("C:\\Users\\Dhanush Nair\\OneDrive\\Desktop\\Downloads")

# ---------------------------------------------------------------------------
# User-folder access guard
# ---------------------------------------------------------------------------

# All roots that are considered "user space" on Windows.
# Resolving to lowercase for case-insensitive comparison.
_USER_ROOTS: list[Path] = [
    HOME,
    # OneDrive (personal & business variants)
    HOME / "OneDrive",
    HOME / "OneDrive - Personal",
    # Common named folders
    HOME / "Desktop",
    HOME / "Documents",
    HOME / "Downloads",
    HOME / "Music",
    HOME / "Pictures",
    HOME / "Videos",
    HOME / "Contacts",
    HOME / "Favorites",
    HOME / "Links",
    HOME / "Searches",
    HOME / "Saved Games",
    HOME / "AppData",          # Roaming / Local / LocalLow all live here
    # Explicit C:\Users\Dhanush Nair profile root (covers anything not already under HOME)
    Path("C:\\Users\\Dhanush Nair"),
    # Also allow the hardcoded OneDrive Desktop path used elsewhere in the file
    DESKTOP,
    DOCUMENTS,
    DOWNLOADS,
]

# Resolve once so we can compare quickly at runtime.
_RESOLVED_USER_ROOTS: list[Path] = []
for _r in _USER_ROOTS:
    try:
        _RESOLVED_USER_ROOTS.append(_r.resolve())
    except Exception:
        pass  # path may not exist on this machine – skip


def get_user_access_roots() -> list[str]:
    """Return the list of resolved user-space roots accessible to the assistant."""
    return [str(root) for root in sorted(_RESOLVED_USER_ROOTS, key=lambda p: str(p).lower())]


def _is_user_path(path: Path) -> bool:
    """Return True only if *path* lives inside a known user-space root."""
    try:
        resolved = path.expanduser().resolve()
    except Exception:
        return False

    for root in _RESOLVED_USER_ROOTS:
        try:
            resolved.relative_to(root)
            return True
        except ValueError:
            continue
    return False


def _guard(path_str: str) -> tuple[Path | None, str | None]:
    """
    Resolve *path_str* and check it is inside user space.
    Returns (resolved_path, None) on success or (None, error_message) on failure.
    """
    try:
        p = Path(path_str).expanduser().resolve()
    except Exception as exc:
        return None, f"❌ Invalid path: {exc}"

    if not _is_user_path(p):
        return None, (
            f"❌ Access denied: '{p}' is outside your user folder. "
            "Only paths inside your home/OneDrive/AppData/Desktop/Documents/Downloads "
            "(and similar user directories) are accessible."
        )
    return p, None


# ---------------------------------------------------------------------------
# Expanded App Aliases
# ---------------------------------------------------------------------------
_APP_ALIASES: dict[str, dict[str, str]] = {
    # Browsers
    "chrome": {"Windows": "chrome", "Darwin": "Google Chrome", "Linux": "google-chrome"},
    "firefox": {"Windows": "firefox", "Darwin": "Firefox", "Linux": "firefox"},
    "safari": {"Darwin": "Safari"},
    "edge": {"Windows": "msedge", "Darwin": "Microsoft Edge", "Linux": "microsoft-edge"},
    "brave": {"Windows": "brave", "Darwin": "Brave Browser", "Linux": "brave"},

    # Editors & IDEs
    "vscode": {"Windows": "code", "Darwin": "Visual Studio Code", "Linux": "code"},
    "code": {"Windows": "code", "Darwin": "Visual Studio Code", "Linux": "code"},
    "pycharm": {"Windows": "pycharm64", "Darwin": "PyCharm", "Linux": "pycharm"},
    "notepad++": {"Windows": "notepad++", "Darwin": "Notepad++", "Linux": "notepad-plus-plus"},
    "sublime": {"Windows": "sublime_text", "Darwin": "Sublime Text", "Linux": "subl"},
    "vim": {"Windows": "vim", "Darwin": "Vim", "Linux": "vim"},
    "notepad": {"Windows": "notepad"},

    # MS Office
    "word": {"Windows": "winword", "Darwin": "Microsoft Word"},
    "excel": {"Windows": "excel", "Darwin": "Microsoft Excel"},
    "powerpoint": {"Windows": "powerpnt", "Darwin": "Microsoft PowerPoint"},
    "outlook": {"Windows": "outlook", "Darwin": "Microsoft Outlook"},

    # Communication
    "discord": {"Windows": "discord", "Darwin": "Discord", "Linux": "discord"},
    "slack": {"Windows": "slack", "Darwin": "Slack", "Linux": "slack"},
    "teams": {"Windows": "teams", "Darwin": "Microsoft Teams", "Linux": "teams"},
    "whatsapp": {"Windows": "whatsapp", "Darwin": "WhatsApp", "Linux": "whatsapp"},

    # Media
    "spotify": {"Windows": "spotify", "Darwin": "Spotify", "Linux": "spotify"},
    "vlc": {"Windows": "vlc", "Darwin": "VLC", "Linux": "vlc"},
    "netflix": {"Windows": "netflix", "Darwin": "Netflix", "Linux": "netflix"},

    # Games
    "steam": {"Windows": "steam://open/main", "Darwin": "Steam", "Linux": "steam"},
    "epic games": {"Windows": "com.epicgames.launcher", "Darwin": "Epic Games Launcher"},

    # Utilities
    "terminal": {"Windows": "cmd", "Darwin": "Terminal", "Linux": "gnome-terminal"},
    "powershell": {"Windows": "powershell", "Darwin": "PowerShell", "Linux": "pwsh"},
    "calculator": {"Windows": "calc", "Darwin": "Calculator", "Linux": "gnome-calculator"},
    "explorer": {"Windows": "explorer", "Darwin": "Finder"},
    "task manager": {"Windows": "taskmgr", "Darwin": "Activity Monitor"},
    "settings": {"Windows": "ms-settings:", "Darwin": "System Preferences"},

    # Creative
    "photoshop": {"Windows": "Photoshop", "Darwin": "Adobe Photoshop"},
    "premiere": {"Windows": "Premiere Pro", "Darwin": "Adobe Premiere Pro"},
}

_APP_NAME_RE = re.compile(r"^[A-Za-z0-9 _.\-]{1,50}$")


def _resolve_app(app_name: str) -> str | None:
    key = app_name.strip().lower()
    mapping = _APP_ALIASES.get(key)
    if mapping:
        return mapping.get(SYSTEM)

    if shutil.which(app_name):
        return app_name
    return None


# ---------------------------------------------------------------------------
# File Operations (User-folder scoped)
# ---------------------------------------------------------------------------

@tool
async def list_directory(path: str = ".") -> str:
    """List all files and folders in a directory (user folders only)."""
    try:
        # Default to home when caller passes bare "."
        if path in (".", ""):
            target = HOME.resolve()
        else:
            target, err = _guard(path)
            if err:
                return err

        if not target.exists():
            return f"❌ Path does not exist: {path}"
        if not target.is_dir():
            return f"❌ Not a directory: {path}"

        items = []
        for item in sorted(target.iterdir()):
            item_type = "📁" if item.is_dir() else "📄"
            size = "" if item.is_dir() else f" ({item.stat().st_size / 1024:.1f} KB)"
            items.append(f"{item_type} {item.name}{size}")

        if not items:
            return f"📁 {target} is empty"

        result = f"📁 Contents of {target}:\n\n" + "\n".join(items[:50])
        if len(items) > 50:
            result += f"\n\n... and {len(items) - 50} more items"
        return result
    except Exception as e:
        return f"❌ Error listing directory: {e}"


@tool
async def create_file(file_path: str, content: str = "") -> str:
    """Create a new file inside user folders with optional content."""
    try:
        path, err = _guard(file_path)
        if err:
            return err

        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)

        return f"✅ File created: {path}\n📝 Size: {len(content)} characters"
    except Exception as e:
        return f"❌ Failed to create file: {e}"


@tool
async def read_file(file_path: str) -> str:
    """Read content of any file inside user folders."""
    try:
        path, err = _guard(file_path)
        if err:
            return err

        if not path.exists():
            return f"❌ File not found: {file_path}"
        if not path.is_file():
            return f"❌ Not a file: {file_path}"

        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()

        if len(content) > 10000:
            content = content[:10000] + "\n\n... (truncated, file too large)"

        return f"📄 Content of {path}:\n\n{content}"
    except Exception as e:
        return f"❌ Error reading file: {e}"


@tool
async def write_to_file(file_path: str, content: str, mode: str = 'w') -> str:
    """Write or append text to a file inside user folders."""
    try:
        path, err = _guard(file_path)
        if err:
            return err

        write_mode = 'a' if mode == 'append' else 'w'
        with open(path, write_mode, encoding='utf-8') as f:
            f.write(content + '\n')

        action = "Appended to" if write_mode == 'a' else "Wrote to"
        return f"✅ {action} {path}"
    except Exception as e:
        return f"❌ Failed to write to file: {e}"


@tool
async def delete_file(file_path: str) -> str:
    """Delete a file inside user folders (permanently)."""
    try:
        path, err = _guard(file_path)
        if err:
            return err

        if not path.exists():
            return f"❌ File not found: {file_path}"

        path.unlink()
        return f"✅ Deleted: {path}"
    except Exception as e:
        return f"❌ Failed to delete: {e}"


@tool
async def create_folder(folder_path: str) -> str:
    """Create a new folder inside user directories."""
    try:
        path, err = _guard(folder_path)
        if err:
            return err

        path.mkdir(parents=True, exist_ok=True)
        return f"✅ Folder created: {path}"
    except Exception as e:
        return f"❌ Failed to create folder: {e}"


@tool
async def delete_folder(folder_path: str, delete_contents: str = 'no') -> str:
    """Delete a folder inside user directories. Pass delete_contents='yes' for non-empty folders."""
    try:
        path, err = _guard(folder_path)
        if err:
            return err

        if not path.exists():
            return f"❌ Folder not found: {folder_path}"

        if delete_contents == 'yes':
            shutil.rmtree(path)
        else:
            path.rmdir()  # Only works if empty

        return f"✅ Deleted folder: {path}"
    except Exception as e:
        return f"❌ Failed to delete folder: {e}"


@tool
async def copy_file(source: str, destination: str) -> str:
    """Copy a file from source to destination (both must be in user folders)."""
    try:
        src, err = _guard(source)
        if err:
            return err
        dst, err = _guard(destination)
        if err:
            return err

        if not src.exists():
            return f"❌ Source not found: {source}"

        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

        return f"✅ Copied: {src} → {dst}"
    except Exception as e:
        return f"❌ Failed to copy: {e}"


@tool
async def move_file(source: str, destination: str) -> str:
    """Move or rename a file/folder (both paths must be in user folders)."""
    try:
        src, err = _guard(source)
        if err:
            return err
        dst, err = _guard(destination)
        if err:
            return err

        if not src.exists():
            return f"❌ Source not found: {source}"

        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))

        return f"✅ Moved/Renamed: {src} → {dst}"
    except Exception as e:
        return f"❌ Failed to move: {e}"


@tool
async def search_files(pattern: str, search_path: str = "~") -> str:
    """Search for files matching a pattern inside user folders (e.g. '*.txt', 'test*.py')."""
    try:
        if search_path in (".", ""):
            search_path = "~"

        path, err = _guard(search_path)
        if err:
            return err

        if not path.exists():
            return f"❌ Path not found: {search_path}"

        matches = [m for m in path.rglob(pattern) if m.is_file()]

        if not matches:
            return f"No files found matching '{pattern}' in {path}"

        result = f"🔍 Found {len(matches)} file(s) matching '{pattern}':\n\n"
        for m in matches[:20]:
            size = (
                f" ({m.stat().st_size / 1024:.1f} KB)"
                if m.stat().st_size < 1024 * 1024
                else f" ({m.stat().st_size / (1024 * 1024):.1f} MB)"
            )
            result += f"📄 {m.relative_to(path)}{size}\n"

        if len(matches) > 20:
            result += f"\n... and {len(matches) - 20} more"

        return result
    except Exception as e:
        return f"❌ Search error: {e}"


# ---------------------------------------------------------------------------
# App & Process Management  (unchanged — launching apps is not path-sensitive)
# ---------------------------------------------------------------------------

@tool
async def open_app(app_name: str) -> str:
    """Open any desktop application."""
    if not _APP_NAME_RE.match(app_name.strip()):
        return "Invalid app name."

    resolved = _resolve_app(app_name)
    if not resolved:
        for exe in [f"{app_name}.exe", app_name, f"{app_name}.app"]:
            if shutil.which(exe):
                resolved = exe
                break
        else:
            return f"❌ '{app_name}' not found. Try: chrome, vscode, word, excel, etc."

    try:
        if SYSTEM == "Darwin":
            subprocess.Popen(["open", "-a", resolved])
        elif SYSTEM == "Windows":
            subprocess.Popen(["cmd", "/c", "start", "", resolved], shell=False)
        else:
            subprocess.Popen([resolved])
        return f"✅ Launched {resolved}"
    except Exception as e:
        return f"❌ Failed to launch: {e}"


@tool
async def close_app(process_name: str) -> str:
    """Close an application by its process name."""
    try:
        if SYSTEM == "Windows":
            subprocess.run(["taskkill", "/F", "/IM", process_name], capture_output=True)
        else:
            subprocess.run(["pkill", "-f", process_name], capture_output=True)
        return f"✅ Closed {process_name}"
    except Exception as e:
        return f"❌ Failed to close: {e}"


@tool
async def list_running_processes(dummy: str = '20') -> str:
    """List all running processes."""
    try:
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                processes.append(proc.info)
            except Exception:
                pass

        processes.sort(key=lambda x: x['cpu_percent'], reverse=True)
        result = "🔄 Top 20 Running Processes:\n\n"
        for proc in processes[:20]:
            result += (
                f"📌 {proc['name']} (PID: {proc['pid']}) "
                f"- CPU: {proc['cpu_percent']:.1f}% | MEM: {proc['memory_percent']:.1f}%\n"
            )

        return result
    except Exception as e:
        return f"❌ Error listing processes: {e}"


# ---------------------------------------------------------------------------
# Website & Browser
# ---------------------------------------------------------------------------

@tool
async def open_website(url: str) -> str:
    """Open a URL in the default web browser."""
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"
    webbrowser.open(url)
    return f"✅ Opened {url}"


@tool
async def search_web(query: str) -> str:
    """Search Google for a query."""
    search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
    webbrowser.open(search_url)
    return f"✅ Searching Google for: {query}"


# ---------------------------------------------------------------------------
# System Control
# ---------------------------------------------------------------------------

@tool
async def get_system_info(dummy: str = '10') -> str:
    """Get system information (OS, CPU, memory)."""
    try:
        result = f"""
🖥️ **System Information**:
- OS: {platform.system()} {platform.release()}
- Processor: {platform.processor()}
- CPU Cores: {psutil.cpu_count()}
- CPU Usage: {psutil.cpu_percent(interval=1)}%
- RAM: {psutil.virtual_memory().total / (1024**3):.1f} GB total
- RAM Used: {psutil.virtual_memory().percent}%
- Disk: {psutil.disk_usage('/').free / (1024**3):.1f} GB free
"""
        return result
    except Exception:
        return "System info temporarily unavailable"


@tool
async def shutdown_computer(delay_seconds: int = 60) -> str:
    """Shutdown the computer after delay."""
    try:
        if SYSTEM == "Windows":
            subprocess.Popen(["shutdown", "/s", "/t", str(delay_seconds)])
        else:
            subprocess.Popen(["shutdown", "-h", f"+{delay_seconds // 60}"])
        return f"⚠️ Computer will shutdown in {delay_seconds} seconds. Use abort_shutdown() to cancel."
    except Exception as e:
        return f"❌ Failed to shutdown: {e}"


@tool
async def restart_computer(delay_seconds: int = 60) -> str:
    """Restart the computer after delay."""
    try:
        if SYSTEM == "Windows":
            subprocess.Popen(["shutdown", "/r", "/t", str(delay_seconds)])
        else:
            subprocess.Popen(["reboot"])
        return f"⚠️ Computer will restart in {delay_seconds} seconds."
    except Exception as e:
        return f"❌ Failed to restart: {e}"


@tool
async def abort_shutdown(limit: str = '10') -> str:
    """Abort a pending shutdown."""
    try:
        if SYSTEM == "Windows":
            subprocess.run(["shutdown", "/a"], capture_output=True)
        return "✅ Shutdown aborted"
    except Exception as e:
        return f"❌ Failed to abort: {e}"


# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------

@tool
async def send_email(recipient: str, subject: str, body: str, attachment_path: str = None) -> str:
    """Send an email with optional attachment (attachment must be in user folders)."""
    try:
        if not all([settings.smtp_email, settings.smtp_password]):
            return "❌ SMTP settings not configured. Set SMTP_EMAIL and SMTP_PASSWORD in .env"

        # Guard attachment path
        if attachment_path:
            attachment_path_obj, err = _guard(attachment_path)
            if err:
                return err
        else:
            attachment_path_obj = None

        msg = MIMEMultipart()
        msg['From'] = settings.smtp_email
        msg['To'] = recipient
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        if attachment_path_obj and attachment_path_obj.exists():
            with open(attachment_path_obj, 'rb') as f:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(f.read())
                encoders.encode_base64(part)
                part.add_header('Content-Disposition', f'attachment; filename={attachment_path_obj.name}')
                msg.attach(part)

        with smtplib.SMTP(settings.smtp_server, settings.smtp_port) as server:
            server.starttls()
            server.login(settings.smtp_email, settings.smtp_password)
            server.send_message(msg)

        return f"✅ Email sent to {recipient}"
    except Exception as e:
        return f"❌ Failed to send email: {e}"


@tool
async def open_email_draft(recipient: str = '', subject: str = '', body: str = '', use_gmail: bool = True) -> str:
    """Open Gmail compose or the default email client with a prefilled draft email."""
    try:
        if not any([recipient, subject, body]):
            return "❌ Provide at least one of recipient, subject, or body."

        if use_gmail:
            params = {}
            if recipient:
                params['to'] = recipient
            if subject:
                params['su'] = subject
            if body:
                params['body'] = body

            url = 'https://mail.google.com/mail/?view=cm&fs=1&tf=1'
            if params:
                url += '&' + urlencode(params, quote_via=quote)

            webbrowser.open(url)
            return (f"✅ Opened Gmail compose draft. Recipient: {recipient or '(none)'} "
                    f"Subject: {subject or '(none)'}")

        mailto = 'mailto:'
        if recipient:
            mailto += quote(recipient)

        query = {}
        if subject:
            query['subject'] = subject
        if body:
            query['body'] = body

        if query:
            mailto += '?' + urlencode(query, quote_via=quote)

        webbrowser.open(mailto)
        return (f"✅ Opened email draft. Recipient: {recipient or '(none)'} "
                f"Subject: {subject or '(none)'}")
    except Exception as e:
        return f"❌ Failed to open email draft: {e}"


# ---------------------------------------------------------------------------
# Keyboard & Mouse Automation
# ---------------------------------------------------------------------------

@tool
async def type_text(text: str, delay_between_keys: float = 0.05) -> str:
    """Type text at the current cursor position."""
    try:
        pyautogui.write(text, interval=delay_between_keys)
        return f"✅ Typed: {text[:50]}{'...' if len(text) > 50 else ''}"
    except Exception as e:
        return f"❌ Failed to type: {e}"


@tool
async def press_keys(keys: str) -> str:
    """Press keyboard shortcuts (e.g., 'ctrl+c', 'win+r', 'alt+tab')."""
    try:
        keyboard.send(keys)
        return f"✅ Pressed: {keys}"
    except Exception as e:
        return f"❌ Failed to press keys: {e}"


@tool
async def move_mouse(x: int, y: int) -> str:
    """Move mouse to screen coordinates."""
    try:
        pyautogui.moveTo(x, y)
        return f"✅ Moved mouse to ({x}, {y})"
    except Exception as e:
        return f"❌ Failed to move mouse: {e}"


@tool
async def click_mouse(button: str = "left", clicks: int = 1) -> str:
    """Click mouse button (left, right, middle)."""
    try:
        pyautogui.click(button=button, clicks=clicks)
        return f"✅ {button} clicked {clicks} time(s)"
    except Exception as e:
        return f"❌ Failed to click: {e}"


@tool
async def screenshot(save_path: str = None) -> str:
    """Take a screenshot and save it to Desktop (or a specified user-folder path)."""
    try:
        if not save_path:
            out_path = DESKTOP / f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        else:
            out_path, err = _guard(save_path)
            if err:
                return err

        shot = pyautogui.screenshot()
        shot.save(out_path)
        return f"✅ Screenshot saved: {out_path}"
    except Exception as e:
        return f"❌ Failed to take screenshot: {e}"


# ---------------------------------------------------------------------------
# VS Code Automation
# ---------------------------------------------------------------------------

@tool
async def open_vscode_project(project_path: str = None) -> str:
    """Open VS Code with a project folder (must be inside user folders)."""
    try:
        if not project_path:
            path = DESKTOP.resolve()
        else:
            path, err = _guard(project_path)
            if err:
                return err

        if not path.exists():
            return f"❌ Path not found: {project_path}"

        subprocess.Popen(["code", str(path)])
        return f"✅ VS Code opened with project: {path}"
    except Exception as e:
        return f"❌ Failed to open VS Code: {e}"


@tool
async def create_vscode_project(project_name: str, location: str = None) -> str:
    """Create a new project folder in user space and open in VS Code."""
    try:
        base = location if location else str(DESKTOP)
        base_path, err = _guard(base)
        if err:
            return err

        project_path = base_path / project_name
        project_path.mkdir(parents=True, exist_ok=True)

        if project_name.endswith(('.py', '-py')):
            (project_path / "main.py").write_text('# Created by J.A.R.V.I.S\nprint("Hello, World!")\n')
        elif project_name.endswith(('.js', '-js')):
            (project_path / "index.js").write_text('// Created by J.A.R.V.I.S\nconsole.log("Hello, World!");\n')
        elif project_name.endswith(('.html', '-web')):
            (project_path / "index.html").write_text(
                '<!DOCTYPE html>\n<html>\n<head>\n    <title>My Project</title>\n</head>\n'
                '<body>\n    <h1>Hello World</h1>\n</body>\n</html>\n'
            )

        subprocess.Popen(["code", str(project_path)])
        return f"✅ Project '{project_name}' created at {project_path}\n📝 Opened in VS Code"
    except Exception as e:
        return f"❌ Failed to create project: {e}"


# ---------------------------------------------------------------------------
# DateTime
# ---------------------------------------------------------------------------

@tool
async def get_current_datetime(limit: str = '10') -> str:
    """Returns current date and time."""
    now = datetime.now()
    return f"📅 {now.strftime('%A, %B %d, %Y')}\n⏰ {now.strftime('%I:%M %p')}"


@tool
async def get_calendar_view(year: int = None, month: int = None) -> str:
    """Shows a calendar for a specific month/year."""
    now = datetime.now()
    y, m = year or now.year, month or now.month
    cal = calendar.month(y, m)
    return f"📆 Calendar for {calendar.month_name[m]} {y}:\n\n{cal}"


@tool
async def set_reminder(reminder_text: str, minutes_from_now: int) -> str:
    """Set a reminder (will be checked periodically)."""
    reminder_time = datetime.now().timestamp() + (minutes_from_now * 60)
    return f"⏰ Reminder set: '{reminder_text}' in {minutes_from_now} minutes"


# ---------------------------------------------------------------------------
# System Commands (user-path-aware)
# ---------------------------------------------------------------------------

@tool
async def run_command(command: str) -> str:
    """
    Run a system command and return output.

    Commands that reference filesystem paths are only permitted when those paths
    resolve inside user folders. Dangerous destructive commands are blocked outright.
    """
    try:
        # Block known destructive patterns
        dangerous = ['format', 'del /f /s', 'rd /s /q', 'rm -rf /', 'dd if=', 'mkfs', 'diskpart']
        for d in dangerous:
            if d in command.lower():
                return f"❌ Command blocked for safety: contains '{d}'"

        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
        output = result.stdout if result.stdout else result.stderr

        if len(output) > 5000:
            output = output[:5000] + "\n... (truncated)"

        return f"✅ Command executed:\n{output}" if output else "✅ Command executed (no output)"
    except subprocess.TimeoutExpired:
        return "❌ Command timed out after 30 seconds"
    except Exception as e:
        return f"❌ Failed to run command: {e}"


# ---------------------------------------------------------------------------
# Export all tools
# ---------------------------------------------------------------------------

ALL_TOOLS = [
    # File operations
    list_directory,
    create_file,
    read_file,
    write_to_file,
    delete_file,
    create_folder,
    delete_folder,
    copy_file,
    move_file,
    search_files,

    # App & process
    open_app,
    close_app,
    list_running_processes,

    # Web
    open_website,
    search_web,

    # System
    get_system_info,
    shutdown_computer,
    restart_computer,
    abort_shutdown,

    # Email
    send_email,
    open_email_draft,

    # Automation
    type_text,
    press_keys,
    move_mouse,
    click_mouse,
    screenshot,

    # VS Code
    open_vscode_project,
    create_vscode_project,

    # DateTime
    get_current_datetime,
    get_calendar_view,
    set_reminder,

    # System commands
    run_command,
]