# J.A.R.V.I.S — Personal Voice Assistant

A full-featured personal assistant built in Python with:
- **FastAPI** backend for async REST and audio endpoints
- **Streamlit** web UI for chat, voice input, and audio playback
- **LangChain** agent tooling for safe, composable tool calls
- **faster-whisper** for local speech transcription
- **edge-tts** for streamed speech synthesis
- Multi-model support: Mistral for chat, Gemini for additional generative capabilities

## What J.A.R.V.I.S can do

J.A.R.V.I.S is more than a chatbot — it can:

- Control desktop apps and browse safely: open Chrome, VS Code, Spotify, or open a website
- Manage files inside the user workspace: create, read, list, copy, move, and delete files
- Handle email drafts and send messages when configured with SMTP credentials
- Transcribe uploaded audio and speak responses back as streamed MP3
- Maintain session memory and history so it remembers context across turns
- Execute secure automation tools while preventing unsafe shell access
- Provide system status and user-folder scoped access guards

Examples:

- “Open Chrome and go to youtube.com”
- “Create a file called `notes.txt` in my workspace and write today’s agenda”
- “Transcribe this audio file and summarize the result”
- “Send an email to Alice with subject `Meeting` and body `Let’s meet tomorrow at 10 AM`”
- “Search the web for the fastest way to learn Rust and summarize the top answer”
- “List the contents of my Documents folder”

## Project layout

```
voice-assistant/
├── backend/
│   ├── main.py            # FastAPI app
│   ├── agent.py           # LangChain agent and tool orchestration
│   ├── memory.py          # In-memory session memory
│   ├── memory_sql.py      # SQLite-backed session history
│   ├── tools/             # Agent tool implementations
│   └── voice/             # STT / TTS wrappers
├── frontend/
│   └── app.py             # Streamlit UI
├── config.py              # Environment-driven settings
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .dockerignore
└── .env.example
```

## Requirements

- Python 3.10+
- Docker 24+ / Docker Compose
- `ffmpeg` is required for local audio transcription and playback

## Local setup

1. Create and activate a virtual environment:

   ```bash
   python -m venv .venv
   source .venv/bin/activate          # macOS / Linux
   .venv\Scripts\activate           # Windows
   ```

2. Install Python dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Create a local config file:

   ```bash
   cp .env.example .env
   ```

4. Edit `.env` and set at least:

   - `GOOGLE_API_KEY`
   - `MISTRAL_API_KEY`

## Run locally

Start the backend service:

```bash
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

Start the frontend UI:

```bash
streamlit run frontend/app.py
```

Then open `http://localhost:8501`.

## Docker setup

Build and launch the app with Docker Compose:

```bash
docker compose up --build
```

The frontend will be available at `http://localhost:8501` and the backend at
`http://localhost:8000`.

Stop services with:

```bash
docker compose down
```

## Wake listener

The current `wake_listener.py` script is a separate host-side helper, not part of the Docker Compose runtime.
It is designed to run on Windows and listens for keywords like `hey_jarvis` or `alexa`; when detected, it launches `run_app.ps1` to start the local app.

If you want to use it:

1. Install the required wake word dependencies on your Windows host.
2. Copy `.env.example` to `.env` and configure your API keys.
3. Run:

```bash
python wake_listener.py
```

Because `wake_listener.py` depends on local audio input and Windows-specific tooling, it is usually run outside Docker.

## API endpoints

| Method | Path                       | Purpose                         |
| ------ | -------------------------- | ------------------------------- |
| GET    | `/health`                  | Backend / model health          |
| POST   | `/chat`                    | Send a message, get a reply     |
| GET    | `/history/{session_id}`    | Inspect a session transcript    |
| DELETE | `/history/{session_id}`    | Clear a session transcript      |
| GET    | `/sessions`                | List active sessions            |
| POST   | `/voice/transcribe`        | Upload audio → transcript (STT) |
| GET    | `/voice/speak?text=…`      | Stream synthesised speech (TTS) |

## Usage examples

Try messages like:

- `open chrome`
- `open youtube.com`
- `create a file called notes.txt`
- `what's a good way to learn Rust?`

## Safety notes

- `open_app` is restricted to a curated allow-list.
- `open_website` only allows valid `http(s)` hosts.
- `create_file` only writes inside `SAFE_ROOT`.
- Tool calls are capped to prevent runaway behavior.

## Notes

- The backend is built with asynchronous FastAPI routes.
- The frontend is a Streamlit web UI that posts chat messages to the backend.
- Docker Compose runs the backend and frontend in separate containers.
