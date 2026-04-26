# Personal Voice Assistant

A production-ready desktop personal voice assistant built with **FastAPI**,
**Streamlit**, **LangChain**, **Google Gemini**, **faster-whisper** (STT), and
**edge-tts** (TTS). Async-first, modular, Python 3.10 compatible.

## Project layout

```
voice-assistant/
├── backend/
│   ├── main.py            # FastAPI app
│   ├── agent.py           # LangChain agent (create_tool_calling_agent)
│   ├── memory.py          # Per-session chat memory
│   ├── tools/
│   │   ├── __init__.py
│   │   └── system_tools.py  # open_app, open_website, create_file
│   └── voice/
│       ├── stt.py         # faster-whisper async wrapper
│       └── tts.py         # edge-tts async wrapper
├── frontend/
│   └── app.py             # Streamlit UI
├── config.py              # Centralised settings (.env)
├── requirements.txt
└── .env.example
```

## Setup

1. **Create a virtualenv** (Python 3.10+):

   ```bash
   python -m venv .venv
   source .venv/bin/activate          # macOS / Linux
   .venv\Scripts\activate             # Windows
   ```

2. **Install dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

   `faster-whisper` requires `ffmpeg` to be available on your system (e.g.
   `brew install ffmpeg`, `apt install ffmpeg`, or `choco install ffmpeg`).

3. **Configure environment**:

   ```bash
   cp .env.example .env
   # then edit .env and put your real GOOGLE_API_KEY
   ```

   Get a Gemini key at <https://aistudio.google.com/app/apikey>.

## Run

Open two terminals.

**Terminal 1 — backend:**

```bash
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

**Terminal 2 — frontend:**

```bash
streamlit run frontend/app.py
```

Open the URL Streamlit prints (usually <http://localhost:8501>).

## Try it

Type any of these into the chat box:

- `open chrome`
- `open youtube.com`
- `create a file called notes.txt`
- `what's a good way to learn Rust?`

The assistant replies conversationally and invokes the matching tool when
appropriate.

## API endpoints

| Method | Path                       | Purpose                         |
| ------ | -------------------------- | ------------------------------- |
| GET    | `/health`                  | Backend / model health          |
| POST   | `/chat`                    | Send a message, get a reply     |
| GET    | `/history/{session_id}`    | Inspect a session's transcript  |
| DELETE | `/history/{session_id}`    | Clear a session's transcript    |
| POST   | `/voice/transcribe`        | Upload audio → transcript (STT) |
| GET    | `/voice/speak?text=…`      | Stream synthesised speech (TTS) |

## Safety notes

- `open_app` is restricted to a curated allow-list (Chrome, Firefox, Edge,
  Safari, VS Code, Calculator, Notepad, TextEdit, Spotify, Terminal, Finder,
  Explorer). Anything else is refused.
- `open_website` only allows `http(s)` URLs with valid hosts.
- `create_file` only writes inside `SAFE_ROOT` (default: `./workspace`).
  Absolute paths and `..` traversal are rejected.
- The agent is capped at 5 tool-call iterations per turn.

## Notes

- All FastAPI endpoints are `async`; the LLM is invoked via `ainvoke`.
- Blocking work (`subprocess`, `webbrowser`, file IO, `faster-whisper`) is
  dispatched through `asyncio.run_in_executor`.
- Uses the modern `create_tool_calling_agent` + `AgentExecutor` API — no
  deprecated `initialize_agent`.
