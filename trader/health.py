"""Trader process health: single-instance lock and decision validation."""

from __future__ import annotations

import os
import subprocess
import sys
from typing import Any

from activity_log import log_event
from config import PID_DIR

TRADER_PID_FILE = PID_DIR / "trader.pid"
VALID_ACTIONS = frozenset({"hold", "open", "close", "close_all"})


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if sys.platform == "win32":
        try:
            out = subprocess.check_output(
                ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
                stderr=subprocess.DEVNULL,
                text=True,
                timeout=5,
            )
            line = out.strip().lower()
            return str(pid) in line and "no tasks" not in line
        except (subprocess.SubprocessError, FileNotFoundError, ValueError):
            return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _trader_pids(exclude: int | None = None) -> list[int]:
    """Find running trader.agent PIDs (Windows + Unix)."""
    mine = exclude or os.getpid()
    found: list[int] = []
    try:
        if sys.platform == "win32":
            out = subprocess.check_output(
                [
                    "powershell",
                    "-NoProfile",
                    "-Command",
                    "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
                    "Where-Object { $_.CommandLine -match '(-m trader\\.agent|trader\\\\__main__\\.py)' } | "
                    "Select-Object -ExpandProperty ProcessId",
                ],
                stderr=subprocess.DEVNULL,
                text=True,
                timeout=15,
            )
            for line in out.splitlines():
                line = line.strip()
                if line.isdigit():
                    pid = int(line)
                    if pid != mine:
                        found.append(pid)
        else:
            out = subprocess.check_output(["pgrep", "-f", "-m trader.agent"], text=True, timeout=10)
            for line in out.splitlines():
                if line.strip().isdigit():
                    pid = int(line.strip())
                    if pid != mine:
                        found.append(pid)
    except (subprocess.SubprocessError, FileNotFoundError, ValueError):
        pass
    return found


def kill_duplicate_traders(exclude_pid: int | None = None) -> int:
    """Terminate extra trader.agent processes. Returns count killed."""
    killed = 0
    for pid in _trader_pids(exclude_pid):
        try:
            if sys.platform == "win32":
                subprocess.run(
                    ["taskkill", "/PID", str(pid), "/F"],
                    check=False,
                    capture_output=True,
                    timeout=10,
                )
            else:
                os.kill(pid, 15)
            killed += 1
            log_event("system", "Duplicate trader stopped", f"pid {pid}")
        except OSError:
            pass
    return killed


def acquire_trader_lock() -> bool:
    """Ensure only one trader.agent runs."""
    PID_DIR.mkdir(parents=True, exist_ok=True)
    my_pid = os.getpid()

    if TRADER_PID_FILE.is_file():
        try:
            old = int(TRADER_PID_FILE.read_text(encoding="utf-8").strip())
            if old == my_pid:
                return True
            if _pid_alive(old):
                log_event("system", "Trader lock held", f"another trader running (pid {old})")
                return False
        except (ValueError, OSError):
            pass
        try:
            TRADER_PID_FILE.unlink(missing_ok=True)
        except OSError:
            pass

    TRADER_PID_FILE.write_text(str(my_pid), encoding="utf-8")
    return True


def release_trader_lock() -> None:
    my_pid = os.getpid()
    try:
        if TRADER_PID_FILE.is_file() and int(TRADER_PID_FILE.read_text(encoding="utf-8").strip()) == my_pid:
            TRADER_PID_FILE.unlink(missing_ok=True)
    except (ValueError, OSError):
        pass


def normalize_decision(raw: dict[str, Any]) -> dict[str, Any]:
    """Reject API error blobs and invalid actions before execution."""
    if not isinstance(raw, dict):
        raise ValueError("decision is not a dict")
    if raw.get("error"):
        raise ValueError(f"API error in decision: {raw.get('error')}")
    action = str(raw.get("action") or "hold").lower().strip()
    if action not in VALID_ACTIONS:
        raise ValueError(f"invalid action: {action!r}")
    raw["action"] = action
    if action == "open" and not raw.get("instId"):
        raise ValueError("open requires instId")
    if action == "close" and not raw.get("instId"):
        raise ValueError("close requires instId")
    return raw
