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

# Copy the real Python binary to /app/python and retarget venv symlinks to it.
RUN PYTHON_REAL=$(readlink -f "$(which python3)") && \
    cp "$PYTHON_REAL" /app/python && \
    find /app/venv/bin -name 'python*' -exec ln -sf /app/python {} \;

# Alpine stage (root) is required for setcap; the Chainguard builder is non-root.
# See docs/decisions.md (D008) for the full rationale.
FROM alpine AS capable-python

RUN apk add --no-cache libcap

COPY --from=builder /app/python /app/python

# Grant NET_BIND_SERVICE so uid 65532 can bind to port 53 without running as root.
RUN setcap 'cap_net_bind_service=+ep' /app/python

FROM cgr.dev/chainguard/python:latest AS production

ENV PATH="/app/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY --from=builder --chown=65532:65532 /app/venv /app/venv
COPY --from=builder --chown=65532:65532 --chmod=0700 /app/keys /app/keys

# Copy without --chown to preserve the security.capability xattr set by setcap.
# See docs/decisions.md (D008).
COPY --from=capable-python /app/python /app/python

# Expose the standard DNS port (static metadata; pass --port 53 to bind it).
EXPOSE 53/udp

# Volume for DNSSEC keys.
VOLUME ["/app/keys"]

# Run the CLI directly; pass runtime configuration as command arguments.
ENTRYPOINT ["/app/venv/bin/a-healthy-dns"]
