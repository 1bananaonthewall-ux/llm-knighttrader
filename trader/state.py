"""Persistent trader state and research memory."""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any

from config import STATE_FILE, DATA_DIR
from trader.directives import append_user_directive as _append_user_directive_impl

_lock = threading.Lock()


def _default_state() -> dict[str, Any]:
    return {
        "started_at": time.time(),
        "cycles": 0,
        "research_notes": [],
        "trades": [],
        "lessons": [],
        "last_decision": None,
        "peak_equity": 0.0,
        "chat_history": [],
        "user_directives": [],
        "order_guard": {"history": []},
    }


def load_state() -> dict[str, Any]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not STATE_FILE.is_file():
        return _default_state()
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return _default_state()


_PROTECTED_KEYS = ("chat_history", "user_directives")


def _merge_protected_fields(state: dict[str, Any]) -> dict[str, Any]:
    """Keep chat/directives written by the dashboard when trader saves state."""
    if not STATE_FILE.is_file():
        return state
    try:
        on_disk = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return state
    for key in _PROTECTED_KEYS:
        disk_items = on_disk.get(key) or []
        mem_items = state.get(key) or []
        if len(disk_items) >= len(mem_items):
            state[key] = disk_items
        else:
            state[key] = mem_items
    return state


def save_state(state: dict[str, Any]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with _lock:
        state = _merge_protected_fields(dict(state))
        STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def reload_chat_fields(state: dict[str, Any]) -> dict[str, Any]:
    """Refresh chat/directives from disk before trader mutates state."""
    if not STATE_FILE.is_file():
        return state
    try:
        on_disk = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return state
    for key in _PROTECTED_KEYS:
        if on_disk.get(key):
            state[key] = on_disk[key]
    return state


def append_research(state: dict[str, Any], note: str) -> None:
    state["research_notes"].append({"ts": time.time(), "note": note})
    state["research_notes"] = state["research_notes"][-100:]


def append_trade(state: dict[str, Any], trade: dict[str, Any]) -> None:
    state["trades"].append(trade)
    state["trades"] = state["trades"][-200:]


def append_chat(state: dict[str, Any], role: str, content: str) -> None:
    state["chat_history"].append({"ts": time.time(), "role": role, "content": content})
    state["chat_history"] = state["chat_history"][-100:]


def append_user_directive(state: dict[str, Any], directive: str, *, source: str = "chat") -> None:
    _append_user_directive_impl(state, directive, source=source)


def get_lessons(state: dict[str, Any], limit: int = 20) -> list[dict[str, Any]]:
    rows = list(state.get("lessons") or [])
    rows.sort(key=lambda r: float(r.get("last_ts") or r.get("ts") or 0), reverse=True)
    return rows[:limit]
