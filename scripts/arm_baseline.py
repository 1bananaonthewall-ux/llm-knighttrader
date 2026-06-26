"""Arm performance baseline before USDT injection."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from blofin.account_cache import get_account_snapshot
from trader.baseline import DEFAULT_EXPECTED_INJECTION_USD, arm_baseline, progress_summary, try_detect_injection
from trader.state import load_state, save_state


def main() -> None:
    import argparse

    p = argparse.ArgumentParser(description="Arm or check performance baseline")
    p.add_argument("--inject", type=float, default=DEFAULT_EXPECTED_INJECTION_USD, help="Expected USDT deposit")
    p.add_argument("--force-refresh", action="store_true", help="Force BloFin account refresh")
    args = p.parse_args()

    state = load_state()
    account = get_account_snapshot(force=args.force_refresh)
    equity = float(account.get("equity") or 0)

    bl = state.get("performance_baseline") or {}
    if bl.get("active"):
        prog = progress_summary(state, account)
        print("Baseline already ACTIVE")
        print(f"  Started: ${prog['baseline_equity']:.4f}")
        print(f"  Now:     ${prog['current_equity']:.4f} ({prog['equity_change_pct']:+.2f}%)")
        print(f"  Realized since baseline: ${prog['realized_pnl_since_baseline']:.4f}")
        return

    if bl.get("armed"):
        activated = try_detect_injection(state, account)
        save_state(state)
        prog = progress_summary(state, account)
        if activated and activated.get("active"):
            print(f"Injection detected — baseline ACTIVE at ${prog.get('current_equity', equity):.4f}")
        else:
            pre = float(bl.get("pre_injection_equity") or equity)
            print(f"Baseline ARMED — waiting for deposit")
            print(f"  Pre-injection snapshot: ${pre:.4f}")
            print(f"  Current equity:         ${equity:.4f} (+${equity - pre:.4f})")
            print(f"  Expected after +${args.inject:.2f}: ~${pre + args.inject:.2f}")
        return

    arm_baseline(state, pre_injection_equity=equity, expected_injection_usd=args.inject)


if __name__ == "__main__":
    main()
