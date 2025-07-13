# A Healthy DNS

A health-aware DNS server that performs health checks on IP addresses and automatically updates DNS responses based on the health status of backend services.
This ensures that DNS queries only return healthy endpoints, providing automatic failover and load balancing capabilities.

## Features

- **Health Checking**: Continuously monitors IP addresses via TCP connectivity tests
- **Dynamic Updates**: Automatically updates DNS zones based on health check results
- **Configurable TTL**: TTL calculation based on health check intervals
- **Threaded Operations**: Background health checking
- **Multiple Records**: Support for multiple IP addresses per subdomain with individual health tracking
- **DNSSEC Support**: Optional DNSSEC signing

## Installation

### Prerequisites

- Python 3.7 or higher
- pip package manager

### Install from Source

1. Clone the repository:
   ```bash
   git clone https://github.com/indisoluble/a-healthy-dns.git
   cd a-healthy-dns
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
- `cryptography>=44.0.2,<45.0.0` - For DNSSEC cryptographic operations
- `dnspython>=2.7.0,<3.0.0` - For DNS protocol handling

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

#### DNSSEC Parameters

- `--priv-key-path`: Path to the DNSSEC private key file for zone signing
- `--priv-key-alg`: Algorithm used for DNSSEC signing (default: RSASHA256)

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