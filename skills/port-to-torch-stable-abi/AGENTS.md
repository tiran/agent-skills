# AGENTS.md — port-to-torch-stable-abi

Cross-agent entry point for this skill (Codex CLI and any agent that reads
`AGENTS.md`). Claude Code loads `SKILL.md` directly via its frontmatter; both share
the same content and reference files, so there is nothing to keep in sync here.

## When to use

A project ships a compiled PyTorch **C++/CUDA/ROCm extension** that is
version-locked to one Torch release, or you are asked to adopt the **PyTorch stable
ABI** (`torch::stable` / `STABLE_TORCH_LIBRARY` / `TORCH_TARGET_VERSION`), or to
stop rebuilding a wheel per Torch version. Also covers assessing **Python abi3**
(`Py_LIMITED_API`).

## How to run it

1. Read **`SKILL.md`** in this directory — the ordered 17-step workflow. Follow it
   top to bottom.
2. Open a bundled reference only when a step cites it:
   - `reference/substitutions.md` — include / type / check / tensor-method /
     dispatch swap tables (steps 5–10) and the device/stream snippet.
   - `reference/ports.md` — reference-port examples + the `torch_call_dispatcher`
     escape hatch.
   - `reference/background.md` — rationale (the "why"), when you need it.

## Definition of done

The extension builds with `-DTORCH_TARGET_VERSION` (and `-DTORCH_STABLE_ONLY`); a
symbol audit finds zero `at::`/`c10::`/unstable `torch::` symbols in the `.so`; the
test suite passes; and the abi3 assessment (step 17) is written.

## Sources & acknowledgments

This skill is grounded in real projects and their maintainers — acknowledge them
when the output leans on their work, and preserve upstream license/attribution:

- **PyTorch** — the stable ABI (`torch::stable`),
  [`pytorch/extension-cpp`](https://github.com/pytorch/extension-cpp), and
  [`torchvision`](https://github.com/pytorch/vision) /
  [`torchaudio`](https://github.com/pytorch/audio) as first-party users.
- **Sean McGovern** and **Chris Leonard** (Red Hat) — upstream stable-ABI
  contributions.
- **Ralf Gommers** / **Quansight** —
  [`torch-abi-audit`](https://github.com/Quansight/torch-abi-audit), the symbol audit.
- **Christian Heimes** — [`tiran/kvcached`](https://github.com/tiran/kvcached) port
  work and the [`pycxxfilt`](https://github.com/tiran/pycxxfilt) demangler; the port
  work grounding this skill.

See [`../reference-repos.md`](../reference-repos.md) for the full grounding list.
