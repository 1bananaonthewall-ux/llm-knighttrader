"""Realized PnL tracking — success lessons only when money is actually made."""

from __future__ import annotations

import time
from typing import Any

MIN_REALIZED_WIN_USD = 0.02
MIN_REALIZED_LOSS_USD = 0.01


def _ledger(state: dict[str, Any]) -> dict[str, Any]:
    lg = state.setdefault("pnl_ledger", {"entries": [], "opens": {}})
    return lg


def drawdown_state(account: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    peak = float(state.get("peak_equity") or 0)
    equity = float(account.get("equity") or 0)
    if peak <= 0:
        return {"sub_peak": False, "recovery_mode": False, "drawdown_pct": 0.0, "equity": equity, "peak": peak}
    dd = max(0.0, (peak - equity) / peak)
    return {
        "sub_peak": equity < peak * 0.98,
        "recovery_mode": dd >= 0.15,
        "drawdown_pct": round(dd * 100, 1),
        "equity": equity,
        "peak": peak,
    }


def record_open_entry(
    state: dict[str, Any],
    *,
    inst_id: str,
    side: str,
    price: float,
    size: str,
    leverage: int,
) -> None:
    lg = _ledger(state)
    lg["opens"][inst_id] = {
        "ts": time.time(),
        "side": side,
        "price": price,
        "size": size,
        "leverage": leverage,
    }


def capture_close_pnl(pos: dict[str, Any]) -> float:
    """Use unrealized PnL at close time as realized PnL for full closes."""
    return float(pos.get("upl") or pos.get("unrealizedPnl") or pos.get("unrealizedPnlUsd") or 0)


def record_close_entry(
    state: dict[str, Any],
    *,
    inst_id: str,
    side: str | None,
    realized_pnl: float,
) -> dict[str, Any]:
    lg = _ledger(state)
    open_row = lg["opens"].pop(inst_id, {})
    entry = {
        "ts": time.time(),
        "instId": inst_id,
        "side": side or open_row.get("side"),
        "realized_pnl": round(realized_pnl, 6),
        "entry_price": open_row.get("price"),
        "leverage": open_row.get("leverage"),
        "hold_sec": int(time.time() - float(open_row.get("ts") or time.time())),
    }
    entries = list(lg.get("entries") or [])
    entries.append(entry)
    lg["entries"] = entries[-100:]
    return entry


def performance_summary(state: dict[str, Any]) -> dict[str, Any]:
    entries = list(_ledger(state).get("entries") or [])
    wins = [e for e in entries if float(e.get("realized_pnl") or 0) >= MIN_REALIZED_WIN_USD]
    losses = [e for e in entries if float(e.get("realized_pnl") or 0) <= -MIN_REALIZED_LOSS_USD]
    total_pnl = sum(float(e.get("realized_pnl") or 0) for e in entries)
    best = sorted(wins, key=lambda e: float(e.get("realized_pnl") or 0), reverse=True)[:3]
    return {
        "closed_trades": len(entries),
        "realized_wins": len(wins),
        "realized_losses": len(losses),
        "total_realized_pnl": round(total_pnl, 4),
        "best_wins": [
            {
                "instId": b.get("instId"),
                "pnl": b.get("realized_pnl"),
                "leverage": b.get("leverage"),
                "hold_min": int(float(b.get("hold_sec") or 0) // 60),
            }
            for b in best
        ],
        "worst_losses": [
            {
                "instId": e.get("instId"),
                "pnl": e.get("realized_pnl"),
            }
            for e in sorted(losses, key=lambda x: float(x.get("realized_pnl") or 0))[:3]
        ],
    }
