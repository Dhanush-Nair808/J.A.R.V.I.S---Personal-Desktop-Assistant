from __future__ import annotations
from functools import lru_cache

from langchain_mistralai import ChatMistralAI
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.prebuilt import create_react_agent   # ← Changed to this

from config import settings

# Correct imports
from .memory import memory
from .memory_sql import get_history_for_context, save_message
from .tools.system_tools import ALL_TOOLS


SYSTEM_PROMPT = (
    "You are J.A.R.V.I.S, personal assistant of Dhanush Nair. "
    "Refer to him as 'sir'. "
    "You are a powerful desktop voice assistant with full system access. "
    "Always use the correct tool for the requested action."
)


@lru_cache(maxsize=1)
def get_agent():
    if not settings.mistral_api_key:
        raise RuntimeError("MISTRAL_API_KEY is not configured.")

    llm = ChatMistralAI(
        model=settings.mistral_model,
        api_key=settings.mistral_api_key,
        temperature=0.1,
    )

    print(f"[DEBUG] ✅ Loaded {len(ALL_TOOLS)} tools!")
    tool_names = [t.name for t in ALL_TOOLS]
    print("Tools loaded:", tool_names[:15], "...")

    return create_react_agent(
        model=llm,
        tools=ALL_TOOLS,
        state_modifier=SYSTEM_PROMPT
    )


def reload_agent():
    get_agent.cache_clear()
    print("✅ Agent cache cleared.")


async def run_agent(session_id: str, user_input: str) -> str:
    if not user_input or not user_input.strip():
        return "Please say or type something."

    agent = get_agent()

    history = []
    try:
        rows = get_history_for_context(session_id, limit=30)
        for role, content in rows:
            if role == "human":
                history.append(HumanMessage(content=content))
            elif role == "ai":
                history.append(AIMessage(content=content))
    except Exception:
        pass

    inputs = {"messages": history + [HumanMessage(content=user_input)]}

    try:
        result = await agent.ainvoke(inputs)
        output = result["messages"][-1].content.strip() or "(done)"
    except Exception as exc:
        print(f"[ERROR] {exc}")
        output = "Sorry sir, something went wrong."

    try:
        save_message(session_id, "human", user_input)
        save_message(session_id, "ai", output)
    except:
        pass

    memory.add_user(session_id, user_input)
    memory.add_ai(session_id, output)

    return output