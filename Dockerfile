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

# Copy the real Python interpreter to /app/python and retarget all venv Python
# symlinks to it.  These operations are non-privileged: cp and ln work as the
# Chainguard non-root user without requiring apk or root access.
RUN PYTHON_REAL=$(readlink -f "$(which python3)") && \
    cp "$PYTHON_REAL" /app/python && \
    find /app/venv/bin -name 'python*' -exec ln -sf /app/python {} \;

# Apply the NET_BIND_SERVICE file capability using Alpine, which provides root
# access and libcap.  The Chainguard builder image runs non-root and cannot use
# apk, so a separate root-capable stage is required for setcap.
FROM alpine AS capable-python

RUN apk add --no-cache libcap

COPY --from=builder /app/python /app/python

# Grant the NET_BIND_SERVICE file capability so that uid 65532 can bind to
# privileged ports (e.g., 53/udp) at runtime without running as root.
RUN setcap 'cap_net_bind_service=+ep' /app/python

FROM cgr.dev/chainguard/python:latest AS production

ENV PATH="/app/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY --from=builder --chown=65532:65532 /app/venv /app/venv
COPY --from=builder --chown=65532:65532 --chmod=0700 /app/keys /app/keys

# Copy the capability-enabled Python interpreter without --chown so the
# security.capability xattr set by setcap is preserved by Docker BuildKit.
# Chowning a file clears its file capabilities (Linux security invariant);
# root ownership is intentional — uid 65532 can still execute the binary
# (world-execute permission) while the file capability allows it to bind
# to privileged ports regardless of the executing user's uid.
COPY --from=capable-python /app/python /app/python

# 65532 is the default non-root user in Chainguard distroless images.
USER 65532

# Expose the standard DNS port (static metadata; pass --port 53 to bind it).
EXPOSE 53/udp

# Volume for DNSSEC keys.
VOLUME ["/app/keys"]

# Run the CLI directly; pass runtime configuration as command arguments.
ENTRYPOINT ["/app/venv/bin/a-healthy-dns"]
