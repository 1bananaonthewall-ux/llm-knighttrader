"""TP/SL attachment using live mark price — avoids stale-scan trigger rejections."""

from __future__ import annotations

from typing import Any

from activity_log import log_event


def resolve_mark_price(
    client: Any,
    inst_id: str,
    *,
    account: dict[str, Any] | None = None,
    fallback: float = 0.0,
) -> float:
    """Best available mark: open position → account snapshot → candles → fallback."""
    if account:
        for pos in account.get("positions") or []:
            if str(pos.get("instId") or "") != inst_id:
                continue
            mark = float(pos.get("mark") or pos.get("markPrice") or 0)
            if mark > 0:
                return mark
            entry = float(pos.get("entry") or pos.get("avgPx") or pos.get("averagePrice") or 0)
            if entry > 0:
                return entry

    try:
        from blofin.account_cache import get_account_snapshot

        snap = get_account_snapshot(force=True)
        for pos in snap.get("positions") or []:
            if str(pos.get("instId") or "") != inst_id:
                continue
            mark = float(pos.get("mark") or pos.get("markPrice") or 0)
            if mark > 0:
                return mark
    except Exception:
        pass

    try:
        rows = client.get_candles(inst_id, "1m", "2")
        if rows:
            px = float(rows[-1][4])
            if px > 0:
                return px
    except Exception:
        pass

    return float(fallback or 0)


def compute_tpsl_triggers(
    side: str,
    mark: float,
    *,
    tp_pct: float = 2.0,
    sl_pct: float = 1.0,
    leverage: int = 3,
) -> tuple[float, float, str]:
    """Return (tp, sl, close_side) with triggers valid vs latest mark."""
    if mark <= 0:
        raise ValueError("mark price required for TP/SL")

    tp_r = max(abs(float(tp_pct)) / 100.0, 0.005)
    sl_r = max(abs(float(sl_pct)) / 100.0, 0.005)
    if int(leverage) > 10:
        sl_r = min(sl_r, 0.015)

    # Small buffer so exchange accepts triggers vs last price.
    buf = 0.002

    if side == "buy":
        close_side = "sell"
        tp = mark * (1 + tp_r)
        sl = mark * (1 - sl_r)
        tp = max(tp, mark * (1 + buf))
        sl = min(sl, mark * (1 - buf))
    else:
        close_side = "buy"
        tp = mark * (1 - tp_r)
        sl = mark * (1 + sl_r)
        tp = min(tp, mark * (1 - buf))
        sl = max(sl, mark * (1 + buf))

    return tp, sl, close_side


def attach_tpsl_safe(
    client: Any,
    *,
    inst_id: str,
    side: str,
    contracts: str,
    mark: float,
    tp_pct: float = 2.0,
    sl_pct: float = 1.0,
    leverage: int = 3,
    account: dict[str, Any] | None = None,
    max_attempts: int = 4,
) -> dict[str, Any]:
    """Attach TP/SL; refresh mark and nudge triggers on BloFin rejections."""
    mark_px = float(mark or 0)
    if mark_px <= 0:
        mark_px = resolve_mark_price(client, inst_id, account=account)

    last: dict[str, Any] = {"code": "1", "msg": "no mark price"}
    for attempt in range(max_attempts):
        if mark_px <= 0:
            mark_px = resolve_mark_price(client, inst_id, account=account)
        if mark_px <= 0:
            break

        tp, sl, close_side = compute_tpsl_triggers(
            side, mark_px, tp_pct=tp_pct, sl_pct=sl_pct, leverage=leverage
        )
        last = client.attach_tpsl(inst_id, None, close_side, contracts, tp, sl)
        if str(last.get("code")) in ("0", "0.0"):
            log_event(
                "trade",
                f"TP/SL attached {inst_id}",
                f"mark={mark_px:.6f} tp={tp:.6f} sl={sl:.6f}",
                {"instId": inst_id, "attempt": attempt + 1},
            )
            return last

        _, err = client.order_rejected(last)
        err_l = (err or str(last.get("msg") or "")).lower()
        log_event(
            "trade",
            f"TP/SL retry {inst_id}",
            f"attempt {attempt + 1}: {err_l[:160]}",
            {"mark": mark_px, "tp": tp, "sl": sl},
        )

        if side == "buy" and "lower" in err_l:
            mark_px = resolve_mark_price(client, inst_id, account=account) or mark_px * 0.998
        elif side == "sell" and "higher" in err_l:
            mark_px = resolve_mark_price(client, inst_id, account=account) or mark_px * 1.002
        else:
            mark_px = resolve_mark_price(client, inst_id, account=account) or mark_px

    return last
