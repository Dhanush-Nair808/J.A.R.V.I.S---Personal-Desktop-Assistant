"""Lightweight chat memory keyed by session id.

Stores ``HumanMessage`` / ``AIMessage`` objects in a bounded deque per session.
Suitable for a single-process desktop assistant; swap in Redis or a database
for multi-process deployments.
"""
from __future__ import annotations

from collections import deque
from threading import Lock
from typing import Deque, Dict, List

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

DEFAULT_MAX_TURNS = 8  # 8 user+assistant pairs


class ConversationMemory:
    """Thread-safe in-memory conversation store."""

    def __init__(self, max_messages: int = DEFAULT_MAX_TURNS * 2) -> None:
        self._max = max_messages
        self._store: Dict[str, Deque[BaseMessage]] = {}
        self._lock = Lock()

    def _bucket(self, session_id: str) -> Deque[BaseMessage]:
        if session_id not in self._store:
            self._store[session_id] = deque(maxlen=self._max)
        return self._store[session_id]

    def history(self, session_id: str) -> List[BaseMessage]:
        with self._lock:
            return list(self._bucket(session_id))

    def add_user(self, session_id: str, content: str) -> None:
        with self._lock:
            self._bucket(session_id).append(HumanMessage(content=content))

    def add_ai(self, session_id: str, content: str) -> None:
        with self._lock:
            self._bucket(session_id).append(AIMessage(content=content))

    def clear(self, session_id: str) -> None:
        with self._lock:
            self._store.pop(session_id, None)


memory = ConversationMemory()
