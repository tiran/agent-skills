# Skill: secure build-and-release pipeline for Python (GitHub Actions)

Build, verify, and publish a Python package from GitHub Actions the secure way:
split sdist and wheel builds (wheels build **from** the sdist, so a broken sdist
is caught), publish to PyPI via a **Trusted Publisher** (OIDC, no API token) from
a dedicated job, use **cibuildwheel** for C/C++/Rust wheels, and harden the
pipeline (minimal permissions, SHA-pinned actions, no cache on release, **zizmor**
audit, [PEP 740](https://peps.python.org/pep-0740/) attestations).

**Status: Experimental** — assembled from two real shipping projects (pycxxfilt,
zipwire) plus upstream docs; the consolidated workflow is a new draft. Review
permissions and the PyPI publisher config before relying on it.

## Why this matters

Stored publishing credentials get stolen and abused. The Dec 2024
[**ultralytics** compromise](https://www.reversinglabs.com/blog/compromised-ultralytics-pypi-package-delivers-crypto-coinminer)
used a stolen PyPI API token to push malicious releases of a popular AI package,
and PyPI has since documented a
[campaign that injected GitHub Actions workflows to exfiltrate publishing tokens](https://blog.pypi.org/archive/2025/)
stored as secrets; AI packages such as
[litellm](https://www.trendmicro.com/en_us/research/26/c/your-ai-stack-just-handed-over-your-root-keys-inside-the-litellm-pypi-breach.html)
and [Mistral](https://raven.io/blog/the-mistral-compromise) were hit in 2026.
Trusted Publishing removes the standing token entirely, and PEP 740 attestations
let consumers verify an artifact's origin — that's the core of this pipeline.

## Layout

| File | Role |
| --- | --- |
| `SKILL.md` | The workflow — 8 ordered steps + frontmatter. **Source of truth.** |
| `AGENTS.md` | Cross-agent entry point (Codex and other `AGENTS.md`-aware agents). |
| `reference/templates.md` | Copy-paste workflows: pure-Python, compiled+cibuildwheel, zizmor, PyPI trusted-publisher checklist. |
| `reference/hardening.md` | Security rationale and the per-job permission map. |

## Related

- [`port-to-scikit-build-core`](../port-to-scikit-build-core/) /
  [`port-to-meson-python`](../port-to-meson-python/) — the build backends;
  their VCS versioning is frozen into the sdist by this pipeline.
- [`pybind11-to-nanobind`](../pybind11-to-nanobind/) /
  [`port-to-torch-stable-abi`](../port-to-torch-stable-abi/) — produce the abi3
  wheels this pipeline builds and audits.

See the repository [`README.md`](../../README.md) for per-agent setup.
