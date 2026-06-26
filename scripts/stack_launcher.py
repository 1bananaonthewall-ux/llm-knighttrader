"""Desktop launcher — cold stop or restart the full LLM KnightTrader stack."""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import DASHBOARD_HOST, DASHBOARD_PORT, PID_DIR
from trader.stack_control import (
    _enumerate_python_processes,
    _kill_pid,
    _module_pids,
    _trader_python,
    is_entire_stack_stopped,
    kill_entire_stack,
    running_process_counts,
    stack_status,
    start_single_trader,
)

DASHBOARD_URL = f"http://{DASHBOARD_HOST}:{DASHBOARD_PORT}"


def _write_pid(name: str, pid: int) -> None:
    PID_DIR.mkdir(parents=True, exist_ok=True)
    (PID_DIR / f"{name}.pid").write_text(str(pid), encoding="utf-8")


def _popen_module(module: str) -> subprocess.Popen:
    python_bin = _trader_python()
    kwargs: dict = {
        "cwd": str(ROOT),
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
    }
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
    return subprocess.Popen([python_bin, "-m", module], **kwargs)


def _wait_dashboard_health(timeout_sec: float = 30.0) -> bool:
    deadline = time.time() + timeout_sec
    url = f"{DASHBOARD_URL}/api/health"
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2.0) as resp:
                if resp.status == 200:
                    return True
        except (urllib.error.URLError, TimeoutError, OSError):
            pass
        time.sleep(1.0)
    return False


def _ensure_desktop_shortcuts() -> None:
    script = ROOT / "scripts" / "create_desktop_shortcuts.ps1"
    if not script.is_file():
        return
    subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script)],
        cwd=str(ROOT),
        check=False,
    )


def stop_stack() -> int:
    print("Stopping all LLM KnightTrader processes...")
    killed = kill_entire_stack()
    if killed:
        print(f"  stopped {len(killed)} process(es)")
    time.sleep(1.0)
    extra = kill_entire_stack()
    if extra:
        print(f"  second pass stopped {len(extra)} process(es)")

    counts = running_process_counts()
    if is_entire_stack_stopped():
        print("LLM KnightTrader stopped (dashboard, trader, monitor, watchers).")
        return 0

    print(
        "ERROR: some processes still running — "
        f"dashboard={counts['dashboard']} trader={counts['trader']} "
        f"monitor={counts['monitor']} watchers={counts['watchers']}"
    )
    return 1


def _resolve_module_pid(module: str, *, timeout_sec: float = 15.0) -> int | None:
    """Return a running PID for module once it appears (never kill during wait)."""
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        pids = sorted(set(_module_pids(module)))
        if pids:
            return pids[-1]
        time.sleep(0.5)
    return None


def _dedupe_module(module: str) -> int | None:
    """Keep one process for module; prefer KNIGHTTRADER_PYTHON interpreter."""
    preferred = str(Path(_trader_python()).resolve()).lower()
    pids = sorted(set(_module_pids(module)))
    if not pids:
        return None
    keep = pids[-1]
    for row in _enumerate_python_processes():
        pid = row["pid"]
        if pid not in pids:
            continue
        if preferred in (row.get("cmd") or "").lower():
            keep = pid
            break
    for pid in pids:
        if pid != keep:
            _kill_pid(pid)
    time.sleep(0.5)
    return keep


def start_stack(*, open_browser: bool = False) -> int:
    """Stop everything, then start exactly one dashboard + one trader."""
    code = stop_stack()
    if code != 0:
        print("Warning: cleanup incomplete — attempting fresh start anyway...")

    print("Starting dashboard...")
    dash = _popen_module("dashboard.server")
    time.sleep(2.0)
    if dash.poll() is not None:
        print(f"ERROR: dashboard.server exited immediately (code {dash.returncode})")
        return 1

    if not _wait_dashboard_health():
        print("ERROR: dashboard health check failed")
        return 1

    dash_pid = _resolve_module_pid("dashboard.server")
    if dash_pid is None:
        print("ERROR: dashboard process not found after start")
        return 1
    _write_pid("dashboard", dash_pid)

    print("Starting trader...")
    trader_result = start_single_trader()
    if not trader_result.get("ok"):
        print(f"ERROR: trader failed to start — {trader_result.get('error', 'unknown')}")
        return 1
    trader_pid = int(trader_result["pid"])
    _write_pid("trader", trader_pid)

    counts = running_process_counts()
    stack = stack_status()
    if stack.get("trader", {}).get("status") not in ("online", "duplicate"):
        print(
            f"ERROR: trader not online — "
            f"dashboard={counts['dashboard']} trader={counts['trader']} "
            f"status={stack.get('trader')}"
        )
        return 1
    if counts["dashboard"] < 1:
        print(f"ERROR: dashboard not running (count={counts['dashboard']})")
        return 1

    _ensure_desktop_shortcuts()
    print(f"Dashboard PID {dash_pid} | Trader PID {trader_pid}")
    print(f"LLM KnightTrader ready -> {DASHBOARD_URL}")
    print("Daily use: double-click 'Start LLM KnightTrader' on desktop to restart the stack.")

    if open_browser:
        webbrowser.open(DASHBOARD_URL)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="LLM KnightTrader desktop stack control")
    sub = parser.add_subparsers(dest="command", required=True)

    start_p = sub.add_parser("start", help="Stop all KT processes, then start dashboard + trader")
    start_p.add_argument("--open-browser", action="store_true")

    sub.add_parser("stop", help="Stop all KT processes (dashboard, trader, monitor, watchers)")

    args = parser.parse_args()
    if args.command == "stop":
        return stop_stack()
    return start_stack(open_browser=bool(args.open_browser))


if __name__ == "__main__":
    raise SystemExit(main())
