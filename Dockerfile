# syntax=docker/dockerfile:1

# Build dependencies in the Chainguard dev image and keep the runtime image distroless.
FROM cgr.dev/chainguard/python:latest-dev AS builder

ENV PATH="/app/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

RUN python -m venv /app/venv && \
    mkdir -p /app/keys

COPY setup.py .
COPY indisoluble/ ./indisoluble/

RUN pip install --no-cache-dir .

FROM cgr.dev/chainguard/python:latest AS production

ENV PATH="/app/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY --from=builder /app/venv /app/venv
COPY --from=builder --chmod=0700 /app/keys /app/keys

# Expose the standard DNS port (static metadata; pass --port 53 to bind it).
EXPOSE 53/udp

# Volume for DNSSEC keys.
VOLUME ["/app/keys"]

# Run the CLI directly; pass runtime configuration as command arguments.
ENTRYPOINT ["/app/venv/bin/a-healthy-dns"]
