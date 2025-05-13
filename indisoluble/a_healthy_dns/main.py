#!/usr/bin/env python3

import argparse
import logging
import socketserver

import dns.dnssec
import dns.dnssectypes

from typing import Any, Dict, Optional

from . import dns_server_zone_factory as dszf
from .dns_server_udp_handler import DnsServerUdpHandler
from .dns_server_zone_updater import (
    ARG_CONNECTION_TIMEOUT,
    ARG_TEST_INTERVAL,
    DnsServerZoneUpdater,
)


_ARG_DNSSEC_PRIVATE_KEY_PATH = "priv_key_path"
_ARG_LOG_LEVEL = "log_level"
_ARG_PORT = "port"
_GRP_A_RECORDS = "Address (A) records"
_GRP_CONNECTIVITY_TESTS = "Connectivity tests"
_GRP_GENERAL = "General"
_GRP_DNSSEC_PARAMS = "DNS Security Extensions (DNSSEC) parameters"
_GRP_NS_RECORDS = "Name Server (NS) records"
_GRP_SOA_RECORDS = "Start of Authority (SOA) records"
_GRP_ZONE_RESOLUTIONS = "Zone resolutions"
_NAME_DNSKEY_TTL = "dnskey-ttl"
_NAME_DNSSEC_LIFETIME = "dnssec-lifetime"
_NAME_HOSTED_ZONE = "hosted-zone"
_NAME_LOG_LEVEL = "log-level"
_NAME_NAME_SERVERS = "ns"
_NAME_NS_TTL = "ns-ttl"
_NAME_PORT = "port"
_NAME_PRIV_KEY_ALG = "priv-key-alg"
_NAME_PRIV_KEY_PATH = "priv-key-path"
_NAME_SOA_EXPIRE = "soa-expire"
_NAME_SOA_MIN_TTL = "soa-min-ttl"
_NAME_SOA_REFRESH = "soa-refresh"
_NAME_SOA_RETRY = "soa-retry"
_NAME_SOA_TTL = "soa-ttl"
_NAME_TEST_INTERVAL = "test-interval"
_NAME_TEST_TIMEOUT = "test-timeout"
_NAME_TTL_A = "a-ttl"
_NAME_ZONE_RESOLUTIONS = "zone-resolutions"
_VAL_CONNECTION_TIMEOUT = 2
_VAL_DNSSEC_ALGORITHM = dns.dnssec.algorithm_to_text(
    dns.dnssectypes.Algorithm.RSASHA256
)
_VAL_DNSSEC_LIFETIME = 1209600  # 14 days
_VAL_DNSSEC_TTL_DNSKEY = 86400  # 24 hours
_VAL_FACTOR_SOA_EXPIRE = 30
_VAL_FACTOR_SOA_RETRY = 4
_VAL_FACTOR_TEST_INTERVAL = 2
_VAL_LOG_LEVEL = logging._levelToName[logging.INFO].lower()
_VAL_PORT = 53053
_VAL_SOA_MIN_TTL = 600  # 10 minutes
_VAL_TTL_A = 60  # 1 minute
_VAL_TTL_NS = 86400  # 24 hours


def _make_arg_parser() -> argparse.ArgumentParser:
    epilog = f"""
Parameter details
=================

{_GRP_GENERAL}
{len(_GRP_GENERAL) * '-'}
--{_NAME_PORT}: Port on which the DNS server will listen for incoming DNS requests.
--{_NAME_LOG_LEVEL}: Controls verbosity of log output (debug, info, warning, error, critical).

{_GRP_ZONE_RESOLUTIONS}
{len(_GRP_ZONE_RESOLUTIONS) * '-'}
--{_NAME_HOSTED_ZONE}: The domain name for which this DNS server is authoritative.
--{_NAME_ZONE_RESOLUTIONS}: JSON configuration defining subdomains, their IP addresses, and health check ports.

Examples:
    --{_NAME_HOSTED_ZONE} example.com
    --{_NAME_ZONE_RESOLUTIONS} '{{"www":{{"ips":["192.168.1.100","192.168.1.101"],"health_port":8080}},"api":{{"ips":["192.168.1.102"],"health_port":8000}}}}'

{_GRP_CONNECTIVITY_TESTS}
{len(_GRP_CONNECTIVITY_TESTS) * '-'}
--{_NAME_TEST_INTERVAL}: How often to check if IPs are healthy (in seconds).
--{_NAME_TEST_TIMEOUT}: Maximum time to wait for a health check response (in seconds).

{_GRP_A_RECORDS}
{len(_GRP_A_RECORDS) * '-'}
--{_NAME_TTL_A}: Time-to-live for A records (in seconds). Controls how long DNS resolvers cache the IP addresses.

{_GRP_NS_RECORDS}
{len(_GRP_NS_RECORDS) * '-'}
--{_NAME_NAME_SERVERS}: Name servers responsible for this zone (JSON array).
--{_NAME_NS_TTL}: Time-to-live for NS records (in seconds). Controls how long DNS resolvers cache the IP addresses.

Examples:
    --{_NAME_NAME_SERVERS} '["ns1.example.com", "ns2.example.com"]'

{_GRP_SOA_RECORDS}
{len(_GRP_SOA_RECORDS) * '-'}
--{_NAME_SOA_TTL}: Time-to-live for SOA record (in seconds). Controls how long DNS resolvers cache the IP addresses.
--{_NAME_SOA_REFRESH}: Time interval secondary servers wait before requesting zone updates (in seconds).
--{_NAME_SOA_RETRY}: Time interval to wait before retrying failed zone transfers (in seconds).
--{_NAME_SOA_EXPIRE}: Time after which secondary servers should stop answering queries if primary is unreachable (in seconds).
--{_NAME_SOA_MIN_TTL}: How long a resolver should cache negative responses (NXDOMAIN) (in seconds).

{_GRP_DNSSEC_PARAMS}
{len(_GRP_DNSSEC_PARAMS) * '-'}
--{_NAME_PRIV_KEY_PATH}: Path to the DNSSEC private key file for zone signing.
--{_NAME_PRIV_KEY_ALG}: Algorithm used for DNSSEC signing.
--{_NAME_DNSKEY_TTL}: Time-to-live for DNSKEY records (in seconds). Controls how long DNS resolvers cache the IP addresses.
--{_NAME_DNSSEC_LIFETIME}: How long DNSSEC signatures are valid (in seconds).

Example usage
=============
a_healthy_dns \\
    --{_NAME_HOSTED_ZONE} example.com \\
    --{_NAME_ZONE_RESOLUTIONS} '{{"www":{{"ips":["192.168.1.100"],"health_port":8080}}}}' \\
    --{_NAME_NAME_SERVERS} '["ns1.example.com"]' \\
    --{_NAME_PORT} 53053
"""
    parser = argparse.ArgumentParser(
        description="A Healthy DNS server",
        epilog=epilog,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    general_group = parser.add_argument_group(_GRP_GENERAL)
    general_group.add_argument(
        f"--{_NAME_PORT}",
        type=int,
        default=_VAL_PORT,
        dest=_ARG_PORT,
        help=f"DNS server port (default: {_VAL_PORT})",
    )
    general_group.add_argument(
        f"--{_NAME_LOG_LEVEL}",
        type=str,
        choices=[
            name.lower() for name in logging._levelToName.values() if name != "NOTSET"
        ],
        default=_VAL_LOG_LEVEL,
        dest=_ARG_LOG_LEVEL,
        help=f"Logging level (default: {_VAL_LOG_LEVEL})",
    )
    res_group = parser.add_argument_group(_GRP_ZONE_RESOLUTIONS)
    res_group.add_argument(
        f"--{_NAME_HOSTED_ZONE}",
        type=str,
        required=True,
        dest=dszf.ARG_HOSTED_ZONE,
        help="Hosted zone name",
    )
    res_group.add_argument(
        f"--{_NAME_ZONE_RESOLUTIONS}",
        type=str,
        required=True,
        dest=dszf.ARG_ZONE_RESOLUTIONS,
        help=(
            f"Subdomains with IPs and health ports as JSON string "
            f"(ex. {{sd1: {{'{dszf.ARG_SUBDOMAIN_IP_LIST}': [ip1, ip2, ...], "
            f"'{dszf.ARG_SUBDOMAIN_HEALTH_PORT}': port}}, ...}})"
        ),
    )
    conn_group = parser.add_argument_group(_GRP_CONNECTIVITY_TESTS)
    conn_group.add_argument(
        f"--{_NAME_TEST_INTERVAL}",
        type=int,
        dest=ARG_TEST_INTERVAL,
        help=f"Interval for connectivity tests (default: {_NAME_TTL_A} // {_VAL_FACTOR_TEST_INTERVAL})",
    )
    conn_group.add_argument(
        f"--{_NAME_TEST_TIMEOUT}",
        type=int,
        default=_VAL_CONNECTION_TIMEOUT,
        dest=ARG_CONNECTION_TIMEOUT,
        help=f"Timeout for each connection test (default: {_VAL_CONNECTION_TIMEOUT} seconds)",
    )
    a_group = parser.add_argument_group(_GRP_A_RECORDS)
    a_group.add_argument(
        f"--{_NAME_TTL_A}",
        type=int,
        default=_VAL_TTL_A,
        dest=dszf.ARG_TTL_A,
        help=f"TTL for A records (default: {_VAL_TTL_A} seconds)",
    )
    ns_group = parser.add_argument_group(_GRP_NS_RECORDS)
    ns_group.add_argument(
        f"--{_NAME_NAME_SERVERS}",
        type=str,
        required=True,
        dest=dszf.ARG_NAME_SERVERS,
        help="Name servers as JSON string (ex. [fqdn1, fqdn2, ...])",
    )
    ns_group.add_argument(
        f"--{_NAME_NS_TTL}",
        type=int,
        default=_VAL_TTL_NS,
        dest=dszf.ARG_TTL_NS,
        help=f"TTL for NS records (default: {_VAL_TTL_NS} seconds)",
    )
    soa_group = parser.add_argument_group(_GRP_SOA_RECORDS)
    soa_group.add_argument(
        f"--{_NAME_SOA_TTL}",
        type=int,
        dest=dszf.ARG_TTL_SOA,
        help=f"TTL for SOA records (default: {_NAME_TTL_A})",
    )
    soa_group.add_argument(
        f"--{_NAME_SOA_REFRESH}",
        type=int,
        dest=dszf.ARG_SOA_REFRESH,
        help=f"SOA refresh time (default: {_NAME_TTL_A})",
    )
    soa_group.add_argument(
        f"--{_NAME_SOA_RETRY}",
        type=int,
        dest=dszf.ARG_SOA_RETRY,
        help=f"SOA retry time (default: {_NAME_TTL_A} // {_VAL_FACTOR_SOA_RETRY})",
    )
    soa_group.add_argument(
        f"--{_NAME_SOA_EXPIRE}",
        type=int,
        dest=dszf.ARG_SOA_EXPIRE,
        help=f"SOA expire time (default: {_NAME_TTL_A} * {_VAL_FACTOR_SOA_EXPIRE})",
    )
    soa_group.add_argument(
        f"--{_NAME_SOA_MIN_TTL}",
        type=int,
        default=_VAL_SOA_MIN_TTL,
        dest=dszf.ARG_SOA_MIN_TTL,
        help=f"SOA minimum TTL (default: {_VAL_SOA_MIN_TTL} seconds)",
    )
    dnssec_group = parser.add_argument_group(_GRP_DNSSEC_PARAMS)
    dnssec_group.add_argument(
        f"--{_NAME_PRIV_KEY_PATH}",
        type=str,
        dest=_ARG_DNSSEC_PRIVATE_KEY_PATH,
        help="Path to DNSSEC private key PEM file",
    )
    dnssec_group.add_argument(
        f"--{_NAME_PRIV_KEY_ALG}",
        type=str,
        choices=[
            dns.dnssec.algorithm_to_text(alg)
            for alg in dns.dnssectypes.Algorithm
            if alg < dns.dnssectypes.Algorithm.INDIRECT
        ],
        default=_VAL_DNSSEC_ALGORITHM,
        dest=dszf.ARG_DNSSEC_ALGORITHM,
        help=f"DNSSEC private key algorithm (default: {_VAL_DNSSEC_ALGORITHM})",
    )
    dnssec_group.add_argument(
        f"--{_NAME_DNSKEY_TTL}",
        type=int,
        default=_VAL_DNSSEC_TTL_DNSKEY,
        dest=dszf.ARG_DNSSEC_TTL_DNSKEY,
        help=f"TTL for DNSKEY records (default: {_VAL_DNSSEC_TTL_DNSKEY} seconds)",
    )
    dnssec_group.add_argument(
        f"--{_NAME_DNSSEC_LIFETIME}",
        type=int,
        default=_VAL_DNSSEC_LIFETIME,
        dest=dszf.ARG_DNSSEC_LIFETIME,
        help=f"DNSSEC lifetime (default: {_VAL_DNSSEC_LIFETIME} seconds)",
    )

    return parser


def _derive_if_none(value: Optional[Any]) -> bool:
    return value is None


def _derive_if_informed(value: Optional[Any]) -> bool:
    return value is not None


def _derive_ttl_soa(args: Dict[str, Any]) -> int:
    result = args[dszf.ARG_TTL_A]
    logging.info("SOA TTL not provided, using A record TTL as default: %d", result)

    return result


def _derive_soa_refresh(args: Dict[str, Any]) -> int:
    result = args[dszf.ARG_TTL_A]
    logging.info("SOA refresh not provided, using A record TTL as default: %d", result)

    return result


def _derive_soa_retry(args: Dict[str, Any]) -> int:
    result = args[dszf.ARG_TTL_A] // _VAL_FACTOR_SOA_RETRY
    logging.info(
        "SOA retry not provided, using A record TTL // %d as default: %d",
        _VAL_FACTOR_SOA_RETRY,
        result,
    )

    return result


def _derive_soa_expire(args: Dict[str, Any]) -> int:
    result = args[dszf.ARG_TTL_A] * _VAL_FACTOR_SOA_EXPIRE
    logging.info(
        "SOA expire not provided, using A record TTL * %d as default: %d",
        _VAL_FACTOR_SOA_EXPIRE,
        result,
    )

    return result


def _derive_test_interval(args: Dict[str, Any]) -> int:
    result = args[dszf.ARG_TTL_A] // _VAL_FACTOR_TEST_INTERVAL
    logging.info(
        "Test interval not provided, using A record TTL // %d as default: %d",
        _VAL_FACTOR_TEST_INTERVAL,
        result,
    )

    return result


def _load_dnssec_private_key(args: Dict[str, Any]) -> Optional[bytes]:
    try:
        with open(args[_ARG_DNSSEC_PRIVATE_KEY_PATH], "rb") as key_file:
            private_key = key_file.read()
            logging.info(
                "Loaded DNSSEC private key from %s", args[_ARG_DNSSEC_PRIVATE_KEY_PATH]
            )
            return private_key
    except Exception as ex:
        logging.error("Failed to load DNSSEC private key: %s", ex)
        return None


def _normalize_config(args: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    actions = {
        dszf.ARG_TTL_SOA: (_derive_if_none, dszf.ARG_TTL_SOA, _derive_ttl_soa),
        dszf.ARG_SOA_REFRESH: (
            _derive_if_none,
            dszf.ARG_SOA_REFRESH,
            _derive_soa_refresh,
        ),
        dszf.ARG_SOA_RETRY: (_derive_if_none, dszf.ARG_SOA_RETRY, _derive_soa_retry),
        dszf.ARG_SOA_EXPIRE: (_derive_if_none, dszf.ARG_SOA_EXPIRE, _derive_soa_expire),
        ARG_TEST_INTERVAL: (_derive_if_none, ARG_TEST_INTERVAL, _derive_test_interval),
        _ARG_DNSSEC_PRIVATE_KEY_PATH: (
            _derive_if_informed,
            dszf.ARG_DNSSEC_PRIVATE_KEY_PEM,
            _load_dnssec_private_key,
        ),
    }

    config = {}
    for key, value in args.items():
        if key not in actions:
            config[key] = value
            continue

        condition, destination_key, derive = actions[key]
        if not condition(value):
            config[destination_key] = value
            continue

        derived_value = derive(args)
        if derived_value is None:
            return None

        config[destination_key] = derived_value

    return config


def _main(args: Dict[str, Any]):
    # Set up logging
    numeric_level = getattr(logging, args[_ARG_LOG_LEVEL].upper())
    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s - %(levelname)s - %(module)s.%(funcName)s - %(message)s",
    )

    # Complete config
    config = _normalize_config(args)
    if not config:
        return

    # Compose zone
    ext_zone = dszf.make_zone(config)
    if not ext_zone:
        return

    # Start zone updater
    zone_updater = DnsServerZoneUpdater(ext_zone, config)
    zone_updater.start()

    # Launch DNS server
    server_address = ("", config[_ARG_PORT])
    with socketserver.UDPServer(server_address, DnsServerUdpHandler) as server:
        server.zone = ext_zone.zone

        logging.info("DNS server listening on port %d...", config[_ARG_PORT])
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            logging.info("Shutting down DNS server...")

    # Stop zone updater
    zone_updater.stop()


def main():
    args = _make_arg_parser().parse_args()
    _main(vars(args))
