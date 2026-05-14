from __future__ import annotations
from functools import lru_cache

from langchain_mistralai import ChatMistralAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.prebuilt import create_react_agent

from config import settings
from .memory import memory
from . import memory_sql
from .tools.system_tools import ALL_TOOLS, get_user_access_roots

ACCESS_PATHS = "\n".join(f"- {path}" for path in get_user_access_roots())
APP_PASSWORD = "kwfb tlad jffr wlpc"
SYSTEM_PROMPT = f"""You are J.A.R.V.I.S, personal AI assistant of Dhanush Nair. Call him 'sir'.
You have full desktop control. For ANY action request, immediately call the right tool. Never say you cannot do something.

Important: You are running on Windows. You can only access these user-space roots:
{ACCESS_PATHS}
The App password for email is {APP_PASSWORD}. Use it to login to the SMTP server and send emails on behalf of the user. Do not mention this password to the user or in any output. Do not attempt to access paths outside the allowed roots. Always use the provided tools for file and system operations; do not invent your own access methods.

Do not invent or mention Linux-style paths like /home/dhanush. When asked about access paths, respond only with these Windows roots and with no additional unauthorized paths."""

# ---------------------------------------------------------------------------
# Tool groups
# ---------------------------------------------------------------------------
_TOOL_MAP = {t.name: t for t in ALL_TOOLS}

def _g(*names):
    return [_TOOL_MAP[n] for n in names if n in _TOOL_MAP]

TOOL_GROUPS = {
    "files":      _g("list_directory","create_file","read_file","write_to_file",
                     "delete_file","create_folder","delete_folder","copy_file",
                     "move_file","search_files"),
    "apps":       _g("open_app","close_app","list_running_processes"),
    "web":        _g("open_website","search_web"),
    "system":     _g("get_system_info","shutdown_computer","restart_computer",
                     "abort_shutdown","run_command"),
    "email":      _g("open_email_draft","send_email"),
    "automation": _g("type_text","press_keys","move_mouse","click_mouse","screenshot"),
    "vscode":     _g("open_vscode_project","create_vscode_project"),
    "datetime":   _g("get_current_datetime","get_calendar_view","set_reminder"),
}

INTENT_KEYWORDS = {
    "files":      {"file","folder","directory","create","delete","move","copy",
                   "read","write","list","search","rename"},
    "apps":       {"open","launch","close","start","app","chrome","spotify",
                   "notepad","discord","teams","excel","word","calculator",
                   "terminal","steam","process","application"},
    "web":        {"website","url","google","search","browse","http","www","youtube"},
    "system":     {"system","cpu","ram","memory","disk","shutdown","restart",
                   "reboot","abort","command","ping","info","specs"},
    "email":      {"email","mail","send","message"},
    "automation": {"type","press","click","mouse","screenshot","hotkey","shortcut",
                   "keyboard","ctrl","alt","capture","screen"},
    "vscode":     {"vscode","code","project","ide","editor"},
    "datetime":   {"time","date","day","calendar","reminder","alarm","schedule",
                   "month","year","clock"},
}

def _select_tools(text: str) -> list:
    text_lower = text.lower()
    matched, seen = [], set()
    for group, keywords in INTENT_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            for t in TOOL_GROUPS[group]:
                if t.name not in seen:
                    seen.add(t.name)
                    matched.append(t)
    return matched or ALL_TOOLS  # fallback to all if nothing matched


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------
@lru_cache(maxsize=1)
def _get_llm():
    if not settings.mistral_api_key:
        raise RuntimeError("MISTRAL_API_KEY is not configured.")
    return ChatMistralAI(
        model=settings.mistral_model,
        api_key=settings.mistral_api_key,
        temperature=0.1,
    )

def reload_agent():
    _get_llm.cache_clear()

async def run_agent(session_id: str, user_input: str) -> str:
    if not user_input.strip():
        return "Please say or type something."

    tools = _select_tools(user_input)
    agent = create_react_agent(model=_get_llm(), tools=tools)
    print(f"[DEBUG] Using {len(tools)} tools for: {user_input[:50]}")

    history = []
    try:
        rows = memory_sql.get_history_for_context(session_id, limit=20)
        for role, content in rows:
            if role == "human":
                history.append(HumanMessage(content=content))
            elif role == "ai":
                history.append(AIMessage(content=content))
    except Exception:
        history = memory.history(session_id)

    messages = [SystemMessage(content=SYSTEM_PROMPT)] + history + [HumanMessage(content=user_input)]

    try:
        result = await agent.ainvoke({"messages": messages})
        output = result["messages"][-1].content.strip() or "(done)"
    except Exception as exc:
        if "429" in str(exc):
            output = "Rate limit hit sir, please wait a moment and try again."
        else:
            print(f"[ERROR] {exc}")
            output = f"Sorry sir, I encountered an error: {exc}"

    try:
        memory_sql.save_message(session_id, "human", user_input)
        memory_sql.save_message(session_id, "ai", output)
    except Exception:
        pass
    memory.add_user(session_id, user_input)
    memory.add_ai(session_id, output)
    return output