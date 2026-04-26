from __future__ import annotations
from functools import lru_cache
from langchain_mistralai import ChatMistralAI
from langgraph.prebuilt import create_react_agent # The modern alternative
from config import settings
from .memory import memory
from .tools import ALL_TOOLS

SYSTEM_PROMPT = (
    "You are J.A.R.V.I.S, "
    "a helpful, concise desktop voice assistant. "
    "When the user asks you to perform an action — opening an app, opening a website, "
    "or creating a file — call the appropriate tool exactly once and then describe "
    "when the user asks you to send an email,use the send_email tool to send an email and then describe the action."
    "what you did in one short sentence. If the user just chats, reply conversationally "
    "without calling tools. Always be professional and efficient."
)


@lru_cache(maxsize=1)
def get_agent():
    """Builds the LangGraph agent. Replaces get_agent_executor."""
    if not settings.mistral_api_key:
        raise RuntimeError("MISTRAL_API_KEY is not configured.")

    llm = ChatMistralAI(
        model=settings.mistral_model,
        api_key=settings.mistral_api_key,
        temperature=0.1,
        
    )

    # create_react_agent handles the prompt, tools, and iteration logic internally
    # In get_agent()
    return create_react_agent(
    model=llm,
    tools=ALL_TOOLS,
    # Change state_modifier to system_message
    
)


async def run_agent(session_id: str, user_input: str) -> str:
    """Invokes the agent and manages history."""
    if not user_input or not user_input.strip():
        return "Please say or type something."

    agent = get_agent()
    
    # Fetch existing history from your memory module
    history = memory.history(session_id)

    # LangGraph expects a list of messages. We combine history + new input.
    inputs = {"messages": history + [("human", user_input)]}

    # Run the agent
    result = await agent.ainvoke(inputs)

    # The result contains the full message list; the last one is the AI response
    output = result["messages"][-1].content.strip() or "(no response)"

    # Persist to your existing memory
    memory.add_user(session_id, user_input)
    memory.add_ai(session_id, output)

    return output
