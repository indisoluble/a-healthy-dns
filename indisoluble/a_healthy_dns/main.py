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


_ARG_DNSSEC_PRIVATE_KEY_PATH = "dnssec_priv_key_path"
_ARG_LOG_LEVEL = "log_level"
_ARG_PORT = "port"
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
    parser = argparse.ArgumentParser(description="DNS server")
    parser.add_argument(
        "-z",
        "--hosted-zone",
        type=str,
        required=True,
        dest=dszf.ARG_HOSTED_ZONE,
        help="Hosted zone name",
    )
    parser.add_argument(
        "-n",
        "--name-servers",
        type=str,
        required=True,
        dest=dszf.ARG_NAME_SERVERS,
        help="List of name servers as JSON string (ex. [fqdn1, fqdn2, ...])",
    )
    parser.add_argument(
        "-r",
        "--zone-resolutions",
        type=str,
        required=True,
        dest=dszf.ARG_ZONE_RESOLUTIONS,
        help=(
            f"List of subdomains with their respective IPs and health ports as JSON string "
            f"(ex. {{sd1: {{'{dszf.ARG_SUBDOMAIN_IP_LIST}': [ip1, ip2, ...], "
            f"'{dszf.ARG_SUBDOMAIN_HEALTH_PORT}': port}}, ...}})"
        ),
    )
    parser.add_argument(
        "-p",
        "--port",
        type=int,
        default=_VAL_PORT,
        dest=_ARG_PORT,
        help=f"DNS server port (default: {_VAL_PORT})",
    )
    parser.add_argument(
        "-a",
        "--ttl-a",
        type=int,
        default=_VAL_TTL_A,
        dest=dszf.ARG_TTL_A,
        help=f"TTL in seconds for A records (default: {_VAL_TTL_A})",
    )
    parser.add_argument(
        "-s",
        "--ttl-ns",
        type=int,
        default=_VAL_TTL_NS,
        dest=dszf.ARG_TTL_NS,
        help=f"TTL in seconds for NS records (default: {_VAL_TTL_NS})",
    )
    parser.add_argument(
        "-o",
        "--ttl-soa",
        type=int,
        dest=dszf.ARG_TTL_SOA,
        help="TTL in seconds for SOA records (default: --ttl-a if not provided)",
    )
    parser.add_argument(
        "-f",
        "--soa-refresh",
        type=int,
        dest=dszf.ARG_SOA_REFRESH,
        help="SOA refresh time in seconds (default: --ttl-soa if not provided)",
    )
    parser.add_argument(
        "-t",
        "--soa-retry",
        type=int,
        dest=dszf.ARG_SOA_RETRY,
        help=f"SOA retry time in seconds (default: --ttl-soa//{_VAL_FACTOR_SOA_RETRY} if not provided)",
    )
    parser.add_argument(
        "-e",
        "--soa-expire",
        type=int,
        dest=dszf.ARG_SOA_EXPIRE,
        help=f"SOA expire time in seconds (default: --ttl-soa*{_VAL_FACTOR_SOA_EXPIRE} if not provided)",
    )
    parser.add_argument(
        "-m",
        "--soa-min-ttl",
        type=int,
        default=_VAL_SOA_MIN_TTL,
        dest=dszf.ARG_SOA_MIN_TTL,
        help=f"SOA minimum TTL in seconds (default: {_VAL_SOA_MIN_TTL})",
    )
    parser.add_argument(
        "-k",
        "--dnssec-priv-key-path",
        type=str,
        dest=_ARG_DNSSEC_PRIVATE_KEY_PATH,
        help="Path to DNSSEC private key PEM file",
    )
    parser.add_argument(
        "-g",
        "--dnssec-alg",
        type=str,
        choices=[
            dns.dnssec.algorithm_to_text(alg)
            for alg in dns.dnssectypes.Algorithm
            if alg < dns.dnssectypes.Algorithm.INDIRECT
        ],
        default=_VAL_DNSSEC_ALGORITHM,
        dest=dszf.ARG_DNSSEC_ALGORITHM,
        help=f"DNSSEC algorithm (default: {_VAL_DNSSEC_ALGORITHM})",
    )
    parser.add_argument(
        "-l",
        "--dnssec-ttl-dnskey",
        type=int,
        default=_VAL_DNSSEC_TTL_DNSKEY,
        dest=dszf.ARG_DNSSEC_TTL_DNSKEY,
        help=f"TTL in seconds for DNSKEY records (default: {_VAL_DNSSEC_TTL_DNSKEY})",
    )
    parser.add_argument(
        "-d",
        "--dnssec-lifetime",
        type=int,
        default=_VAL_DNSSEC_LIFETIME,
        dest=dszf.ARG_DNSSEC_LIFETIME,
        help=f"DNSSEC lifetime in seconds (default: {_VAL_DNSSEC_LIFETIME})",
    )
    parser.add_argument(
        "-i",
        "--test-interval",
        type=int,
        dest=ARG_TEST_INTERVAL,
        help=f"Interval in seconds for connectivity tests (default: --ttl-a//{_VAL_FACTOR_TEST_INTERVAL} if not provided)",
    )
    parser.add_argument(
        "-c",
        "--connection-timeout",
        type=int,
        default=_VAL_CONNECTION_TIMEOUT,
        dest=ARG_CONNECTION_TIMEOUT,
        help=f"Timeout in seconds for connectivity tests (default: {_VAL_CONNECTION_TIMEOUT})",
    )
    parser.add_argument(
        "-v",
        "--log-level",
        type=str,
        choices=[name.lower() for name in logging._levelToName.values()],
        default=_VAL_LOG_LEVEL,
        dest=_ARG_LOG_LEVEL,
        help=f"Logging level (default: {_VAL_LOG_LEVEL})",
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
        "SOA retry not provided, using A record TTL//%d as default: %d",
        _VAL_FACTOR_SOA_RETRY,
        result,
    )

    return result


def _derive_soa_expire(args: Dict[str, Any]) -> int:
    result = args[dszf.ARG_TTL_A] * _VAL_FACTOR_SOA_EXPIRE
    logging.info(
        "SOA expire not provided, using A record TTL*%d as default: %d",
        _VAL_FACTOR_SOA_EXPIRE,
        result,
    )

    return result


def _derive_test_interval(args: Dict[str, Any]) -> int:
    result = args[dszf.ARG_TTL_A] // _VAL_FACTOR_TEST_INTERVAL
    logging.info(
        "Test interval not provided, using A record TTL//%d as default: %d",
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

        logging.info("DNS server listening on port %d", config[_ARG_PORT])
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            logging.info("Shutting down DNS server")

    # Stop zone updater
    zone_updater.stop()


def main():
    args = _make_arg_parser().parse_args()
    _main(vars(args))
