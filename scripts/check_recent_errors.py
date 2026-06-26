import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from trader.agent import _parse_json_response

s = '{"research": "x", "action": "hold", "reasoning": "truncated'
d = _parse_json_response(s)
print("repair ok:", d.get("action"), d.get("research"))

lines = (ROOT / "data" / "activity.jsonl").read_text(encoding="utf-8").splitlines()
restart_ts = 0.0
for line in reversed(lines[-200:]):
    ev = json.loads(line)
    if ev.get("type") == "system" and "started" in str(ev.get("title", "")).lower():
        restart_ts = float(ev.get("ts") or 0)
        break

errs = []
for line in reversed(lines):
    ev = json.loads(line)
    ts = float(ev.get("ts") or 0)
    if ts < restart_ts:
        break
    if ev.get("type") == "error":
        errs.append((ts, ev.get("title"), (ev.get("detail") or "")[:140]))

print(f"restart_ts={restart_ts} errors_since={len(errs)}")
for row in reversed(errs[-15:]):
    print(row)
