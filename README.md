# A Healthy DNS

[![Work in Progress](https://img.shields.io/badge/status-work%20in%20progress-yellow.svg)](https://github.com/indisoluble/a-healthy-dns)
[![CI](https://github.com/indisoluble/a-healthy-dns/actions/workflows/validate-tests.yml/badge.svg)](https://github.com/indisoluble/a-healthy-dns/actions/workflows/validate-tests.yml)
[![Codecov](https://codecov.io/gh/indisoluble/a-healthy-dns/branch/master/graph/badge.svg)](https://codecov.io/gh/indisoluble/a-healthy-dns)
[![Docker Hub](https://img.shields.io/docker/v/indisoluble/a-healthy-dns?label=docker%20hub&logo=docker)](https://hub.docker.com/r/indisoluble/a-healthy-dns)

A health-aware DNS server that performs health checks on IP addresses and automatically updates DNS responses based on the health status of backend services.
This ensures that DNS queries only return healthy endpoints, providing automatic failover and load balancing capabilities.

## Features

- **Health Checking**: Continuously monitors IP addresses via TCP connectivity tests
- **Dynamic Updates**: Automatically updates DNS zones based on health check results
- **Multi-Domain Support**: Serve multiple domains with the same records without duplicating health checks
- **Configurable TTL**: TTL calculation based on health check intervals
- **Threaded Operations**: Background health checking
- **Multiple Records**: Support for multiple IP addresses per subdomain with individual health tracking
- **DNSSEC Support**: Optional DNSSEC signing

## Installation

### Prerequisites

- Python 3.10 or higher
- pip package manager

### Install from Source

1. Get the source code:
   
   **Option 1.1: Clone the repository**
   ```bash
   git clone https://github.com/indisoluble/a-healthy-dns.git
   cd a-healthy-dns
   ```
   
   **Option 1.2: Download from releases**
   ```bash
   # Download and extract the latest release
   wget https://github.com/indisoluble/a-healthy-dns/archive/refs/tags/v0.1.9.tar.gz
   tar -xzf v0.1.9.tar.gz
   cd a-healthy-dns-0.1.9
   ```

2. Install the package:
   ```bash
   pip install .
   ```

3. Or install in development mode:
   ```bash
   pip install -e .
   ```

### Dependencies

The following dependencies will be automatically installed:
- `cryptography>=46.0.3,<47.0.0` - For DNSSEC cryptographic operations
- `dnspython>=2.8.0,<3.0.0` - For DNS protocol handling

### Using Docker (Recommended)

Docker provides the easiest way to run A Healthy DNS with all dependencies included.

#### Pre-built Image

A pre-built Docker image is available on [Docker Hub](https://hub.docker.com/r/indisoluble/a-healthy-dns).

#### Build the Docker Image

```bash
# Build the image
docker build -t a-healthy-dns .

# Build with a specific tag
docker build -t a-healthy-dns:latest .
```

## Usage

### Basic Usage

Start the DNS server with minimal configuration:

```bash
a-healthy-dns \
    --hosted-zone example.com \
    --zone-resolutions '{"www":{"ips":["192.168.1.100","192.168.1.101"],"health_port":8080},"api":{"ips":["192.168.1.102"],"health_port":8000}}' \
    --ns '["ns1.example.com", "ns2.example.com"]'
```

### Advanced Usage with DNSSEC

Enable DNSSEC signing with custom parameters:

```bash
a-healthy-dns \
    --hosted-zone example.com \
    --zone-resolutions '{"www":{"ips":["192.168.1.100","192.168.1.101"],"health_port":8080},"api":{"ips":["192.168.1.102"],"health_port":8000}}' \
    --ns '["ns1.example.com", "ns2.example.com"]' \
    --priv-key-path /path/to/private.key \
    --priv-key-alg RSASHA256 \
    --port 53 \
    --test-min-interval 15 \
    --test-timeout 3 \
    --log-level info
```

### Configuration Parameters

#### Required Parameters

- `--hosted-zone`: The domain name for which this DNS server is authoritative
- `--zone-resolutions`: JSON configuration defining subdomains, their IP addresses, and health check ports
- `--ns`: Name servers responsible for this zone (JSON array)

#### Optional Parameters

- `--port`: DNS server port (default: 53053)
- `--test-min-interval`: Minimum interval between connectivity tests in seconds (default: 30)
- `--test-timeout`: Maximum time to wait for health check response in seconds (default: 2)
- `--log-level`: Logging level (debug, info, warning, error, critical) (default: info)
- `--alias-zones`: Additional domain names that resolve to the same records as the hosted zone (JSON array, optional)

#### DNSSEC Parameters

- `--priv-key-path`: Path to the DNSSEC private key file for zone signing
- `--priv-key-alg`: Algorithm used for DNSSEC signing (default: RSASHA256)

### Multi-Domain Support

The DNS server supports serving multiple domains that resolve to the same IP addresses without duplicating health checks. This is achieved through the `--alias-zones` parameter:

```bash
a-healthy-dns \
  --hosted-zone primary.com \
  --alias-zones '["alias1.com", "alias2.com"]' \
  --zone-resolutions '{"www": {"ips": ["192.168.1.100"], "health_port": 8080}}' \
  --ns '["ns1.primary.com"]'
```

With this configuration:
- `www.primary.com` → resolves to `192.168.1.100`
- `www.alias1.com` → resolves to `192.168.1.100` (same IP)
- `www.alias2.com` → resolves to `192.168.1.100` (same IP)

**Key Benefits:**
- All domains share the same A records and health checks
- No duplication of health check workload
- DNS responses preserve the original query name (clients see their requested domain)
- Unknown domains are correctly rejected with NXDOMAIN

### Zone Resolution Configuration

The `--zone-resolutions` parameter accepts a JSON object with the following structure:

```json
{
  "subdomain_name": {
    "ips": ["ip1", "ip2", ...],
    "health_port": port_number
  }
}
```

**Example:**
```json
{
  "www": {
    "ips": ["192.168.1.100", "192.168.1.101"],
    "health_port": 8080
  },
  "api": {
    "ips": ["192.168.1.102", "192.168.1.103"],
    "health_port": 8000
  }
}
```

### Health Check Behavior

- The server performs TCP connectivity tests to each IP address on the specified health port
- Only healthy IP addresses are included in DNS responses
- If all IP addresses for a subdomain are unhealthy, the subdomain returns no records (NXDOMAIN)
- Health checks run continuously in the background at the configured interval
- TTL values are automatically calculated based on health check intervals

### Example Deployment

For a deployment serving `example.com`:

```bash
a-healthy-dns \
    --hosted-zone example.com \
    --zone-resolutions '{"www":{"ips":["10.0.1.100","10.0.1.101"],"health_port":80},"api":{"ips":["10.0.1.200","10.0.1.201"],"health_port":8080}}' \
    --ns '["ns1.example.com", "ns2.example.com"]' \
    --priv-key-path /etc/dns/private.key \
    --port 53 \
    --test-min-interval 10 \
    --test-timeout 2 \
    --log-level info
```

This configuration:
- Serves DNS for `example.com` on port 53
- Monitors `www.example.com` with 2 backend servers on port 80
- Monitors `api.example.com` with 2 backend servers on port 8080
- Performs health checks every 10 seconds with 2-second timeout
- Signs the zone with DNSSEC using the provided private key

### Docker Usage

#### Quick Start

**Option 1: Using pre-built image**
```bash
docker run -d \
  --name a-healthy-dns \
  -p 53053:53053/udp \
  -e DNS_HOSTED_ZONE="example.com" \
  -e DNS_ZONE_RESOLUTIONS='{"www":{"ips":["192.168.1.100"],"health_port":8080}}' \
  -e DNS_NAME_SERVERS='["ns1.example.com"]' \
  indisoluble/a-healthy-dns
```

**Option 2: Using local image**
```bash
docker run -d \
  --name a-healthy-dns \
  -p 53053:53053/udp \
  -e DNS_HOSTED_ZONE="example.com" \
  -e DNS_ZONE_RESOLUTIONS='{"www":{"ips":["192.168.1.100"],"health_port":8080}}' \
  -e DNS_NAME_SERVERS='["ns1.example.com"]' \
  a-healthy-dns
```

#### Docker Compose

Copy the provided `docker-compose.example.yml` to `docker-compose.yml` and modify the environment variables as needed:

```bash
cp docker-compose.example.yml docker-compose.yml
# Edit docker-compose.yml with your configuration
docker-compose up -d
```

#### Docker Environment Variables

**Required Parameters:**
- `DNS_HOSTED_ZONE`: The domain name for which this DNS server is authoritative
- `DNS_ZONE_RESOLUTIONS`: JSON configuration defining subdomains and health check ports
- `DNS_NAME_SERVERS`: Name servers responsible for this zone (JSON array)

**Optional Parameters:**
- `DNS_PORT`: Port on which the DNS server will listen (default: 53053)
- `DNS_LOG_LEVEL`: Logging level (default: info)
- `DNS_TEST_MIN_INTERVAL`: Minimum interval between connectivity tests in seconds (default: 30)
- `DNS_TEST_TIMEOUT`: Timeout for each connection test in seconds (default: 2)
- `DNS_ALIAS_ZONES`: Additional domain names that resolve to the same records (JSON array)
- `DNS_PRIV_KEY_PATH`: Path to DNSSEC private key PEM file
- `DNS_PRIV_KEY_ALG`: DNSSEC private key algorithm (default: RSASHA256)

#### DNSSEC with Docker

```bash
# Create a directory for DNSSEC keys
mkdir -p ./keys
cp your-private-key.pem ./keys/

# Run with DNSSEC
docker run -d \
  --name a-healthy-dns \
  -p 53053:53053/udp \
  -v "$(pwd)/keys:/app/keys:ro" \
  -e DNS_HOSTED_ZONE="example.com" \
  -e DNS_ZONE_RESOLUTIONS='{"www":{"ips":["192.168.1.100"],"health_port":8080}}' \
  -e DNS_NAME_SERVERS='["ns1.example.com"]' \
  -e DNS_PRIV_KEY_PATH="/app/keys/your-private-key.pem" \
  indisoluble/a-healthy-dns
```

## Troubleshooting

### Docker Troubleshooting

#### Check if the service is running
```bash
# Test DNS resolution
dig @localhost -p 53053 www.example.com

# Check container status
docker ps | grep a-healthy-dns

# View logs
docker logs a-healthy-dns
docker logs -f a-healthy-dns  # Follow logs
```

#### Debug mode
```bash
docker run -it \
  -e DNS_LOG_LEVEL="debug" \
  -e DNS_HOSTED_ZONE="example.com" \
  -e DNS_ZONE_RESOLUTIONS='{"www":{"ips":["192.168.1.100"],"health_port":8080}}' \
  -e DNS_NAME_SERVERS='["ns1.example.com"]' \
  indisoluble/a-healthy-dns
```

#### Shell access
```bash
# Get a shell in the running container
docker exec -it a-healthy-dns sh

# Run a new container with shell access
docker run -it --entrypoint sh indisoluble/a-healthy-dns
```

### Performance Tuning

For high-performance scenarios, consider:
- Using host networking: `docker run --network host` (better performance, less isolation)
- Setting resource limits: `docker run --memory=256m --cpus=0.5`
- Running multiple instances behind a load balancer
- Monitoring packet drops: `docker exec a-healthy-dns cat /proc/net/snmp | grep Udp`