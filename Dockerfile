# Multi-stage build for minimal image size
FROM python:3-slim AS builder

# Install build dependencies
RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    libssl-dev \
    cargo \
    rustc \
    && apt-get autoremove -y \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY setup.py .
COPY indisoluble/ ./indisoluble/

# Install the application and dependencies
RUN pip install --no-cache-dir --user .

# Production stage
FROM python:3-slim AS production

# Install runtime dependencies only
RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends \
    libffi8 \
    libssl3 \
    libcap2-bin \
    tini \
    && apt-get autoremove -y \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd -r -g 10000 appuser && \
    useradd -r -u 10000 -g appuser -s /bin/false -c "Application user" appuser

# Create directory for DNSSEC keys with proper permissions
RUN mkdir -p /app/keys && \
    chown appuser:appuser /app/keys && \
    chmod 700 /app/keys

# Copy installed packages from builder
COPY --from=builder --chown=appuser:appuser /root/.local /home/appuser/.local

# Grant capability to Python interpreter to bind to privileged ports
RUN PYTHON_REAL=$(readlink -f /usr/local/bin/python3) && \
    setcap 'cap_net_bind_service=+ep' "$PYTHON_REAL"

# Switch to non-root user
USER appuser

# Set environment variables
ENV PATH="/home/appuser/.local/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Working directory
WORKDIR /app

# Default environment variables for all parameters
ENV DNS_HOSTED_ZONE="" \
    DNS_ZONE_RESOLUTIONS="" \
    DNS_NAME_SERVERS="" \
    DNS_PORT="53" \
    DNS_LOG_LEVEL="info" \
    DNS_TEST_MIN_INTERVAL="30" \
    DNS_TEST_TIMEOUT="2" \
    DNS_PRIV_KEY_PATH="" \
    DNS_PRIV_KEY_ALG="RSASHA256"

# Expose the default DNS port (static at build time)
EXPOSE 53/udp

# Volume for DNSSEC keys
VOLUME ["/app/keys"]

# Entry point script that converts environment variables to command line arguments
ENTRYPOINT ["tini", "--", "sh", "-c", "\
    set -e; \
    if [ -z \"$DNS_HOSTED_ZONE\" ]; then \
    echo 'Error: DNS_HOSTED_ZONE environment variable is required'; \
    exit 1; \
    fi; \
    if [ -z \"$DNS_ZONE_RESOLUTIONS\" ]; then \
    echo 'Error: DNS_ZONE_RESOLUTIONS environment variable is required'; \
    exit 1; \
    fi; \
    if [ -z \"$DNS_NAME_SERVERS\" ]; then \
    echo 'Error: DNS_NAME_SERVERS environment variable is required'; \
    exit 1; \
    fi; \
    ARGS=\"--hosted-zone $DNS_HOSTED_ZONE\"; \
    ARGS=\"$ARGS --zone-resolutions $DNS_ZONE_RESOLUTIONS\"; \
    ARGS=\"$ARGS --ns $DNS_NAME_SERVERS\"; \
    ARGS=\"$ARGS --port $DNS_PORT\"; \
    ARGS=\"$ARGS --log-level $DNS_LOG_LEVEL\"; \
    ARGS=\"$ARGS --test-min-interval $DNS_TEST_MIN_INTERVAL\"; \
    ARGS=\"$ARGS --test-timeout $DNS_TEST_TIMEOUT\"; \
    if [ -n \"$DNS_PRIV_KEY_PATH\" ]; then \
    ARGS=\"$ARGS --priv-key-path $DNS_PRIV_KEY_PATH\"; \
    fi; \
    ARGS=\"$ARGS --priv-key-alg $DNS_PRIV_KEY_ALG\"; \
    echo \"Starting a-healthy-dns with arguments: $ARGS\"; \
    exec a-healthy-dns $ARGS"]
