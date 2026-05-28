# syntax=docker/dockerfile:1

# Build dependencies in the Chainguard dev image and keep the runtime image distroless.
FROM cgr.dev/chainguard/python:latest-dev AS builder

ENV PATH="/app/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

RUN python -m venv /app/venv && \
    mkdir -p /app/keys

COPY pyproject.toml README.md ./
COPY indisoluble/ ./indisoluble/

RUN pip install --no-cache-dir .

FROM cgr.dev/chainguard/python:latest AS production

ENV PATH="/app/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# COPY defaults to root ownership; keep runtime files readable by the
# Chainguard non-root uid 65532. See docs/docker.md#1-runtime-contract for the runtime contract.
COPY --from=builder --chown=65532:65532 /app/venv /app/venv
COPY --from=builder --chown=65532:65532 --chmod=0700 /app/keys /app/keys

# Static metadata for standard DNS; the runtime command controls the actual listener port.
EXPOSE 53/udp

# Volume for DNSSEC keys.
VOLUME ["/app/keys"]

# Run the CLI directly; pass runtime configuration as command arguments.
ENTRYPOINT ["/app/venv/bin/a-healthy-dns"]
