"""Watch activity.jsonl every minute for N minutes; print new events + errors."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG = ROOT / "data" / "activity.jsonl"
OUT = ROOT / "data" / "watch_session.jsonl"


def tail_since(since_ts: float) -> list[dict]:
    if not LOG.is_file():
        return []
    out = []
    for line in LOG.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        if float(ev.get("ts") or 0) > since_ts:
            out.append(ev)
    return out


def main() -> None:
    minutes = int(sys.argv[1]) if len(sys.argv) > 1 else 12
    since = time.time()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("a", encoding="utf-8") as fp:
        for i in range(minutes):
            time.sleep(60)
            now = time.time()
            batch = tail_since(since)
            since = now
            errors = [e for e in batch if e.get("type") == "error"]
            summary = {
                "minute": i + 1,
                "ts": now,
                "events": len(batch),
                "errors": len(errors),
                "error_titles": [e.get("title") for e in errors],
                "last_titles": [e.get("title") for e in batch[-5:]],
            }
            fp.write(json.dumps(summary) + "\n")
            fp.flush()
            print(json.dumps(summary), flush=True)


if __name__ == "__main__":
    main()
