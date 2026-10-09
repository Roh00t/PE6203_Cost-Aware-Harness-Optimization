# Optional containerised runner for Harbor. The primary path is running
# `scripts/harbor_run.sh` on the host; this image exists so teammates get an
# identical toolchain (Python 3.12, uv, Docker CLI, pinned Harbor).
#
# Harbor launches each task in a sibling container through the host's Docker
# daemon (socket mounted by docker-compose.yml). It bind-mounts log/artifact
# paths *as it sees them*, so the repo must be mounted at the same absolute
# path inside this container as on the host — see docker-compose.yml.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    # Keep the Linux venv out of the bind-mounted repo so it never clobbers
    # the host's macOS .venv.
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:${PATH}"

RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        git \
        jq \
    && rm -rf /var/lib/apt/lists/*

# Docker CLI + compose plugin (Harbor shells out to `docker compose`) and uv.
COPY --from=docker:27.5.1-cli /usr/local/bin/docker /usr/local/bin/docker
COPY --from=docker:27.5.1-cli /usr/local/libexec/docker/cli-plugins/docker-compose /usr/local/libexec/docker/cli-plugins/docker-compose
COPY --from=ghcr.io/astral-sh/uv:0.11.14 /uv /uvx /usr/local/bin/

# Dependencies only; the source tree is bind-mounted at runtime, not copied,
# so secrets in .env can never end up in an image layer.
WORKDIR /opt/harness
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-install-project

CMD ["harbor", "--version"]
