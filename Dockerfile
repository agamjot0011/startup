# syntax=docker/dockerfile:1
# Backend image for WZDM LiveRecord. Build from the REPOSITORY ROOT:
#   docker build -f Dockerfile -t wzdm-backend:g1 .
# No secrets are baked into the image; supply runtime env vars at `docker run`.

# --- Stage 1: build an isolated virtual environment -------------------------
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /build
COPY backend/requirements.txt ./requirements.txt

RUN python -m venv /opt/venv \
    && /opt/venv/bin/python -m pip install --no-cache-dir --upgrade pip \
    && /opt/venv/bin/python -m pip install --no-cache-dir -r requirements.txt

# --- Stage 2: minimal runtime image ----------------------------------------
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:${PATH}"

# Non-root execution. UID/GID are fixed for predictable volume permissions.
RUN groupadd --gid 10001 app \
    && useradd --uid 10001 --gid app --create-home --shell /usr/sbin/nologin app

WORKDIR /app

COPY --from=builder --chown=app:app /opt/venv /opt/venv
COPY --chown=app:app backend/app ./app
COPY --chown=app:app backend/server.py ./server.py

LABEL org.opencontainers.image.title="wzdm-backend" \
      org.opencontainers.image.description="WZDM LiveRecord API (G1 skeleton image)" \
      org.opencontainers.image.source="https://github.com/agamjot0011/startup.git" \
      org.opencontainers.image.licenses="proprietary"

USER app
EXPOSE 4000

# Config is read from runtime environment variables (see .env.example / docs/G1_README.md).
CMD ["python", "-m", "uvicorn", "server:app", "--host", "0.0.0.0", "--port", "4000"]
