# Decisions

This file records architecture decisions inferred from code behavior as of 2026-02-26.

## 2026-02-26: In-Memory Versioned Zone as Source of Truth
- Status: inferred-existing
- Context: DNS responses must be fast and reflect frequent health transitions.
- Decision: Maintain an in-memory `dns.versioned.Zone` and rebuild it transactionally.
- Evidence: `indisoluble/a_healthy_dns/dns_server_zone_updater.py:112`, `indisoluble/a_healthy_dns/dns_server_zone_updater.py:168-173`.
- Consequences:
  - Positive: low-latency serving path and simple read model for UDP handler.
  - Negative: no persistence across process restarts.

## 2026-02-26: Health-Driven A Record Publication via TCP Probes
- Status: inferred-existing
- Context: Subdomain endpoints can be up/down independently.
- Decision: Probe each `ip:health_port` with TCP connect and publish only healthy IPs.
- Evidence: `indisoluble/a_healthy_dns/dns_server_zone_updater.py:194-196`, `indisoluble/a_healthy_dns/tools/can_create_connection.py:13-21`, `indisoluble/a_healthy_dns/records/a_record.py:25-33`.
- Consequences:
  - Positive: DNS answers track backend availability automatically.
  - Negative: probe strategy is limited to TCP connect semantics.

## 2026-02-26: Optional DNSSEC with Automatic Re-Sign Scheduling
- Status: inferred-existing
- Context: Some deployments require signed zones while others do not.
- Decision: Enable DNSSEC only when a private key path is supplied; compute resign/expiration windows from interval math.
- Evidence: `indisoluble/a_healthy_dns/dns_server_config_factory.py:232-236`, `indisoluble/a_healthy_dns/records/dnssec.py:39-66`, `indisoluble/a_healthy_dns/dns_server_zone_updater.py:176-181`.
- Consequences:
  - Positive: flexible security posture per deployment.
  - Negative: operational key management burden for signed environments.

## 2026-02-26: Alias Zones Resolved Through Relative Name Mapping
- Status: inferred-existing
- Context: Same backend records should be reachable from multiple zone origins.
- Decision: Normalize primary + aliases as absolute names and resolve incoming absolute query names to a relative name via the most specific origin match.
- Evidence: `indisoluble/a_healthy_dns/records/zone_origins.py:33-46`.
- Consequences:
  - Positive: single record namespace serves many zones.
  - Negative: alias/origin overlap must be reasoned carefully to avoid ambiguity.
