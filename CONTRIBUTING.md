# Contributing to agent-skills

Guidance for anyone — human or agent — **editing this repository** (adding or changing
skills, references, or config). If you only want to *use* a skill, see
[`AGENTS.md`](AGENTS.md) and the [`README.md`](README.md) index instead.

## Working in this repo

- **Always work on a _new_ branch, one per change** — never commit to `main`, and
  never reuse, reset, or add commits to a branch left over from earlier work. Start
  each task by branching off freshly-fetched `main`
  (`git fetch origin && git switch -c <name> origin/main`), commit there, open a PR.
  When the user says "create a new branch," run `git switch -c` for a brand-new
  branch — do **not** reinterpret it as committing onto the current branch. One
  branch = one PR = one logical change; don't mix unrelated changes on a branch.
- **Follow standard commit-message conventions:** an imperative subject line of
  **≤50 characters** (capitalized, no trailing period), a blank line, then a body
  wrapped at **72 columns** explaining the *why* / user impact — not a file-by-file
  changelog. Keep it terse; omit the body for trivial changes.
  **Optimize for human readability:** write the body for a reviewer skimming
  `git log` — lead with the user impact and the important change, cut restated
  detail and boilerplate, and prefer a short message over an exhaustive one. Bullet
  points are fine, and preferred over a run-on paragraph, when the change has
  several distinct parts.
- **Verify `pre-commit` before pushing** — run `pre-commit run --all-files` (or let
  the git hook run) and fix any failures locally; don't push a branch whose hooks
  fail.
- **PR title and description mirror the commit** — reuse the commit subject as the
  PR title and the commit body as the description. Don't pad the PR with boilerplate
  the commit doesn't have (no invented "Testing" / "Changes" sections).
- **Always sign off commits** (`git commit -s`) — add the `Signed-off-by` line
  (DCO).

## Authoring or editing a skill (conventions)

- One skill per directory under `skills/<name>/`, with a single `SKILL.md` as the
  source of truth (frontmatter `name` + `description`, then an ordered workflow).
- Keep the `description` tight and specific — agents trigger the skill from it.
- Put tables, snippets, and long rationale under `reference/` and cite them from
  the numbered steps; do not inline them into the workflow.
- Do not duplicate the workflow into the per-skill `AGENTS.md`/`README.md`; those
  are thin adapters that point back at `SKILL.md`.
- **Register the skill in both index tables, in the same change.** Adding, renaming,
  or removing a skill must update the `## Skills` table in [`AGENTS.md`](AGENTS.md)
  *and* the `## Skills` table in the root [`README.md`](README.md) (the human-facing
  index) — they must list the same skills. Add a row to `skills/reference-repos.md`
  too when the skill introduces a grounding repo. The `AGENTS.md` cell describes
  *when to use* the skill (trigger conditions); the `README.md` cell describes
  *what it does*.
- Keep prose lean. Draft with AI if you like, but read and cut it down before
  committing — unedited AI text is long, unchecked, and expensive to review.
- **Link PEP references in human-facing docs.** In `README.md` files (the root index
  and each skill's), write a PEP mention as a link to `https://peps.python.org/pep-XXXX/`
  — zero-padded, e.g. `[PEP 517](https://peps.python.org/pep-0517/)` — on first mention
  per file. `SKILL.md`/`AGENTS.md` are agent-facing and need no such linking.
- **Acknowledge the projects and people a skill is grounded in.** When a skill leans
  on external work — reference repos, tools, standards, authored practice — recognize
  it: add an `## Acknowledgments` section to the skill's `README.md` and a `## Sources
  & acknowledgments` section to its `AGENTS.md` naming the people and projects, and list
  the grounding repos in `skills/reference-repos.md`. Preserve upstream
  license/attribution when a skill copies or vendors anything. Acknowledge generously
  and accurately; when the author is the repo owner, list them last.
