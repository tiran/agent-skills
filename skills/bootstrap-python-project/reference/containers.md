# Containers — OCI-standard, tool-agnostic (house rule)

Only relevant **if the project actually uses containers** (for building, running, or
development). Don't scaffold any of this otherwise.

**House rule: containers must be OCI-standard and tool-agnostic.** The same files
must build and run under both **Podman** and **Docker** (and buildah).

## 1. Write to the OCI spec; avoid dockerisms

Stick to standard image/`Dockerfile` instructions that Podman/buildah **and** Docker
both support. A "dockerism" is something that assumes the Docker engine or a
Docker-only build feature. Avoid, or gate behind a confirmed-portable check:

- **BuildKit-only build features** — `RUN --mount=type=secret|ssh`, and other
  build-secret mechanisms only Docker's BuildKit provides.
- **Docker-daemon assumptions** — rootful-only steps, socket mounts
  (`/var/run/docker.sock`), Docker-in-Docker.
- **Hardcoded `docker` in scripts/CI** — parameterize the engine
  (`${CONTAINER_ENGINE:-podman}`) so `podman` and `docker` are interchangeable.
- **Bare image names** — Podman has no implicit Docker Hub default, so `python:3.12`
  is a dockerism; use a **fully-qualified reference**
  (`registry.access.redhat.com/ubi10/ubi-minimal:latest`, `docker.io/library/…`).

Name the build file **`Containerfile`** (the OCI-neutral name — Podman/buildah pick
it up automatically; Docker builds it with `-f Containerfile`).

**Recommend heredoc `RUN` blocks** for readable multi-step layers — they collapse a
chain of `&&`-joined commands into a clean shell script and are fully cross-tool:

```dockerfile
# syntax=docker/dockerfile:1
...
RUN bash -euo pipefail <<EOF
microdnf install -y --nodocs python${PYTHON_VERSION}
microdnf clean all
EOF
```

Docker needs the `# syntax=docker/dockerfile:1` directive to enable heredocs;
Podman/buildah support them natively (the directive is harmless there).

> **Caveat — heredoc layer-cache invalidation on Podman/buildah.** Buildah has a
> long-running bug where editing the *content* of a heredoc `RUN` doesn't invalidate
> the build cache, so `--layers`/cached builds silently reuse the stale layer
> (containers/podman#21498, buildah#5225 — fixed in **buildah 1.35 / Podman 5.0**).
> It then **recurred when an `ARG` precedes the heredoc `RUN`** — exactly the
> `ARG PYTHON_VERSION` + heredoc shape below — and was only fixed by buildah PR #6041
> in **buildah 1.40.0 → Podman 5.5.0** (podman#24089, podman#25469, buildah#5656).
> **Require Podman ≥ 5.5 / buildah ≥ 1.40** to use heredocs after an `ARG`; on older
> versions, build such edits with `--no-cache` or keep version-carrying `ARG`s out of
> the heredoc's stage. Verify a heredoc edit actually re-ran before trusting a cached
> image.

## 2. Prefer `ARG` over hard-coded values

Base-image tag, Python version, tool/package pins, UID/GID — as `ARG` so the build
is configurable without editing the file. Override identically in both engines
(`podman build --build-arg …` / `docker build -f Containerfile --build-arg …`).

## 3. Multi-stage when the container builds code

If the wheel/artifacts are built **inside** the container, use a **multi-stage
build**: a `builder` stage with the build tools, then a lean `runtime` stage that
copies only the built artifacts — so compilers and build deps never ship in the final
image. (If artifacts are pre-built outside, e.g. into `dist/`, a single runtime stage
that installs them is fine.)

## 4. Ready-made Python base image, chosen to match the user's ecosystem

**Prefer a ready-made Python base image** — don't build CPython from source. Pick the
family from the user's platform preference:

- **Fedora / Red Hat →** Red Hat **UBI** (`registry.access.redhat.com/ubi10/ubi-minimal`,
  install `python3.12` via `microdnf`) or **Fedora SCL** Python images.
- **Debian / Ubuntu →** an **Ubuntu**-based image (or the Debian-based
  `docker.io/library/python:<ver>-slim`).

Pass the exact base as `ARG BASE_IMAGE=…` so it's swappable.

## 5. Always create a virtualenv inside the container

Install into an explicit venv, not the system interpreter — clean isolation and a
predictable `PATH`. With uv (copy the static binary from the published image):

```dockerfile
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
RUN uv venv --python python${PYTHON_VERSION} /opt/app-root
ENV VIRTUAL_ENV=/opt/app-root \
    PATH="/opt/app-root/bin:$PATH" \
    HOME=/opt/app-root/src
```

## 6. Run as non-root, cloud-native `1001:0`

Follow the OpenShift/cloud-native convention: run as an **arbitrary non-root UID in
the root group (GID 0)** so platforms that assign a random UID still work. Use UID
**1001**, group **0**, home under `/opt/app-root/src`; make the app dirs
**group-writable and group-owned by 0** (`chmod -R g=u` / `0770`, `chown -R 1001:0`),
and end with `USER 1001`.

## Worked example — multi-stage, UBI, venv, non-root `1001:0`, `ARG`

```dockerfile
# syntax=docker/dockerfile:1
ARG PYTHON_VERSION=3.12
ARG BASE_IMAGE=registry.access.redhat.com/ubi10/ubi-minimal:latest

# ---- builder: build the wheel (build tools stay here) ----
FROM ${BASE_IMAGE} AS builder
ARG PYTHON_VERSION
RUN microdnf install -y --nodocs python${PYTHON_VERSION} && microdnf clean all
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
WORKDIR /src
COPY . .
RUN uv build --wheel --out-dir /dist

# ---- runtime: only the venv + wheel ----
FROM ${BASE_IMAGE} AS runtime
ARG PYTHON_VERSION
RUN bash -euo pipefail <<EOF
microdnf install -y --nodocs python${PYTHON_VERSION} shadow-utils
useradd -u 1001 -g 0 -d /opt/app-root/src -M -s /bin/bash default
mkdir -p -m 0770 /opt/app-root/src
chown -R 1001:0 /opt/app-root
microdnf remove -y shadow-utils
microdnf clean all
EOF
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
RUN uv venv --python python${PYTHON_VERSION} /opt/app-root
ENV VIRTUAL_ENV=/opt/app-root \
    PATH="/opt/app-root/bin:$PATH" \
    HOME=/opt/app-root/src
COPY --from=builder /dist/*.whl /tmp/
RUN uv pip install --no-cache /tmp/*.whl && rm -rf /tmp/*.whl
WORKDIR ${HOME}
USER 1001
ENTRYPOINT ["<dist>"]
```

## 7. Compose and dev containers

- **Compose:** if orchestration is needed, use the
  **[Compose Spec](https://compose-spec.io/)** (`compose.yaml`) so it runs under
  `docker compose` *and* `podman compose` / `podman-compose`.
- **Development containers:** use the open **Dev Container standard**
  ([containers.dev](https://containers.dev), `.devcontainer/devcontainer.json`),
  which VS Code and others consume; point `build.dockerfile` at the `Containerfile`.

## Bottom line

OCI `Containerfile`, fully-qualified ready-made Python base (UBI/Fedora for
Red Hat, Ubuntu for Debian), `ARG` for anything versioned, multi-stage when building
code, a venv inside the image, non-root `1001:0`, Compose Spec for orchestration, and
the Dev Container standard for dev — so the project works identically with Podman and
Docker.
