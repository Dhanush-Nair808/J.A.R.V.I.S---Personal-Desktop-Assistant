# J.A.R.V.I.S. - Your Personal AI Assistant

**Just Another Remarkably Intelligent Virtual Intelligent System**

A powerful **desktop voice assistant** with full file system access, automation capabilities, voice interaction, and tool-using AI agent — built for **Myself**.

---
## ⚠️ Important Note

**This J.A.R.V.I.S. is customized for Dhanush Nair.**  
It contains some hardcoded paths for the user `Dhanush Nair`.  
If someone else wants to use it, they must replace all occurrences of `Dhanush Nair` with their own Windows username.

---

## ✨ Overview

J.A.R.V.I.S. is a **local-first personal AI assistant** that combines:
- Advanced LLM reasoning (Mistral Large)
- Voice input/output (Whisper + Edge TTS)
- Deep desktop integration (files, mouse/keyboard, apps, VS Code)
- Wake word activation ("Hey Jarvis") and deactivation ("alexa")
- Secure sandboxed execution (restricted to your user folders)

It runs as a **FastAPI backend** + **Streamlit frontend** and gives you natural language control over your Windows machine.

---

## 🚀 Features

### Core Capabilities
- **Voice Interaction**: Speak → Transcribe (faster-whisper) → AI responds → TTS (edge-tts)
- **Text Chat**: Full conversational memory with history
- **Tool Use Agent**: React-style agent that can call tools autonomously

### Wake Word Feature
- Say **"Hey Jarvis"** to automatically launch the assistant
- Say **"Alexa"** to stop the assistant
- Runs in background via Windows Startup

### File & Folder Management
- Create, read, write, delete, copy, move files/folders
- Search files with glob patterns (`*.py`, `report*.xlsx`)
- Full access to **Desktop, Documents, Downloads, OneDrive**, etc.

### Development & Productivity
- Create and open VS Code projects instantly
- Type text, press hotkeys, control mouse
- Take screenshots
- Run safe system commands

### System Control
- Launch/close applications (Chrome, VS Code, Spotify, Word, etc.)
- View running processes and system info
- Shutdown/restart with safety delays
- Send emails with attachments

### Security
- Strictly guarded to user-space directories only
- No access to system32, Program Files, or outside your profile

---

## 📁 Project Structure
```text
voice-assistant/
├── .streamlit/
├── .vscode/
├── backend/
│   ├── tools/
│   │   ├── __init__.py
│   │   └── system_tools.py       # Local OS automation tools
│   ├── voice/
│   │   ├── __init__.py
│   │   ├── stt.py                # STT processing engine
│   │   └── tts.py                # TTS generation engine
│   ├── __init__.py
│   ├── agent.py                  # LangGraph state machine orchestrator
│   ├── config.py                 # Pydantic BaseSettings loader
│   ├── main.py                   # FastAPI service runner
│   ├── memory.py                 # Volatile session context
│   └── memory_sql.py             # Persistent SQLite backend
├── frontend/
│   └── app.py                    # Streamlit UI layout and state management
├── workspace/              # Preserves empty safe workspace directory
├── .env.example                  # Template for credentials (API keys, paths)
├── .gitignore                    
├── LICENSE                       # Project distribution permissions
├── README.md                     # Setup instructions and documentation
├── requirements.txt              # Explicit python package dependencies
├── run_app.ps1                   # Automated local execution script
└── wake_listener.py              # Hotword detection loop to trigger assistant
```



## 🛠️ Installation & Setup

### 1. Clone / Download the Project

### 2. Create Virtual Environment
```powershell
python -m venv venv
venv\Scripts\activate
```
3. Install Dependencies
```PowerShellpip install -r requirements.txt```
(You may need to create requirements.txt with: fastapi, uvicorn, streamlit, langchain, faster-whisper, edge-tts, pyautogui, etc.)

4. Configure .env
```text
env# AI
MISTRAL_API_KEY=your_mistral_api_key_here
MISTRAL_MODEL=mistral-large-latest
```

Optional: Google (if using Gemini fallback)
```text
GOOGLE_API_KEY=...
```

Voice
```text
WHISPER_MODEL=base
WHISPER_DEVICE=cpu
TTS_VOICE=en-US-AriaNeural
```

Email (Gmail SMTP recommended)
```text
SMTP_EMAIL=your.email@gmail.com
SMTP_PASSWORD=your_app_password_here
```

Others
```
BACKEND_HOST=127.0.0.1
BACKEND_PORT=8000
Note: For Gmail, use an App Password, not your regular password.
```


## ▶️ Running J.A.R.V.I.S.

### Wake Word Activation (Recommended)

To make "Hey Jarvis" work automatically on startup:

Press Win + R, type shell:startup and press Enter.
Create a new text file named Start_JARVIS_Listener.bat
Paste the following into it:
```
batch@echo off
title J.A.R.V.I.S Wake Word Listener
cd /d "C:\Users\Dhanush Nair\OneDrive\Desktop\voice-assistant\voice-assistant"
venv\Scripts\python.exe wake_listener.py
pause
```

Save the file and restart your computer.

Now whenever you say "Hey Jarvis", the assistant will launch automatically.

To terminate the application say "alexa".

### Easiest Way

Double-click run_app.ps1 (or run in PowerShell).
This will:

Start the FastAPI backend (hidden)
Start the Streamlit frontend (hidden)
Open your browser to http://localhost:8501

### Manual Start

PowerShell Terminal 1
```
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

Terminal 2
```
streamlit run frontend/app.py
```

## 📋 Available Tools (Agent Capabilities)
```text
The agent has access to these tool groups:

Files: list_directory, create_file, read_file, write_to_file, delete_file, etc.
Apps: open_app, close_app, list_running_processes
Web: open_website, search_web
Automation: type_text, press_keys, click_mouse, screenshot
VS Code: open_vscode_project, create_vscode_project
System: get_system_info, shutdown_computer, etc.
Email: send_email, open_email_draft
```
 
## 💡 Example Commands
```text
"Create a new Python project called 'AI_Experiment' on Desktop and open in VS Code"
"List all PDF files in my Documents folder"
"Write a summary of today's tasks in notes.txt on Desktop"
"Open Chrome and search for latest AI news"
"Take a screenshot"
"Send an email to john@example.com with subject 'Meeting Notes'"
```

## 🛡️ Security Model
```text
All file operations are validated against a whitelist of user directories.
Dangerous commands (format, rm -rf, etc.) are blocked.
Runs with your user privileges — never with admin rights.
```

## 🧠 Tech Stack
```text
LLM: Mistral Large (via LangChain)
Agent Framework: LangGraph ReAct Agent
STT: faster-whisper
TTS: edge-tts (high quality, streaming)
Backend: FastAPI
Frontend: Streamlit
Automation: pyautogui + keyboard
Database: SQLite (chat history)
Wakeword: openwakeword
```

## 📌 Limitations
```text
Currently optimized for Windows
Requires internet (LLM API + TTS)
Voice recognition quality depends on microphone and Whisper model size
Agent may occasionally hallucinate tool calls
```

## 🔮 Future Enhancements
```text
Local LLM support (via Ollama/LM Studio)
Vision capabilities (screenshot analysis)
Calendar integration
Custom voice training
Multi-user sessions
```

Made with ❤️ for maximum productivity and fun.

J.A.R.V.I.S. is always at your service, Sir.
