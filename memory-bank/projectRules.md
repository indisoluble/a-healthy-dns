# Project Rules

Rules below are extracted from current implementation and tests, and should be preserved unless intentionally changed.

## Validation and Error Contract
- Validator helpers return `(bool, error_message)` instead of raising.
  - Evidence: `indisoluble/a_healthy_dns/tools/is_valid_ip.py:12-24`, `indisoluble/a_healthy_dns/tools/is_valid_port.py:12-20`, `indisoluble/a_healthy_dns/tools/is_valid_subdomain.py:12-26`.
- Constructors for domain objects raise `ValueError` when validation fails.
  - Evidence: `indisoluble/a_healthy_dns/records/a_healthy_ip.py:36-43`.
- Config factory logs and returns `None` for invalid configuration branches.
  - Evidence: `indisoluble/a_healthy_dns/dns_server_config_factory.py:55-67`, `indisoluble/a_healthy_dns/dns_server_config_factory.py:132-147`, `indisoluble/a_healthy_dns/dns_server_config_factory.py:162-176`.

## Data Modeling Rules
- Use immutable-style value objects with copy-on-change methods (`updated_status`, `updated_ips`).
  - Evidence: `indisoluble/a_healthy_dns/records/a_healthy_ip.py:48-55`, `indisoluble/a_healthy_dns/records/a_healthy_record.py:34-40`.
- Use sets/frozensets to deduplicate repeated IPs and nameservers.
  - Evidence: `indisoluble/a_healthy_dns/records/a_healthy_record.py:32`, `indisoluble/a_healthy_dns/dns_server_config_factory.py:158`, `indisoluble/a_healthy_dns/dns_server_config_factory.py:187`.

## Zone Update Rules
- Update zone via transaction writer context; rebuild records atomically.
  - Evidence: `indisoluble/a_healthy_dns/dns_server_zone_updater.py:168-173`.
- Always include NS and SOA at zone root on rebuild.
  - Evidence: `indisoluble/a_healthy_dns/dns_server_zone_updater.py:137-141`.
- Add A record only when at least one healthy endpoint exists.
  - Evidence: `indisoluble/a_healthy_dns/records/a_record.py:25-29`.

## DNS Query Handling Rules
- Always mark responses as authoritative (`AA`).
  - Evidence: `indisoluble/a_healthy_dns/dns_server_udp_handler.py:79`.
- Return `NXDOMAIN` for unmatched origins or missing subdomain nodes.
  - Evidence: `indisoluble/a_healthy_dns/dns_server_udp_handler.py:31-44`.
- Return `NOERROR` with empty answer when node exists but requested type does not.
  - Evidence: `indisoluble/a_healthy_dns/dns_server_udp_handler.py:46-54`.
- Return `FORMERR` when query has no question section.
  - Evidence: `indisoluble/a_healthy_dns/dns_server_udp_handler.py:90-93`.

## Timing Rules
- TTL and DNSSEC lifetimes are derived from `max_interval` through `records/time.py`.
  - Evidence: `indisoluble/a_healthy_dns/records/time.py:19-75`.
- SOA serial must advance monotonically and waits on duplicate-second timestamp.
  - Evidence: `indisoluble/a_healthy_dns/records/soa_record.py:29-40`.

## Test Rules
- Use pytest parameterization for validation matrices.
  - Evidence: `tests/indisoluble/a_healthy_dns/tools/test_is_valid_ip.py:8-67`.
- Use mocking for network/time/cryptographic side effects.
  - Evidence: `tests/indisoluble/a_healthy_dns/tools/test_can_create_connection.py:9-26`, `tests/indisoluble/a_healthy_dns/records/test_dnssec.py:12-66`.
