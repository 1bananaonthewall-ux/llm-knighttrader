"""LLM KnightTrader configuration."""

from __future__ import annotations

import os
from pathlib import Path

APP_NAME = "LLM KnightTrader"
CHAT_AGENT_NAME = "LLM KnightTrader"

PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data"
ACTIVITY_LOG = DATA_DIR / "activity.jsonl"
STATE_FILE = DATA_DIR / "state.json"
PID_DIR = DATA_DIR / "pids"


def _load_dotenv() -> None:
    """Load PROJECT_ROOT/.env into os.environ (no extra dependency)."""
    path = PROJECT_ROOT / ".env"
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = val


_load_dotenv()

DEFAULT_CREDENTIALS_PATH = Path(
    os.environ.get(
        "BLOFIN_CREDENTIALS_PATH",
        str(PROJECT_ROOT / "credentials" / "blofin.txt"),
    )
)

BLOFIN_BASE = os.environ.get("BLOFIN_API_BASE", "https://openapi.blofin.com")
BLOFIN_BROKER_ID = os.environ.get("BLOFIN_BROKER_ID", "5388cb1f51cec2e3")

DASHBOARD_HOST = os.environ.get(
    "KNIGHTTRADER_DASHBOARD_HOST",
    os.environ.get("HERMES_DASHBOARD_HOST", "127.0.0.1"),
)
DASHBOARD_PORT = int(
    os.environ.get(
        "KNIGHTTRADER_DASHBOARD_PORT",
        os.environ.get("HERMES_DASHBOARD_PORT", "8765"),
    )
)

TARGET_EQUITY = float(
    os.environ.get(
        "KNIGHTTRADER_TARGET_EQUITY",
        os.environ.get("HERMES_TARGET_EQUITY", "1000000"),
    )
)
TRADER_LOOP_SEC = float(
    os.environ.get(
        "KNIGHTTRADER_LOOP_SEC",
        os.environ.get("HERMES_TRADER_LOOP_SEC", "60"),
    )
)

# How often any process may refresh balance/positions from BloFin (seconds).
ACCOUNT_REFRESH_SEC = float(
    os.environ.get(
        "KNIGHTTRADER_ACCOUNT_REFRESH_SEC",
        os.environ.get("HERMES_ACCOUNT_REFRESH_SEC", "15"),
    )
)

# Game mode: raise leverage as needed so min contract margin fits available balance.
TRADE_MODE = os.environ.get("KNIGHTTRADER_TRADE_MODE", "game").strip().lower()
TRADE_MAX_LEVERAGE = int(os.environ.get("KNIGHTTRADER_MAX_LEVERAGE", "50"))
MARGIN_USE_RATIO = float(os.environ.get("KNIGHTTRADER_MARGIN_USE_RATIO", "0.92"))
LEVERAGE_LADDER = [
    int(x)
    for x in os.environ.get("KNIGHTTRADER_LEVERAGE_LADDER", "3,5,10,15,20,30,50").split(",")
    if x.strip().isdigit()
] or [3, 5, 10, 15, 20, 30, 50]

# BloHunter: harvest winners only at +NTP%.
BLOHUNTER_HARVEST_NTP_PCT = float(os.environ.get("KNIGHTTRADER_HARVEST_NTP_PCT", "5.0"))

# LLM HTTP: no short timeouts — slow/free models may take minutes.
LLM_HTTP_TIMEOUT_SEC = float(os.environ.get("KNIGHTTRADER_LLM_HTTP_TIMEOUT_SEC", "600"))
# Parallel repair LLM workers — race until one succeeds (no wall-clock cutoff).
REPAIR_LLM_PARALLEL = max(1, int(os.environ.get("KNIGHTTRADER_REPAIR_LLM_PARALLEL", "3")))

MISSION_PROMPT = (
    "research how to grow crypto futures account the fastest to get a baseline, "
    "learn as you go, and trade the configured BloFin account to 1 million "
    "as fast as you can. make no mistakes"
)
