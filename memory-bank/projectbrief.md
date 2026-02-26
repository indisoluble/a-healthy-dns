# Project Brief

## Objective
Provide an authoritative UDP DNS service that returns A records only for currently healthy endpoints, with optional DNSSEC signing.

## Mission (Code-Derived)
- CLI service identifies itself as "A Healthy DNS server" and boots from console entrypoint `a-healthy-dns`. Evidence: `indisoluble/a_healthy_dns/main.py:108-110`, `setup.py:10-12`.
- Server binds UDP and serves authoritatively for configured zones. Evidence: `indisoluble/a_healthy_dns/main.py:233-242`, `indisoluble/a_healthy_dns/dns_server_udp_handler.py:78-80`.
- Record health is driven by periodic TCP connectivity checks on configured IP:port tuples. Evidence: `indisoluble/a_healthy_dns/dns_server_zone_updater.py:194-196`, `indisoluble/a_healthy_dns/tools/can_create_connection.py:13-21`.
- DNSSEC is optional and enabled only when private key path is provided. Evidence: `indisoluble/a_healthy_dns/dns_server_config_factory.py:232-236`, `indisoluble/a_healthy_dns/dns_server_zone_updater.py:148-167`.

## Required Inputs
- Hosted zone (`--hosted-zone`) is required. Evidence: `indisoluble/a_healthy_dns/main.py:133-138`.
- Zone resolutions JSON (`--zone-resolutions`) is required. Evidence: `indisoluble/a_healthy_dns/main.py:149-159`.
- Nameservers JSON (`--ns`) is required. Evidence: `indisoluble/a_healthy_dns/main.py:176-182`.

## Scope
- In scope:
  - Authoritative answers for configured subdomains and record types present in zone.
  - Alias zones mapped to same internal record namespace.
  - Dynamic zone regeneration based on health checks.
  - Optional DNSSEC signing lifecycle.
- Out of scope:
  - Recursive resolution/forwarding behavior (queries outside configured origins return NXDOMAIN). Evidence: `indisoluble/a_healthy_dns/dns_server_udp_handler.py:31-37`.
  - Persistent storage/database state (zone is in-memory). Evidence: `indisoluble/a_healthy_dns/dns_server_zone_updater.py:112`.

## Non-Functional Priorities
- Deterministic and validated startup (configuration returns `None` on invalid input). Evidence: `indisoluble/a_healthy_dns/dns_server_config_factory.py:218-236`.
- Fast health-driven updates without downtime by writing zone in transactions. Evidence: `indisoluble/a_healthy_dns/dns_server_zone_updater.py:169-173`.
- Security-focused container execution (non-root user, capability-limited binding). Evidence: `Dockerfile:39-55`, `Dockerfile:50-53`.
