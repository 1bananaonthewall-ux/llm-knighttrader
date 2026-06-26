"""Operator chat → live trader context (dashboard messages must be heard)."""

from __future__ import annotations

import time
from typing import Any


def _normalize_entry(item: Any, *, default_source: str = "legacy") -> dict[str, Any]:
    if isinstance(item, dict):
        text = str(item.get("text") or item.get("content") or "").strip()
        return {
            "ts": float(item.get("ts") or 0),
            "text": text,
            "source": str(item.get("source") or default_source),
        }
    text = str(item or "").strip()
    return {"ts": 0.0, "text": text, "source": default_source}


def normalize_directives(state: dict[str, Any]) -> list[dict[str, Any]]:
    raw = state.get("user_directives") or []
    return [_normalize_entry(item) for item in raw if _normalize_entry(item)["text"]]


def recent_operator_chat(state: dict[str, Any], *, limit: int = 10) -> list[dict[str, Any]]:
    """Recent user messages from dashboard chat (not assistant replies)."""
    out: list[dict[str, Any]] = []
    for msg in reversed(state.get("chat_history") or []):
        if str(msg.get("role") or "") != "user":
            continue
        text = str(msg.get("content") or "").strip()
        if not text:
            continue
        out.append(
            {
                "ts": float(msg.get("ts") or 0),
                "content": text,
            }
        )
        if len(out) >= limit:
            break
    return list(reversed(out))


def active_directives(state: dict[str, Any], *, limit: int = 15) -> list[dict[str, Any]]:
    """Newest operator directives first (chat-sourced prioritized by recency)."""
    rows = [r for r in normalize_directives(state) if r["text"]]
    rows.sort(key=lambda r: float(r.get("ts") or 0), reverse=True)
    return list(reversed(rows[:limit]))


def operator_instructions(state: dict[str, Any]) -> dict[str, Any]:
    chat = recent_operator_chat(state, limit=10)
    directives = active_directives(state, limit=15)
    latest = chat[-1]["content"] if chat else (directives[-1]["text"] if directives else "")
    return {
        "heard": bool(chat or directives),
        "note": (
            "Live instructions from the human operator via dashboard chat. "
            "These are injected every trading cycle — follow them over generic defaults when they conflict."
        ),
        "latest_user_message": latest,
        "recent_chat_messages": chat,
        "directives": directives,
    }


def append_user_directive(
    state: dict[str, Any],
    directive: str,
    *,
    source: str = "chat",
) -> None:
    text = str(directive or "").strip()
    if not text:
        return
    rows = normalize_directives(state)
    now = time.time()
    if rows:
        last = rows[-1]
        if last["text"] == text and now - float(last.get("ts") or 0) < 3:
            return
    rows.append({"ts": now, "text": text, "source": source})
    state["user_directives"] = rows[-50:]
