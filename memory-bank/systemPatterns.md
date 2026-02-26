# System Patterns

## Runtime Architecture
1. Parse and validate CLI input.
2. Build immutable config object.
3. Initialize zone updater (threaded wrapper).
4. Build initial in-memory authoritative zone.
5. Serve UDP DNS requests from that zone.
6. Keep refreshing health and rebuilding zone in background.

Evidence: `indisoluble/a_healthy_dns/main.py:248-250`, `indisoluble/a_healthy_dns/main.py:221-242`, `indisoluble/a_healthy_dns/dns_server_zone_updater_threated.py:64-73`, `indisoluble/a_healthy_dns/dns_server_zone_updater_threated.py:47-56`.

## Core Components
- `dns_server_config_factory`:
  - Converts raw args into `DnsServerConfig`.
  - Performs validation and returns `None` on failure.
  - Builds zone origins, A records, NS records input, and optional DNSSEC key.
  - Evidence: `indisoluble/a_healthy_dns/dns_server_config_factory.py:50-69`, `indisoluble/a_healthy_dns/dns_server_config_factory.py:129-188`, `indisoluble/a_healthy_dns/dns_server_config_factory.py:218-243`.
- `DnsServerZoneUpdater`:
  - Maintains in-memory `dns.versioned.Zone`.
  - Rechecks endpoint health and conditionally rebuilds/signs zone.
  - Evidence: `indisoluble/a_healthy_dns/dns_server_zone_updater.py:69-75`, `indisoluble/a_healthy_dns/dns_server_zone_updater.py:236-253`.
- `DnsServerUdpHandler`:
  - Parses DNS wire format.
  - Resolves query name relative to hosted or alias origins.
  - Returns authoritative answers/rcode.
  - Evidence: `indisoluble/a_healthy_dns/dns_server_udp_handler.py:72-95`, `indisoluble/a_healthy_dns/dns_server_udp_handler.py:31-63`.

## Data Model Pattern
- `AHealthyIp`: validated immutable value object (normalized IP, port, health status) with copy-on-change semantics.
  - Evidence: `indisoluble/a_healthy_dns/records/a_healthy_ip.py:34-55`.
- `AHealthyRecord`: subdomain-keyed set of healthy IP objects with copy-on-change semantics.
  - Evidence: `indisoluble/a_healthy_dns/records/a_healthy_record.py:29-40`.
- `ZoneOrigins`: canonical absolute primary+aliases with longest-match relativization.
  - Evidence: `indisoluble/a_healthy_dns/records/zone_origins.py:33-46`.

## Update/Rebuild Pattern
- Health refresh is separated from zone write:
  - Step A: refresh health states.
  - Step B: decide if update required (changes, first build, or sign near expiry).
  - Step C: clear and rebuild zone transactionally.
- Evidence: `indisoluble/a_healthy_dns/dns_server_zone_updater.py:211-253`, `indisoluble/a_healthy_dns/dns_server_zone_updater.py:168-173`.

## DNSSEC Pattern
- If key configured:
  - Build signing key iterator with inception/expiration/resign.
  - Sign full zone during rebuild.
  - Re-sign when `resign` threshold reached.
- Evidence: `indisoluble/a_healthy_dns/records/dnssec.py:39-66`, `indisoluble/a_healthy_dns/dns_server_zone_updater.py:148-167`, `indisoluble/a_healthy_dns/dns_server_zone_updater.py:176-181`.

## Concurrency Pattern
- One daemon thread loops updates.
- Stop signal is `threading.Event`; updater checks abort callback during record iteration.
- Graceful stop joins with timeout based on connection timeout.
- Evidence: `indisoluble/a_healthy_dns/dns_server_zone_updater_threated.py:44-56`, `indisoluble/a_healthy_dns/dns_server_zone_updater.py:190-193`, `indisoluble/a_healthy_dns/dns_server_zone_updater_threated.py:80-87`.

## Error-Handling Pattern
- Input/config failures return `None` and log message.
- Runtime parse failures in UDP handler are logged and dropped (no response).
- No question section returns FORMERR response.
- Evidence: `indisoluble/a_healthy_dns/dns_server_config_factory.py:55-67`, `indisoluble/a_healthy_dns/dns_server_udp_handler.py:73-76`, `indisoluble/a_healthy_dns/dns_server_udp_handler.py:90-93`.
