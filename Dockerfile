# Multi-stage build for minimal image size
FROM python:3.13-alpine AS builder

# Install build dependencies
RUN apk add --no-cache \
    gcc \
    musl-dev \
    libffi-dev \
    openssl-dev \
    cargo \
    rust

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY setup.py .
COPY indisoluble/ ./indisoluble/

# Install the application and dependencies as root
RUN pip install --no-cache-dir --user .

# Production stage
FROM python:3.13-alpine AS production

# Install runtime dependencies only
RUN apk add --no-cache \
    libffi \
    openssl \
    && rm -rf /var/cache/apk/*

# Create non-root user for security
RUN addgroup -g 1000 appgroup && \
    adduser -D -u 1000 -G appgroup appuser

# Create directory for DNSSEC keys with proper permissions
RUN mkdir -p /app/keys && \
    chown -R appuser:appgroup /app

# Copy installed packages from builder
COPY --from=builder --chown=appuser:appgroup /root/.local /home/appuser/.local

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
    DNS_PORT="53053" \
    DNS_LOG_LEVEL="info" \
    DNS_TEST_MIN_INTERVAL="30" \
    DNS_TEST_TIMEOUT="2" \
    DNS_PRIV_KEY_PATH="" \
    DNS_PRIV_KEY_ALG="RSASHA256"

# Expose the default DNS port (static at build time)
EXPOSE 53053/udp

# Volume for DNSSEC keys
VOLUME ["/app/keys"]

# Entry point script that converts environment variables to command line arguments
ENTRYPOINT ["sh", "-c", "\
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
