# Database Schema

## Current State
- No database layer is present in this repository.
- No ORM models, migrations, SQL files, or persistence adapters were found.

## Actual Data Model (In-Memory)
- Zone data lives in `dns.versioned.Zone` inside updater instance.
  - Evidence: `indisoluble/a_healthy_dns/dns_server_zone_updater.py:72-75`, `indisoluble/a_healthy_dns/dns_server_zone_updater.py:112`.
- Endpoint health model:
  - `AHealthyIp(ip, health_port, is_healthy)`
  - `AHealthyRecord(subdomain, healthy_ips)`
  - Evidence: `indisoluble/a_healthy_dns/records/a_healthy_ip.py:16-47`, `indisoluble/a_healthy_dns/records/a_healthy_record.py:16-33`.
- Configuration model:
  - `DnsServerConfig(zone_origins, name_servers, a_records, ext_private_key)`
  - Evidence: `indisoluble/a_healthy_dns/dns_server_config_factory.py:31-38`.

## Implication
- Process restart loses runtime health state and rebuilt zone state; startup recreates from CLI/env configuration.
