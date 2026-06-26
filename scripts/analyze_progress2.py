import json
import re
from pathlib import Path
from collections import Counter

ROOT = Path(r"C:\Users\mknig\hermes-llm-trader\data")
lines = (ROOT / "activity.jsonl").read_text(encoding="utf-8").splitlines()
events = [json.loads(l) for l in lines if l.strip()]

# bucket by cycle-ish windows using ts quartiles
ts_sorted = sorted(e["ts"] for e in events)
q1, q2, q3 = [ts_sorted[int(len(ts_sorted)*p)] for p in (0.25, 0.5, 0.75)]

def bucket(ts):
    if ts < q1: return "Q1_start"
    if ts < q2: return "Q2"
    if ts < q3: return "Q3"
    return "Q4_recent"

def stats(bucket_events):
    errs = [e for e in bucket_events if e.get("type")=="error"]
    opens = [e for e in bucket_events if e.get("type")=="trade" and str(e.get("title","")).startswith("Opened")]
    ok_opens = [e for e in opens if '"code": "0"' in str(e.get("detail","")) or e.get("data",{}).get("response",{}).get("code")=="0"]
    fail_opens = [e for e in opens if "102089" in str(e.get("detail","")) or "103003" in str(e.get("detail","")) or '"code": "1"' in str(e.get("detail",""))]
    holds = [e for e in bucket_events if e.get("type")=="llm" and "Decision: hold" in str(e.get("title",""))]
    lessons = [e for e in bucket_events if e.get("title")=="Lesson learned"]
    eq = []
    for e in bucket_events:
        if e.get("type")=="account" and "Equity" in str(e.get("title","")):
            m = re.search(r"Equity \$([0-9.]+)", e.get("title",""))
            if m: eq.append(float(m.group(1)))
    return {
        "errors": len(errs),
        "opens": len(opens),
        "failed_opens": len(fail_opens),
        "holds": len(holds),
        "lessons": len(lessons),
        "avg_equity": sum(eq)/len(eq) if eq else 0,
        "min_eq": min(eq) if eq else 0,
        "max_eq": max(eq) if eq else 0,
    }

buckets = {}
for e in events:
    b = bucket(e["ts"])
    buckets.setdefault(b, []).append(e)

print("=== QUARTILE EVOLUTION ===")
for name in ["Q1_start", "Q2", "Q3", "Q4_recent"]:
    s = stats(buckets.get(name, []))
    print(name, s)

# successful trades timeline
print("\n=== SUCCESSFUL OPENS (code 0) sample ===")
count = 0
for e in events:
    if e.get("type")=="trade" and str(e.get("title","")).startswith("Opened"):
        d = str(e.get("detail",""))
        if '"code": "0"' in d or (isinstance(e.get("data"), dict) and e.get("data",{}).get("response",{}).get("code")=="0"):
            print(f"  {e.get('title')} @ ts={e.get('ts')}")
            count += 1
print(f"total successful opens in log: {count}")

# when equity dropped
print("\n=== EQUITY MILESTONES ===")
for e in events:
    if e.get("type")=="account":
        t = e.get("title","")
        if any(x in t for x in ["$3.1", "$1.5", "$0.8", "$0.9"]):
            m = re.search(r"Equity \$([0-9.]+)", t)
            if m:
                val = float(m.group(1))
                if val < 1.6 or val > 3.0:
                    pass
print("first $3.12:", next((e["ts"] for e in events if "Equity $3.1199" in str(e.get("title",""))), None))
first_low = next((e for e in events if e.get("type")=="account" and "Equity $1.56" in str(e.get("title",""))), None)
if first_low:
    print("first drop to ~$1.56 at ts", first_low["ts"])
first_88 = next((e for e in events if e.get("type")=="account" and "Equity $0.88" in str(e.get("title",""))), None)
if first_88:
    print("first ~$0.88 at ts", first_88["ts"])

# strategy mentions drawdown
print("\n=== LEARNING SIGNAL: drawdown awareness in decisions ===")
drawdown_mentions = sum(1 for e in events if e.get("type")=="llm" and "drawdown" in str(e.get("detail","")).lower())
ntp_mentions = sum(1 for e in events if e.get("type")=="llm" and "ntp" in str(e.get("detail","")).lower())
print(f"decisions mentioning drawdown: {drawdown_mentions}")
print(f"decisions mentioning NTP: {ntp_mentions}")
