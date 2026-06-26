"""Kill all KnightTrader python agent processes."""
from __future__ import annotations

import json
import os
import subprocess
import sys

MODULES = (
    "trader.agent",
    "dashboard.server",
    "monitor.agent",
    "babysit_12m",
    "babysit_perpetual",
    "watch_and_fix",
    "watch_logs",
)
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def _matches(cmd: str) -> bool:
    if not any(m in cmd for m in MODULES):
        return False
    if ROOT.lower() in cmd.lower():
        return True
    if any(f"-m {m}" in cmd for m in MODULES):
        return True
    if "hermes-llm-trader" in cmd.lower():
        return True
    return False


def main() -> int:
    script = (
        "Get-CimInstance Win32_Process | "
        "Where-Object { $_.Name -eq 'python.exe' } | "
        "Select-Object ProcessId, CommandLine | ConvertTo-Json -Compress"
    )
    try:
        raw = subprocess.check_output(["powershell", "-NoProfile", "-Command", script], text=True).strip()
    except subprocess.SubprocessError:
        print("none")
        return 0
    if not raw:
        print("none")
        return 0
    rows = json.loads(raw)
    if isinstance(rows, dict):
        rows = [rows]
    killed = 0
    me = os.getpid()
    for row in rows:
        pid = int(row["ProcessId"])
        if pid == me:
            continue
        cmd = row.get("CommandLine") or ""
        if not _matches(cmd):
            continue
        subprocess.run(["taskkill", "/F", "/PID", str(pid)], check=False, stdout=subprocess.DEVNULL)
        print("killed", pid, cmd[:110])
        killed += 1
    print("total killed", killed)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
