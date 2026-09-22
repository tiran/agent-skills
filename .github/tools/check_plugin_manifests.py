#!/usr/bin/env python3
"""Guard the plugin manifests.

The repo pins by commit SHA, not by version (see README "Updating"): every
`marketplace update` that pulls a new commit refreshes installs, so no manual
version bump is needed. A stray ``version`` field would re-enable version-based
caching and silently freeze users on a stale copy, so fail if one reappears.
Also checks both manifests parse and agree on ``name``.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

MANIFESTS = ("plugin.json", ".claude-plugin/plugin.json")


def main() -> int:
    root = Path(__file__).resolve().parents[2]  # .github/tools/ -> repo root
    problems = []
    names = set()
    for rel in MANIFESTS:
        path = root / rel
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            problems.append(f"{rel}: {exc}")
            continue
        if "version" in data:
            problems.append(
                f"{rel}: has a 'version' field; omit it to pin by commit SHA"
            )
        if not data.get("name"):
            problems.append(f"{rel}: missing 'name'")
        else:
            names.add(data["name"])

    if len(names) > 1:
        problems.append(f"manifests disagree on 'name': {sorted(names)}")

    for problem in problems:
        print(problem, file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
