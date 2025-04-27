#!/usr/bin/env python3

import argparse
import logging
import socketserver

from typing import Any, Dict

from . import dns_server_zone_factory as dszf
from .dns_server_udp_handler import DnsServerUdpHandler
from .dns_server_zone_updater import (
    ARG_CONNECTION_TIMEOUT,
    ARG_TEST_INTERVAL,
    DnsServerZoneUpdater,
)


_ARG_LOG_LEVEL = "log_level"
_ARG_PORT = "port"
_VAL_CONNECTION_TIMEOUT = 2
_VAL_FACTOR_SOA_EXPIRE = 30
_VAL_FACTOR_SOA_RETRY = 4
_VAL_FACTOR_TEST_INTERVAL = 2
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
        "-l",
        "--log-level",
        type=str,
        choices=[name.lower() for name in logging._levelToName.values()],
        default=logging._levelToName[logging.INFO].lower(),
        dest=_ARG_LOG_LEVEL,
        help=f"Logging level (default: {logging._levelToName[logging.INFO].lower()})",
    )

    return parser


def _completed_config(args: Dict[str, Any]):
    if not args[dszf.ARG_TTL_SOA]:
        args[dszf.ARG_TTL_SOA] = args[dszf.ARG_TTL_A]
        logging.info(
            "SOA TTL not provided, using A record TTL as default: %d",
            args[dszf.ARG_TTL_SOA],
        )

    if not args[dszf.ARG_SOA_REFRESH]:
        args[dszf.ARG_SOA_REFRESH] = args[dszf.ARG_TTL_SOA]
        logging.info(
            "SOA refresh not provided, using SOA record TTL as default: %d",
            args[dszf.ARG_SOA_REFRESH],
        )

    if not args[dszf.ARG_SOA_RETRY]:
        args[dszf.ARG_SOA_RETRY] = args[dszf.ARG_TTL_SOA] // _VAL_FACTOR_SOA_RETRY
        logging.info(
            "SOA retry not provided, using SOA record TTL//%d as default: %d",
            _VAL_FACTOR_SOA_RETRY,
            args[dszf.ARG_SOA_RETRY],
        )

    if not args[dszf.ARG_SOA_EXPIRE]:
        args[dszf.ARG_SOA_EXPIRE] = args[dszf.ARG_TTL_SOA] * _VAL_FACTOR_SOA_EXPIRE
        logging.info(
            "SOA expire not provided, using SOA record TTL*%d as default: %d",
            _VAL_FACTOR_SOA_EXPIRE,
            args[dszf.ARG_SOA_EXPIRE],
        )

    if not args[ARG_TEST_INTERVAL]:
        args[ARG_TEST_INTERVAL] = args[dszf.ARG_TTL_A] // _VAL_FACTOR_TEST_INTERVAL
        logging.info(
            "Test interval not provided, using A record TTL//%d as default: %d",
            _VAL_FACTOR_TEST_INTERVAL,
            args[ARG_TEST_INTERVAL],
        )


def _main(args: Dict[str, Any]):
    # Set up logging
    numeric_level = getattr(logging, args[_ARG_LOG_LEVEL].upper())
    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s - %(levelname)s - %(module)s.%(funcName)s - %(message)s",
    )

    # Complete config
    _completed_config(args)

    # Compose zone
    ext_zone = dszf.make_zone(args)
    if not ext_zone:
        logging.error("Invalid zone configuration")
        return

    # Start zone updater
    zone_updater = DnsServerZoneUpdater(ext_zone, args)
    zone_updater.start()

    # Launch DNS server
    server_address = ("", args[_ARG_PORT])
    with socketserver.UDPServer(server_address, DnsServerUdpHandler) as server:
        server.zone = ext_zone.zone

        logging.info("DNS server listening on port %d", args[_ARG_PORT])
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            logging.info("Shutting down DNS server")

    # Stop zone updater
    zone_updater.stop()


def main():
    args = _make_arg_parser().parse_args()
    _main(vars(args))
