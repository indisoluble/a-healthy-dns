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

# Grant the Python interpreter the NET_BIND_SERVICE file capability so that
# uid 65532 can bind to privileged ports (e.g., 53/udp) at runtime.  libcap
# is a build-time dependency only; it is not installed in the production image.
# The capability-enabled interpreter is placed at /app/python and the venv
# Python symlinks are retargeted to it so the installed console script's
# shebang resolves to the capable binary.
RUN apk add --no-cache libcap && \
    PYTHON_REAL=$(readlink -f "$(which python3)") && \
    cp "$PYTHON_REAL" /app/python && \
    setcap 'cap_net_bind_service=+ep' /app/python && \
    find /app/venv/bin -name 'python*' -exec ln -sf /app/python {} \;

FROM cgr.dev/chainguard/python:latest AS production

ENV PATH="/app/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY --from=builder --chown=65532:65532 /app/venv /app/venv
COPY --from=builder --chown=65532:65532 --chmod=0700 /app/keys /app/keys

# Copy the Python interpreter without --chown so the security.capability xattr
# set by setcap is preserved by Docker BuildKit.  Chowning a file clears its
# file capabilities (Linux security invariant); root ownership is intentional
# here — uid 65532 can still execute the binary (world-execute permission)
# while the file capability allows it to bind to privileged ports regardless
# of the executing user's uid.
COPY --from=builder /app/python /app/python

# 65532 is the default non-root user in Chainguard distroless images.
USER 65532

# Expose the standard DNS port (static metadata; pass --port 53 to bind it).
EXPOSE 53/udp

# Volume for DNSSEC keys.
VOLUME ["/app/keys"]

# Run the CLI directly; pass runtime configuration as command arguments.
ENTRYPOINT ["/app/venv/bin/a-healthy-dns"]
