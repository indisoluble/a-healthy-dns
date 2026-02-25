# Product Context

## Problem Statement
Traditional DNS servers serve static records. When a backend server goes down, clients continue to receive its IP address until an operator manually updates the zone or an external health-check system propagates the change. This creates downtime windows, especially in environments without dedicated load balancers (e.g. bare-metal, edge, homelab, small-scale deployments).

## Target Users
- **Self-hosters / Homelabbers**: Running services on bare-metal or small VMs without cloud load balancers.
- **Edge / IoT operators**: Need lightweight DNS-based failover without heavy infrastructure.
- **Small teams**: Want simple health-aware DNS for multi-server setups without external orchestration.

## User Goals
1. Point DNS at multiple backend IPs and have unreachable ones automatically excluded from responses.
2. Configure via CLI arguments or Docker environment variables — no config files, no databases.
3. Optionally sign the zone with DNSSEC for security-conscious deployments.
4. Support multiple domains (alias zones) resolving to the same set of backends.

## How It Works (User Perspective)
1. User starts `a-healthy-dns` with a hosted zone, subdomain→IP mappings (with health-check ports), and name servers.
2. The server immediately serves DNS queries on the configured port.
3. A background thread continuously checks each IP's health by attempting a TCP connection to its health port.
4. Only IPs that successfully respond are included in DNS A record answers.
5. If all IPs for a subdomain are unhealthy, the subdomain returns no A records (NOERROR with empty answer).

## Deployment Model
- **Docker**: Multi-stage build, non-root user (`appuser:10000`), `tini` init, capabilities restricted to `NET_BIND_SERVICE`, environment variables for all parameters.
- **CLI**: Direct execution via `a-healthy-dns` console script with argparse-driven configuration.
- **Default port**: 53053 (CLI) / 53 (Docker).

## Competitive Context
- Simpler than Consul DNS or Route53 health checks.
- No external dependencies, no agents on backends — just TCP port reachability.
- Unlike CoreDNS health plugins, this is a single-purpose binary with minimal surface area.
