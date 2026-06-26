"""Performance baseline — track improvement from post-learning-fix + capital injection."""

from __future__ import annotations

import json
import time
from typing import Any

from activity_log import log_event
from config import DATA_DIR
from trader.pnl_tracker import performance_summary

TRACKING_FILE = DATA_DIR / "performance_tracking.jsonl"
LEARNING_FIX_TAG = "realized_pnl_v1"
DEFAULT_EXPECTED_INJECTION_USD = 2.41
INJECTION_DETECT_MIN_USD = 1.50  # minimum equity jump to confirm deposit


def _baseline(state: dict[str, Any]) -> dict[str, Any]:
    bl = state.setdefault("performance_baseline", {})
    return bl


def arm_baseline(
    state: dict[str, Any],
    *,
    pre_injection_equity: float,
    expected_injection_usd: float = DEFAULT_EXPECTED_INJECTION_USD,
    note: str = "",
) -> dict[str, Any]:
    """Arm tracking — waits for equity jump matching expected deposit."""
    bl = _baseline(state)
    now = time.time()
    bl.update(
        {
            "armed": True,
            "active": False,
            "armed_at": now,
            "learning_fix_tag": LEARNING_FIX_TAG,
            "expected_injection_usd": expected_injection_usd,
            "pre_injection_equity": round(pre_injection_equity, 6),
            "expected_post_equity": round(pre_injection_equity + expected_injection_usd, 6),
            "note": note or "Awaiting USDT deposit — baseline starts on detection",
        }
    )
    log_event(
        "system",
        "Baseline armed",
        f"pre=${pre_injection_equity:.4f} + ${expected_injection_usd:.2f} → expect ~${bl['expected_post_equity']:.2f}",
        {"baseline": bl},
    )
    return bl


def activate_baseline(state: dict[str, Any], account: dict[str, Any], *, reason: str) -> dict[str, Any]:
    """Lock baseline at current equity — all progress measured from here."""
    equity = float(account.get("equity") or 0)
    return lock_baseline_at(state, account, equity, reason=reason)


def lock_baseline_at(
    state: dict[str, Any],
    account: dict[str, Any],
    equity: float,
    *,
    reason: str,
    user_set: bool = False,
) -> dict[str, Any]:
    """Lock or re-lock baseline at a specific equity (user or auto activation)."""
    eq = round(float(equity), 6)
    if eq <= 0:
        raise ValueError("baseline equity must be positive")

    perf = performance_summary(state)
    bl = _baseline(state)
    now = time.time()
    current = float(account.get("equity") or eq)
    bl.update(
        {
            "armed": False,
            "active": True,
            "activated_at": now,
            "activation_reason": reason,
            "baseline_equity": eq,
            "baseline_peak": round(max(eq, current), 6),
            "baseline_available": round(float(account.get("available") or 0), 6),
            "baseline_positions": len(account.get("positions") or []),
            "cycles_at_start": int(state.get("cycles") or 0),
            "lessons_at_start": len(state.get("lessons") or []),
            "realized_pnl_at_start": perf.get("total_realized_pnl", 0),
            "closed_trades_at_start": perf.get("closed_trades", 0),
            "learning_fix_tag": LEARNING_FIX_TAG,
            "user_set": bool(user_set),
            "user_set_at": now if user_set else bl.get("user_set_at"),
        }
    )
    _append_tracking(
        {
            "event": "baseline_activated",
            "ts": now,
            "equity": eq,
            "reason": reason,
            "user_set": user_set,
            "baseline": bl,
        }
    )
    log_event(
        "system",
        "Performance baseline ACTIVE",
        f"${eq:.4f} — tracking from here ({reason})",
        {"baseline": bl},
    )
    append_research_note(
        state,
        f"Baseline locked at ${eq:.4f}. All progress measured from here ({reason}).",
    )
    return bl


def set_user_baseline(
    state: dict[str, Any],
    account: dict[str, Any],
    *,
    equity: float | None = None,
    reason: str = "user set via dashboard",
) -> dict[str, Any]:
    """Set baseline equity (and thus Baseline Δ) from operator input."""
    eq = float(equity if equity is not None else account.get("equity") or 0)
    return lock_baseline_at(state, account, eq, reason=reason, user_set=True)


def parse_baseline_command(message: str) -> dict[str, Any] | None:
    """Parse chat/dashboard text like 'set baseline to 3.75' or 'reset baseline'."""
    import re

    text = (message or "").strip()
    if not text:
        return None
    low = text.lower()

    if re.search(r"\b(?:set|reset)\s+baseline\b", low) or re.search(r"\bbaseline\s+(?:to|at|=)\b", low):
        m = re.search(
            r"(?:set|reset)\s+baseline(?:\s+(?:to|at|=))?\s*\$?\s*([\d]+(?:\.\d+)?)",
            text,
            re.I,
        )
        if not m:
            m = re.search(r"baseline\s+(?:to|at|=)\s*\$?\s*([\d]+(?:\.\d+)?)", text, re.I)
        if m:
            return {"use_current": False, "equity": float(m.group(1)), "reason": f"user chat: {text[:120]}"}
        return {"use_current": True, "equity": None, "reason": f"user chat: {text[:120]}"}

    m = re.search(r"^baseline\s+\$?\s*([\d]+(?:\.\d+)?)\s*$", text, re.I)
    if m:
        return {"use_current": False, "equity": float(m.group(1)), "reason": f"user chat: {text[:120]}"}

    return None


def append_research_note(state: dict[str, Any], note: str) -> None:
    from trader.state import append_research

    append_research(state, note)


def try_detect_injection(state: dict[str, Any], account: dict[str, Any]) -> dict[str, Any] | None:
    """Activate baseline when deposit detected (equity jump vs pre-injection snapshot)."""
    bl = _baseline(state)
    if bl.get("active"):
        return bl
    if not bl.get("armed"):
        return None

    equity = float(account.get("equity") or 0)
    pre = float(bl.get("pre_injection_equity") or 0)
    expected = float(bl.get("expected_injection_usd") or DEFAULT_EXPECTED_INJECTION_USD)
    jump = equity - pre

    if jump >= INJECTION_DETECT_MIN_USD and equity >= pre + expected * 0.75:
        return activate_baseline(
            state,
            account,
            reason=f"deposit detected (+${jump:.4f} from ${pre:.4f})",
        )
    return None


def update_baseline_peak(state: dict[str, Any], equity: float) -> None:
    bl = _baseline(state)
    if not bl.get("active"):
        return
    peak = float(bl.get("baseline_peak") or bl.get("baseline_equity") or 0)
    if equity > peak:
        bl["baseline_peak"] = round(equity, 6)
        bl["baseline_peak_ts"] = time.time()


def realized_pnl_since_baseline(state: dict[str, Any]) -> float:
    bl = _baseline(state)
    if not bl.get("active"):
        return 0.0
    since = float(bl.get("activated_at") or 0)
    total = 0.0
    for entry in state.get("pnl_ledger", {}).get("entries") or []:
        if float(entry.get("ts") or 0) >= since:
            total += float(entry.get("realized_pnl") or 0)
    return round(total, 6)


def progress_summary(state: dict[str, Any], account: dict[str, Any]) -> dict[str, Any]:
    bl = _baseline(state)
    equity = float(account.get("equity") or 0)
    perf = performance_summary(state)

    if not bl.get("active"):
        return {
            "active": False,
            "armed": bool(bl.get("armed")),
            "learning_fix_tag": LEARNING_FIX_TAG,
            "pre_injection_equity": bl.get("pre_injection_equity"),
            "expected_injection_usd": bl.get("expected_injection_usd"),
            "expected_post_equity": bl.get("expected_post_equity"),
            "current_equity": round(equity, 6),
            "awaiting_deposit": bool(bl.get("armed")),
            "equity_until_baseline": round(
                max(0.0, float(bl.get("expected_post_equity") or 0) - equity), 6
            )
            if bl.get("armed")
            else None,
        }

    base = float(bl.get("baseline_equity") or 0)
    peak = float(bl.get("baseline_peak") or base)
    pnl_since = realized_pnl_since_baseline(state)
    trading_pnl = equity - base
    cycles = int(state.get("cycles") or 0) - int(bl.get("cycles_at_start") or 0)
    activated = float(bl.get("activated_at") or time.time())
    hours = max(0.01, (time.time() - activated) / 3600)

    return {
        "active": True,
        "armed": False,
        "learning_fix_tag": bl.get("learning_fix_tag"),
        "activated_at": bl.get("activated_at"),
        "activation_reason": bl.get("activation_reason"),
        "baseline_equity": base,
        "baseline_peak": peak,
        "current_equity": round(equity, 6),
        "equity_change_usd": round(equity - base, 6),
        "equity_change_pct": round((equity - base) / base * 100, 2) if base > 0 else 0,
        "drawdown_from_baseline_peak_pct": round((peak - equity) / peak * 100, 2) if peak > 0 else 0,
        "realized_pnl_since_baseline": pnl_since,
        "closed_trades_since_baseline": max(
            0,
            perf.get("closed_trades", 0) - int(bl.get("closed_trades_at_start") or 0),
        ),
        "realized_wins_since_baseline": _count_since(state, "win"),
        "realized_losses_since_baseline": _count_since(state, "loss"),
        "cycles_since_baseline": cycles,
        "lessons_since_baseline": max(0, len(state.get("lessons") or []) - int(bl.get("lessons_at_start") or 0)),
        "hours_since_baseline": round(hours, 2),
        "improving": equity > base or pnl_since > 0,
        "user_set": bool(bl.get("user_set")),
        "user_set_at": bl.get("user_set_at"),
    }


def _count_since(state: dict[str, Any], kind: str) -> int:
    bl = _baseline(state)
    since = float(bl.get("activated_at") or 0)
    from trader.pnl_tracker import MIN_REALIZED_LOSS_USD, MIN_REALIZED_WIN_USD

    count = 0
    for entry in state.get("pnl_ledger", {}).get("entries") or []:
        if float(entry.get("ts") or 0) < since:
            continue
        pnl = float(entry.get("realized_pnl") or 0)
        if kind == "win" and pnl >= MIN_REALIZED_WIN_USD:
            count += 1
        if kind == "loss" and pnl <= -MIN_REALIZED_LOSS_USD:
            count += 1
    return count


def _append_tracking(row: dict[str, Any]) -> None:
    TRACKING_FILE.parent.mkdir(parents=True, exist_ok=True)
    with TRACKING_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def snapshot_if_due(
    state: dict[str, Any],
    account: dict[str, Any],
    *,
    every_cycles: int = 5,
) -> None:
    """Append progress snapshot to tracking file periodically."""
    bl = _baseline(state)
    if not bl.get("active"):
        return
    cycle = int(state.get("cycles") or 0)
    last = int(bl.get("last_snapshot_cycle") or 0)
    if cycle - last < every_cycles:
        return
    prog = progress_summary(state, account)
    _append_tracking({"event": "snapshot", "ts": time.time(), "cycle": cycle, **prog})
    bl["last_snapshot_cycle"] = cycle


def ensure_baseline_armed(state: dict[str, Any], account: dict[str, Any]) -> None:
    """On startup: arm if never set; detect injection if already armed."""
    bl = _baseline(state)
    if bl.get("active"):
        return
    if not bl.get("armed"):
        equity = float(account.get("equity") or 0)
        arm_baseline(
            state,
            pre_injection_equity=equity,
            expected_injection_usd=DEFAULT_EXPECTED_INJECTION_USD,
            note="Auto-armed on startup — deposit $2.41 USDT to begin tracked run",
        )
    else:
        try_detect_injection(state, account)


def baseline_context_for_llm(state: dict[str, Any], account: dict[str, Any]) -> dict[str, Any]:
    return progress_summary(state, account)
