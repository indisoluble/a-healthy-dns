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

# Expose the standard DNS port (static metadata; pass --port 53 to bind it)
EXPOSE 53/udp

# Volume for DNSSEC keys
VOLUME ["/app/keys"]

# Run the CLI directly; pass runtime configuration as command arguments.
ENTRYPOINT ["a-healthy-dns"]
