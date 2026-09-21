# Guardrails

Shared operating rules for every skill in this repo. Follow them **unless the
user explicitly says otherwise.** Individual skills link here rather than
repeating the list.

## Environment

- Work in a **project-local `.venv`**, preferably created with **`uv venv`**.
- Prefer **uv** for everything: `uv venv`, `uv pip …`, `uv build`, `uvx`. Run
  one-off tools with **`uvx`** (not `pipx`).
- **Never** install into global or user site-packages — no `sudo pip`, no
  `pip install --user`, no touching the system interpreter.
- If uv isn't available, still use a `.venv` (`python -m venv`); never install
  globally.
- **Favor `uv build`** over `python -m build`, and `uv pip …` over `pip …`.
  `python -m build` / `pip …` are the equivalent fallbacks when uv isn't
  available — use them 1:1, inside the venv.

## Changes

- **Don't delete existing content** (code, docs, comments, config) unless the
  task requires it and the user is aware.
- **Don't commit or push without the user's explicit OK**, and **never commit
  directly to `main`** — branch first.
- Leave changes in the working tree for review rather than finalizing them.

## Footprint

- Be mindful of **disk and CPU/memory**. Some dependencies are large — a torch +
  CUDA install runs to several GB.
- **Ask the user for consent before installing heavy packages or starting a heavy
  compile** (e.g. torch/CUDA, a full C++/CUDA build, cibuildwheel matrices).
  Estimate the cost first (download size, disk, build time) and let them decide.
- Install only what the task needs; don't pull heavy extras or duplicate wheels.
- Reuse an existing venv/cache when it's already set up rather than recreating it.

## Style

- **Match the project's existing conventions** for formatting, naming, comments,
  and docstrings — read the surrounding code first.
- Keep comments and docstrings **terse and to the point**. Explain *why*, not
  *what*; don't restate what the code already makes obvious.
