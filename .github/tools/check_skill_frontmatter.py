#!/usr/bin/env python3
"""Validate every skills/*/SKILL.md has correct frontmatter.

Each SKILL.md must:
  * open with a ``---`` YAML frontmatter block,
  * parse to a mapping,
  * carry a non-empty ``name`` and ``description``,
  * have ``name`` equal to its skill directory.

Prints every problem and exits non-zero if any are found.
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml


def parse_frontmatter(text: str) -> object:
    if not text.startswith("---\n"):
        raise ValueError("missing '---' frontmatter opening")
    end = text.find("\n---", len("---\n"))
    if end == -1:
        raise ValueError("unterminated frontmatter block")
    return yaml.safe_load(text[len("---\n") : end])


def check(path: Path) -> list[str]:
    try:
        meta = parse_frontmatter(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, yaml.YAMLError) as exc:
        return [f"{path}: {exc}"]
    if not isinstance(meta, dict):
        return [f"{path}: frontmatter is not a mapping"]

    problems = []
    name = meta.get("name")
    if not name:
        problems.append(f"{path}: missing 'name'")
    elif name != path.parent.name:
        problems.append(f"{path}: name {name!r} != directory {path.parent.name!r}")
    if not meta.get("description"):
        problems.append(f"{path}: missing 'description'")
    return problems


def main() -> int:
    root = Path(__file__).resolve().parents[2]  # .github/tools/ -> repo root
    skills = sorted((root / "skills").glob("*/SKILL.md"))
    if not skills:
        print("no SKILL.md files found under skills/", file=sys.stderr)
        return 1

    problems = [p for skill in skills for p in check(skill)]
    for problem in problems:
        print(problem, file=sys.stderr)
    print(f"checked {len(skills)} skills, {len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
