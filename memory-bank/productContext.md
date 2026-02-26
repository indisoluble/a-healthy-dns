# Product Context

## Problem Being Solved
- Operators need DNS answers that follow backend service health automatically, so traffic avoids unreachable endpoints.
- The implementation checks each configured endpoint over TCP and includes only healthy IPs in A responses. Evidence: `indisoluble/a_healthy_dns/dns_server_zone_updater.py:189-209`, `indisoluble/a_healthy_dns/records/a_record.py:25-33`.

## Primary Users
- Platform/SRE teams operating self-managed services behind DNS.
- Teams needing one hosted zone plus aliases with shared resolution rules. Evidence: `indisoluble/a_healthy_dns/records/zone_origins.py:33-46`.
- Teams requiring optional DNSSEC signing for authoritative zones. Evidence: `indisoluble/a_healthy_dns/dns_server_config_factory.py:201-216`, `indisoluble/a_healthy_dns/records/dnssec.py:39-66`.

## User-Facing Behaviors
- A query for configured domain+record returns `NOERROR` plus answer when data exists. Evidence: `indisoluble/a_healthy_dns/dns_server_udp_handler.py:61-63`.
- A query for existing name with missing record type returns `NOERROR` with empty answer section. Evidence: `indisoluble/a_healthy_dns/dns_server_udp_handler.py:46-54`.
- Query outside hosted/alias zones returns `NXDOMAIN`. Evidence: `indisoluble/a_healthy_dns/dns_server_udp_handler.py:31-37`.
- Query for unknown subdomain within zone returns `NXDOMAIN`. Evidence: `indisoluble/a_healthy_dns/dns_server_udp_handler.py:40-44`.

## Operational Inputs
- Command line arguments define zone, aliases, subdomain endpoint sets, health timing, and DNSSEC settings. Evidence: `indisoluble/a_healthy_dns/main.py:131-201`.
- Container runtime supports equivalent environment-variable configuration. Evidence: `Dockerfile:65-127`.

## Expected Value
- Safer traffic steering with no external control plane for health-based DNS updates.
- One deployable binary/container with reproducible CI checks for Python logic and Docker behavior. Evidence: `.github/workflows/test-py-code.yml:24-33`, `.github/workflows/test-docker.yml:23-148`.
