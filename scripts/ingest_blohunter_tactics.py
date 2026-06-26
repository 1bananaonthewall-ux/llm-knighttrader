#!/usr/bin/env python3
"""Ingest BloHunter tactics from blohunter-connect + blohunter.com into data/blohunter_tactics.md."""

from __future__ import annotations

import argparse
import re
import sys
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from trader.blohunter_knowledge import BLOHUNTER_SITE, DEFAULT_CONNECT_PATH, TACTICS_FILE

CONNECT_FILES = [
    "src/trading/recovery.js",
    "src/trading/recoveryPlanner.js",
    "src/trading/holdTakeProfit.js",
    "src/trading/managementMode.js",
    "src/trading/dimensionControlLoop.js",
    "src/trading/executor/autoDelever.js",
    "src/trading/executor/constants.js",
    "src/trading/executorSizing.js",
    "src/trading/executor/guards.js",
    "src/trading/executor/handleOpen.js",
    "src/policy/verifier.js",
    "manifest.json",
]


def _read_snippet(path: Path, limit: int = 4000) -> str:
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")[:limit]


def _extract_constants(text: str) -> list[str]:
    found: list[str] = []
    patterns = [
        r"export const ([A-Z_][A-Z0-9_]*)\s*=\s*(\[[^\]]+\]|[^;]+);",
        r"const ([A-Z_][A-Z0-9_]*)\s*=\s*(\d+(?:\.\d+)?);",
        r"export const ([A-Z_][A-Z0-9_]*_PCT)\s*=\s*(\d+(?:\.\d+)?);",
    ]
    for pat in patterns:
        for match in re.finditer(pat, text):
            name, val = match.group(1), match.group(2).strip()
            if len(val) > 120:
                val = val[:117] + "..."
            found.append(f"- `{name}` = {val}")
    return found


def _fetch_site_blurb() -> str:
    for url in (BLOHUNTER_SITE, f"{BLOHUNTER_SITE}/"):
        try:
            with urllib.request.urlopen(url, timeout=12) as resp:
                html = resp.read(8000).decode("utf-8", errors="replace")
            title = re.search(r"<title>([^<]+)</title>", html, re.I)
            return (
                f"Fetched {url} ({resp.status}). "
                f"Title: {(title.group(1).strip() if title else 'BloHunter Trading')}. "
                "Public trade lifecycle stream: `/api/public/trades/v3/stream` (signed SSE)."
            )
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last = str(exc)
    return f"Site fetch skipped ({last}). Tactics sourced from blohunter-connect extension."


def build_tactics_markdown(connect_dir: Path) -> str:
    version = ""
    manifest = connect_dir / "manifest.json"
    if manifest.is_file():
        import json

        data = json.loads(manifest.read_text(encoding="utf-8"))
        version = data.get("version", "?")
        desc = data.get("description", "")
    else:
        desc = ""

    site_note = _fetch_site_blurb()
    generated = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")

    sections = [
        "# BloHunter Tactics (LLM KnightTrader training corpus)",
        "",
        f"Generated: {generated}",
        f"Source extension: `{connect_dir}` (BloHunter Connect v{version})",
        f"Mothership: [{BLOHUNTER_SITE}]({BLOHUNTER_SITE})",
        f"Site note: {site_note}",
        "",
        desc,
        "",
        "## Mission alignment",
        "",
        "BloHunter is a **gateway-managed futures mirroring system**. The mothership publishes "
        "signed lifecycle events (open, DCA, risk-adjust, state, close). The Connect extension "
        "executes on BloFin with strict safety policy. LLM KnightTrader should **emulate these "
        "disciplines** on the same BloFin net_mode account: scale in on planned drawdown, protect "
        "margin, trail winners, never close tiny winners, and gate new risk when the book is hot.",
        "",
        "## Lifecycle modes (one word = one concept)",
        "",
        "| Mode | Meaning | LLM behavior |",
        "|------|---------|--------------|",
        "| `active` | Gateway actively managing; position is live in upstream book | Prefer follow/hold; opens only when policy + dimension allow |",
        "| `hold` | Gateway parked underwater trade; local spectator | Do not fight gateway; manage local profit with trailing TP if in profit |",
        "| `recovery` | Position dropped from gateway snapshot | Run local DCA ladder + trailing TP; full local lifecycle ownership |",
        "| `inactive` | No managed position | Eligible for new opens if gates pass |",
        "",
        "**Rule:** only `active` lifecycle may receive a fresh **open**. DCAs add to existing exposure.",
        "",
        "## Universal floors and ceilings",
        "",
        "- **Never close under +5% PnL** (NTP floor) — applies to recovery, hold-TTP, and normal closes.",
        "- **Max leverage 3x** — client policy ceiling; discrete steps **1x / 2x / 3x** only.",
        "- **Per-position margin cap** — max position % × equity = margin budget (not notional).",
        "- **Max position % client ceiling: 50%** (policy may be lower; client clamps never loosens).",
        "- **BloFin net_mode** — one-way positions; no hedge-mode doubles.",
        "",
        "## DCA / recovery ladder (loss side)",
        "",
        "- Recovery drawdown triggers (add size): **-60%, -70%, -80%, -90%**.",
        "- Recovery reset threshold: **-50%** (re-arm logic).",
        "- **DCAs into existing positions are never blocked** by the Dimension gate.",
        "- After **insufficient margin on DCA**, apply **60s cooldown** before retrying.",
        "- **Cold-start window** can block DCAs right after connect boot (avoid blind catch-up).",
        "",
        "## Trailing take-profit (profit side — bell curve)",
        "",
        "- **Activation:** trailing TP arms when peak PnL reaches **+15%**.",
        "- **Trail distance** widens with peak (bell curve): ~10% trail at +15%, widens toward **30%** "
        "at **+60%** peak, narrows back toward **10%** by **+200%** peak.",
        "- **HOLD-TTP:** on gateway-`hold` positions, bank **local** profit when client is green but "
        "gateway is still underwater (prevents stranded local winners).",
        "",
        "## Dimension control loop (new opens only)",
        "",
        "Dimension is an **account heat** safety lever (not a user knob):",
        "",
        "- Range **30 (aggressive floor) – 80 (conservative ceiling)**, start ~50.",
        "- Target utilization **70%** of equity; drawdown cap **40%** amplifies heat.",
        "- **High heat → raise Dimension fast** (~63% of gap per 4 min) → blocks expensive new opens first.",
        "- **Low heat → loosen slowly** (~35% of (D−floor) per day toward floor).",
        "- **Open gate:** must afford ≥ `dimension` DCAs within per-position margin cap at order leverage.",
        "- If autopilot stale (>6h), gate falls back to conservative floor (**30**).",
        "",
        "## Auto-deleveraging",
        "",
        "- When **used margin ≥ 50%** of per-position cap **and** still at baseline leverage, "
        "step leverage down (3→2→1) as local protection.",
        "- Risk-adjustment retries on **30 min** interval when upstream delever signals fail.",
        "",
        "## Open / execution gates (check in order)",
        "",
        "1. Symbol not blacklisted / supported on BloFin swaps",
        "2. Not liquidation-suppressed (don't reopen blown symbols)",
        "3. BloFin rate-limit / API cooldown inactive",
        "4. Signed server policy valid (max leverage, max position %)",
        "5. Exposure / demo cap / active-trade-area lifecycle check",
        "6. **Dimension affordability gate** for fresh opens",
        "7. Available margin > minimum ($0.10 for KnightTrader)",
        "8. Place market order; persist state; run post-open auto-delever check",
        "",
        "## Sizing model",
        "",
        "- **Percent-of-balance** notional × leverage, or **min-qty multiplier** ladder: **2,4,6,8,10**.",
        "- Event sizing can upshift multiplier steps (`relative_to_client_base`) or force absolute min qty.",
        "- Compare new order **margin** (notional ÷ leverage) against per-position margin cap.",
        "",
        "## Risk management playbook for LLM decisions",
        "",
        "When emitting JSON trade decisions:",
        "",
        "1. **If positions exist** → prefer `hold`, `close`, or `close_all` over new `open` unless scan score ≥3 "
        "and confidence ≥65 with clear margin headroom.",
        "2. **close_all** when multiple losers, margin stress, or dimension heat would block recovery DCAs.",
        "3. **open** only on strong momentum setups with affordable dimension count and leverage ≤3.",
        "4. Set **tp_pct / sl_pct** consistent with BloHunter style: let winners run with trailing logic; "
        "don't clip below +5%; use staged adds on drawdown rather than averaging blindly into heat.",
        "5. On **rate limit** → hold, use cached account, log error, retry next cycle (never spam API).",
        "6. Cite which BloHunter rule drove the decision in `research` / `reasoning`.",
        "",
        "## Mothership integration notes",
        "",
        f"- Homepage: {BLOHUNTER_SITE}",
        "- Extension mirrors SSE v3: `trade-opened`, `trade-dca`, `trade-risk-adjustment`, "
        "`trade-state`, `trade-closed`, `resync-required`.",
        "- Events are **Ed25519 signed**; policy document sets `maxLeverage` and `maxPositionSizePercent`.",
        "- LLM KnightTrader is autonomous but should stay **policy-compatible** with BloHunter discipline.",
        "",
        "## Extracted constants (from extension source)",
        "",
    ]

    for rel in CONNECT_FILES:
        snippet = _read_snippet(connect_dir / rel)
        if not snippet:
            continue
        consts = _extract_constants(snippet)
        if consts:
            sections.append(f"### `{rel}`")
            sections.extend(consts)
            sections.append("")

    return "\n".join(sections).strip() + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest BloHunter tactics into LLM KnightTrader")
    parser.add_argument(
        "--connect",
        type=Path,
        default=DEFAULT_CONNECT_PATH,
        help="Path to blohunter-connect folder",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=TACTICS_FILE,
        help="Output markdown path",
    )
    args = parser.parse_args()

    if not args.connect.is_dir():
        print(f"ERROR: blohunter-connect not found at {args.connect}", file=sys.stderr)
        sys.exit(1)

    md = build_tactics_markdown(args.connect)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(md, encoding="utf-8")
    print(f"Wrote {len(md)} chars -> {args.out}")


if __name__ == "__main__":
    main()
