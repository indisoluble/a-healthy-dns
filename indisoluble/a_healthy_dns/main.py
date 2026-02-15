#!/usr/bin/env python3

import argparse
import json
import logging
import signal
import socketserver
import threading

import dns.dnssec
import dns.dnssectypes

from functools import partial
from typing import Any, Dict

from indisoluble.a_healthy_dns.dns_server_config_factory import (
    ARG_ALIAS_ZONES,
    ARG_DNSSEC_ALGORITHM,
    ARG_DNSSEC_PRIVATE_KEY_PATH,
    ARG_HOSTED_ZONE,
    ARG_NAME_SERVERS,
    ARG_SUBDOMAIN_HEALTH_PORT,
    ARG_SUBDOMAIN_IP_LIST,
    ARG_ZONE_RESOLUTIONS,
    make_config,
)
from indisoluble.a_healthy_dns.dns_server_udp_handler import DnsServerUdpHandler
from indisoluble.a_healthy_dns.dns_server_zone_updater_threated import (
    DnsServerZoneUpdaterThreated,
)


_ARG_CONNECTION_TIMEOUT = "timeout"
_ARG_LOG_LEVEL = "log_level"
_ARG_MIN_TEST_INTERVAL = "min_interval"
_ARG_PORT = "port"
_GRP_CONNECTIVITY_TESTS = "connectivity test arguments"
_GRP_DNSSEC_PARAMS = "dns security extensions (DNSSEC) arguments"
_GRP_GENERAL = "general arguments"
_GRP_NS_RECORDS = "name server (NS) arguments"
_GRP_ZONE_RESOLUTIONS = "zone resolution arguments"
_NAME_ALIAS_ZONES = "alias-zones"
_NAME_HOSTED_ZONE = "hosted-zone"
_NAME_LOG_LEVEL = "log-level"
_NAME_NAME_SERVERS = "ns"
_NAME_PORT = "port"
_NAME_PRIV_KEY_ALG = "priv-key-alg"
_NAME_PRIV_KEY_PATH = "priv-key-path"
_NAME_TEST_MIN_INTERVAL = "test-min-interval"
_NAME_TEST_TIMEOUT = "test-timeout"
_NAME_ZONE_RESOLUTIONS = "zone-resolutions"
_VAL_ALIAS_ZONES = json.dumps([])
_VAL_CONNECTION_TIMEOUT = 2
_VAL_DNSSEC_ALGORITHM = dns.dnssec.algorithm_to_text(
    dns.dnssectypes.Algorithm.RSASHA256
)
_VAL_LOG_LEVEL = logging._levelToName[logging.INFO].lower()
_VAL_MIN_TEST_INTERVAL = 30
_VAL_PORT = 53053


def _make_arg_parser() -> argparse.ArgumentParser:
    epilog = f"""
Argument details
================

{_GRP_GENERAL}
{len(_GRP_GENERAL) * '-'}
--{_NAME_PORT}: Port on which the DNS server will listen for incoming DNS requests.
--{_NAME_LOG_LEVEL}: Controls verbosity of log output (debug, info, warning, error, critical).

{_GRP_ZONE_RESOLUTIONS}
{len(_GRP_ZONE_RESOLUTIONS) * '-'}
--{_NAME_HOSTED_ZONE}: The domain name for which this DNS server is authoritative.
--{_NAME_ALIAS_ZONES}: Additional domain names that resolve to the same records without duplicating health checks.
--{_NAME_ZONE_RESOLUTIONS}: JSON configuration defining subdomains, their IP addresses, and health check ports.

Examples:
    --{_NAME_HOSTED_ZONE} example.com
    --{_NAME_ALIAS_ZONES} '["alias1.com", "alias2.com"]'
    --{_NAME_ZONE_RESOLUTIONS} '{{"www":{{"ips":["192.168.1.100","192.168.1.101"],"health_port":8080}},"api":{{"ips":["192.168.1.102"],"health_port":8000}}}}'

{_GRP_CONNECTIVITY_TESTS}
{len(_GRP_CONNECTIVITY_TESTS) * '-'}
--{_NAME_TEST_MIN_INTERVAL}: Minimum interval between tests of a given IP (in seconds).
--{_NAME_TEST_TIMEOUT}: Maximum time to wait for a health check response (in seconds).

{_GRP_NS_RECORDS}
{len(_GRP_NS_RECORDS) * '-'}
--{_NAME_NAME_SERVERS}: Name servers responsible for this zone (JSON array).

Examples:
    --{_NAME_NAME_SERVERS} '["ns1.example.com", "ns2.example.com"]'

{_GRP_DNSSEC_PARAMS}
{len(_GRP_DNSSEC_PARAMS) * '-'}
--{_NAME_PRIV_KEY_PATH}: Path to the DNSSEC private key file for zone signing.
--{_NAME_PRIV_KEY_ALG}: Algorithm used for DNSSEC signing.

Example usage
=============
%(prog)s \\
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
        dest=ARG_HOSTED_ZONE,
        help="Hosted zone name",
    )
    res_group.add_argument(
        f"--{_NAME_ALIAS_ZONES}",
        type=str,
        default=_VAL_ALIAS_ZONES,
        dest=ARG_ALIAS_ZONES,
        help=(
            "Alias zones that resolve to the same records as the hosted zone "
            f'(ex. ["alias1.com", "alias2.com"], default: {_VAL_ALIAS_ZONES})'
        ),
    )
    res_group.add_argument(
        f"--{_NAME_ZONE_RESOLUTIONS}",
        type=str,
        required=True,
        dest=ARG_ZONE_RESOLUTIONS,
        help=(
            f"Subdomains with IPs and health ports as JSON string "
            f"(ex. {{sd1: {{'{ARG_SUBDOMAIN_IP_LIST}': [ip1, ip2, ...], "
            f"'{ARG_SUBDOMAIN_HEALTH_PORT}': port}}, ...}})"
        ),
    )
    conn_group = parser.add_argument_group(_GRP_CONNECTIVITY_TESTS)
    conn_group.add_argument(
        f"--{_NAME_TEST_MIN_INTERVAL}",
        type=int,
        default=_VAL_MIN_TEST_INTERVAL,
        dest=_ARG_MIN_TEST_INTERVAL,
        help=f"Minimum interval between connectivity tests (default: {_VAL_MIN_TEST_INTERVAL} seconds)",
    )
    conn_group.add_argument(
        f"--{_NAME_TEST_TIMEOUT}",
        type=int,
        default=_VAL_CONNECTION_TIMEOUT,
        dest=_ARG_CONNECTION_TIMEOUT,
        help=f"Timeout for each connection test (default: {_VAL_CONNECTION_TIMEOUT} seconds)",
    )
    ns_group = parser.add_argument_group(_GRP_NS_RECORDS)
    ns_group.add_argument(
        f"--{_NAME_NAME_SERVERS}",
        type=str,
        required=True,
        dest=ARG_NAME_SERVERS,
        help="Name servers as JSON string (ex. [fqdn1, fqdn2, ...])",
    )
    dnssec_group = parser.add_argument_group(_GRP_DNSSEC_PARAMS)
    dnssec_group.add_argument(
        f"--{_NAME_PRIV_KEY_PATH}",
        type=str,
        dest=ARG_DNSSEC_PRIVATE_KEY_PATH,
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
        dest=ARG_DNSSEC_ALGORITHM,
        help=f"DNSSEC private key algorithm (default: {_VAL_DNSSEC_ALGORITHM})",
    )

    return parser


def _signal_handler(server: socketserver.UDPServer, signum: int, frame: Any):
    signal_name = signal.Signals(signum).name
    logging.info("Received %s signal, shutting down DNS server...", signal_name)

    threading.Thread(target=server.shutdown).start()


def _main(args: Dict[str, Any]):
    # Set up logging
    numeric_level = getattr(logging, args[_ARG_LOG_LEVEL].upper())
    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s - %(levelname)s - %(module)s.%(funcName)s - %(message)s",
    )

    # Copose config
    config = make_config(args)
    if not config:
        return

    # Start zone updater
    zone_updater = DnsServerZoneUpdaterThreated(
        args[_ARG_MIN_TEST_INTERVAL], args[_ARG_CONNECTION_TIMEOUT], config
    )
    zone_updater.start()

    # Launch DNS server
    server_address = ("", args[_ARG_PORT])
    with socketserver.UDPServer(server_address, DnsServerUdpHandler) as server:
        partial_signal_handler = partial(_signal_handler, server)
        for sig in (signal.SIGINT, signal.SIGTERM):
            signal.signal(sig, partial_signal_handler)

        logging.info("DNS server listening on port %d...", args[_ARG_PORT])
        server.zone = zone_updater.zone
        server.alias_zones = config.alias_zones
        server.serve_forever()

    # Stop zone updater
    zone_updater.stop()


def main():
    args = _make_arg_parser().parse_args()
    _main(vars(args))
