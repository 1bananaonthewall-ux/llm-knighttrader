"""Load BloHunter tactics knowledge for LLM prompts."""

from __future__ import annotations

from pathlib import Path

from config import DATA_DIR, PROJECT_ROOT

DEFAULT_CONNECT_PATH = Path.home() / "Downloads" / "blohunter-connect"
TACTICS_FILE = DATA_DIR / "blohunter_tactics.md"
BLOHUNTER_SITE = "https://blohunter.com"


def connect_source_path() -> Path:
    env = __import__("os").environ.get("BLOHUNTER_CONNECT_PATH", "")
    if env:
        return Path(env)
    return DEFAULT_CONNECT_PATH


def tactics_path() -> Path:
    return TACTICS_FILE


def load_blohunter_tactics(*, max_chars: int = 12000) -> str:
    """Return tactics markdown for system prompt / trader context."""
    if TACTICS_FILE.is_file():
        text = TACTICS_FILE.read_text(encoding="utf-8").strip()
        if text:
            if len(text) > max_chars:
                return text[: max_chars - 80] + "\n\n[... tactics truncated for token budget ...]"
            return text

    # Minimal fallback if file missing
    return (
        f"BloHunter ({BLOHUNTER_SITE}) streams signed futures lifecycle events. "
        "Mirror tactics: manage active positions, DCA on drawdown ladders, "
        "never close under +5% PnL, cap leverage at 3x, gate new opens on margin heat, "
        "prefer hold/close over reckless opens. Run scripts/ingest_blohunter_tactics.py."
    )


def tactics_meta() -> dict[str, str]:
    path = tactics_path()
    connect = connect_source_path()
    return {
        "tactics_file": str(path),
        "tactics_exists": str(path.is_file()),
        "connect_path": str(connect),
        "connect_exists": str(connect.is_dir()),
        "site": BLOHUNTER_SITE,
    }
