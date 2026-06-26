import json
import re
from pathlib import Path
from collections import Counter

ROOT = Path(r"C:\Users\mknig\hermes-llm-trader\data")
state = json.loads((ROOT / "state.json").read_text(encoding="utf-8"))
lines = (ROOT / "activity.jsonl").read_text(encoding="utf-8").splitlines()
events = []
for line in lines:
    try:
        events.append(json.loads(line))
    except json.JSONDecodeError:
        pass

eq = []
for e in events:
    if e.get("type") == "account" and "Equity" in str(e.get("title", "")):
        m = re.search(r"Equity \$([0-9.]+)", e.get("title", ""))
        if m:
            eq.append((e["ts"], float(m.group(1))))

errs = [e for e in events if e.get("type") == "error"]
opens = [e for e in events if e.get("type") == "trade" and str(e.get("title", "")).startswith("Opened")]
fails = [e for e in events if e.get("type") == "trade" and "failed" in str(e.get("title", "")).lower()]
holds = [e for e in events if e.get("type") == "llm" and "Decision: hold" in str(e.get("title", ""))]
lessons_ev = [e for e in events if e.get("title") == "Lesson learned"]

# split early vs late by midpoint cycles
mid_ts = events[len(events)//2]["ts"] if events else 0
early_err = sum(1 for e in errs if e["ts"] < mid_ts)
late_err = sum(1 for e in errs if e["ts"] >= mid_ts)
early_open = sum(1 for e in opens if e["ts"] < mid_ts)
late_open = sum(1 for e in opens if e["ts"] >= mid_ts)
early_fail = sum(1 for e in fails if e["ts"] < mid_ts)
late_fail = sum(1 for e in fails if e["ts"] >= mid_ts)

print("=== PERFORMANCE ===")
print(f"cycles: {state.get('cycles')}")
print(f"peak_equity: ${state.get('peak_equity', 0):.4f}")
print(f"current_equity (last log): ${eq[-1][1]:.4f}" if eq else "no equity")
print(f"starting_equity: ${eq[0][1]:.4f}" if eq else "")
if eq:
    print(f"max_logged: ${max(x[1] for x in eq):.4f}")
    print(f"drawdown from peak: {(1 - eq[-1][1]/state.get('peak_equity', eq[-1][1]))*100:.1f}%")

print("\n=== LEARNING ===")
print(f"lessons in state: {len(state.get('lessons') or [])}")
print(f"lesson events in log: {len(lessons_ev)}")
print(f"research notes: {len(state.get('research_notes') or [])}")
cats = Counter(r.get("category") for r in (state.get("lessons") or []))
print("lesson categories:", dict(cats.most_common(8)))
repeated = sorted(state.get("lessons") or [], key=lambda r: int(r.get("count") or 1), reverse=True)[:6]
for r in repeated:
    print(f"  x{r.get('count')} [{r.get('category')}] {r.get('lesson','')[:70]}")

print("\n=== BEHAVIOR early vs late (by log midpoint) ===")
print(f"errors: early={early_err} late={late_err}")
print(f"opens: early={early_open} late={late_open}")
print(f"trade failures: early={early_fail} late={late_fail}")
print(f"hold decisions: {len(holds)}")

print("\n=== RECENT ERRORS ===")
for e in errs[-6:]:
    print(f"  {e.get('title')}: {str(e.get('detail',''))[:80]}")

print("\n=== RECENT RESEARCH (strategy evolution) ===")
for n in (state.get("research_notes") or [])[-4:]:
    print(f"  {n.get('note','')[:100]}")
