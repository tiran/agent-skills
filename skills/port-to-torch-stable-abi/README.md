# Skill: port a package to the PyTorch stable ABI

Port a compiled PyTorch C++/CUDA/ROCm extension to the **stable ABI** (so one wheel
works across Torch versions) and assess **Python abi3**. The content is
framework-neutral Markdown; the same files drive multiple coding agents.

## Layout

| File | Role |
| --- | --- |
| `SKILL.md` | The workflow — 17 ordered steps + frontmatter. **Source of truth.** |
| `AGENTS.md` | Cross-agent entry point (Codex and other `AGENTS.md`-aware agents). |
| `reference/substitutions.md` | Include / type / check / method / dispatch swap tables. |
| `reference/ports.md` | Reference-port matrix + `torch_call_dispatcher` escape hatch. |
| `reference/background.md` | Rationale: ABI basics, CUDA/ROCm, abi3 (the "why"). |

`SKILL.md` and `AGENTS.md` point at the same `reference/` files; only `SKILL.md`
carries the full step list, so there is no duplicated workflow to maintain.

## Use with Claude Code

Place this directory under `.claude/skills/` in a repo (or ship it in a plugin's
`skills/`). Claude auto-discovers it from the `description` in `SKILL.md`'s
frontmatter — just describe the task, or invoke `/port-to-torch-stable-abi`.

## Use with Codex CLI (and other `AGENTS.md` agents)

Codex reads `AGENTS.md` from the working directory upward. Either:

- **Run inside this skill directory / repo** — `AGENTS.md` is picked up
  automatically; it tells the agent to follow `SKILL.md`.
- **Run in the project you are porting** — add (or append to) an `AGENTS.md` there
  with a pointer, e.g.:

  ```markdown
  For PyTorch stable-ABI ports, follow <path-to>/port-to-torch-stable-abi/SKILL.md.
  ```

  or start the session by telling Codex to read that `SKILL.md` and follow it.

## Use with any other agent

Point the agent at `SKILL.md` and tell it to follow the steps, opening
`reference/*.md` as cited. Nothing here depends on a specific agent framework.
