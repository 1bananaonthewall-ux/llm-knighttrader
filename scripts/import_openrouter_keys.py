"""
Import OpenRouter keys from arbitrary text files into this repo's local .env.

Purpose: add more `sk-or-...` keys so LLMWrapper can cycle keys when one
provider/model hits rate limits or key exhaustion.

Security: this script NEVER prints any keys to stdout (only counts).
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path


SK_OR_RE = re.compile(r"sk-or-[A-Za-z0-9_-]+")


def _read_text_safe(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def discover_keys_from_text(text: str) -> list[str]:
    keys: list[str] = []
    seen: set[str] = set()
    for m in SK_OR_RE.finditer(text or ""):
        k = (m.group(0) or "").strip()
        if not k or not k.startswith("sk-or-"):
            continue
        if k in seen:
            continue
        seen.add(k)
        keys.append(k)
    return keys


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+", help="Files containing OpenRouter keys (sk-or-...).")
    ap.add_argument("--env", default=str(Path(__file__).resolve().parents[1] / ".env"))
    args = ap.parse_args()

    env_path = Path(args.env)
    env_text = _read_text_safe(env_path) if env_path.exists() else ""
    existing = set(discover_keys_from_text(env_text))

    discovered: list[str] = []
    for f in args.files:
        p = Path(f).expanduser()
        for k in discover_keys_from_text(_read_text_safe(p)):
            if k not in existing and k not in discovered:
                discovered.append(k)

    if not discovered:
        print("OpenRouter keys: 0 new keys found (nothing to add).")
        return

    # Append as OPENROUTER_API_KEY_<n> entries.
    lines = env_text.splitlines()
    if lines and lines[-1].strip():
        env_text = "\n".join(lines) + "\n"

    named: set[str] = set()
    for line in (env_text.splitlines() if env_text else []):
        s = line.strip()
        if s.startswith("OPENROUTER_API_KEY_") and "=" in s:
            named.add(s.split("=", 1)[0].strip())

    idx = 2
    while f"OPENROUTER_API_KEY_{idx}" in named:
        idx += 1

    env_text += "\n# Imported OpenRouter keys (auto-added for cycling)\n"
    added = 0
    for k in discovered:
        env_text += f"OPENROUTER_API_KEY_{idx}={k}\n"
        idx += 1
        added += 1

    env_path.write_text(env_text, encoding="utf-8")
    print(f"OpenRouter keys: {added} new keys added to .env")


if __name__ == "__main__":
    main()

