#!/usr/bin/env python3

import argparse
import logging
import socketserver

from . import dns_server_config_factory as dscf
from .dns_udp_handler import DNSUDPHandler
from .tcp_connectivity_tester import TcpConnectivityTester


_CONNECTION_TIMEOUT_ARG = "connection_timeout"
_LOG_LEVEL_ARG = "log_level"
_PORT_ARG = "port"
_TEST_INTERVAL_ARG = "test_interval"


def _make_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="DNS server")
    parser.add_argument(
        "-z",
        "--hosted-zone",
        type=str,
        required=True,
        dest=dscf.HOSTED_ZONE_ARG,
        help="Hosted zone name",
    )
    parser.add_argument(
        "-n",
        "--name-servers",
        type=str,
        required=True,
        dest=dscf.NAME_SERVERS_ARG,
        help="List of name servers as JSON string (ex. [fqdn1, fqdn2, ...])",
    )
    parser.add_argument(
        "-r",
        "--zone-resolutions",
        type=str,
        required=True,
        dest=dscf.ZONE_RESOLUTIONS_ARG,
        help=f"List of subdomains with their respective IPs and health ports as JSON string (ex. {{sd1: {{'{dscf.SUBDOMAIN_IP_LIST_ARG}': [ip1, ip2, ...], '{dscf.SUBDOMAIN_HEALTH_PORT_ARG}': port}}, ...}})",
    )
    parser.add_argument(
        "-p",
        "--port",
        type=int,
        default=5053,
        dest=_PORT_ARG,
        help="DNS server port (default: 5053)",
    )
    parser.add_argument(
        "-a",
        "--ttl-a",
        type=int,
        default=60,
        dest=dscf.TTL_A_ARG,
        help="TTL in seconds for A records (default: 60)",
    )
    parser.add_argument(
        "-s",
        "--ttl-ns",
        type=int,
        default=86400,
        dest=dscf.TTL_NS_ARG,
        help="TTL in seconds for NS records (default: 86400)",
    )
    parser.add_argument(
        "-f",
        "--soa-refresh",
        type=int,
        default=3600,
        dest=dscf.SOA_REFRESH_ARG,
        help="SOA refresh time in seconds (default: 3600)",
    )
    parser.add_argument(
        "-t",
        "--soa-retry",
        type=int,
        default=600,
        dest=dscf.SOA_RETRY_ARG,
        help="SOA retry time in seconds (default: 600)",
    )
    parser.add_argument(
        "-e",
        "--soa-expire",
        type=int,
        default=86400,
        dest=dscf.SOA_EXPIRE_ARG,
        help="SOA expire time in seconds (default: 86400)",
    )
    parser.add_argument(
        "-i",
        "--test-interval",
        type=int,
        default=30,
        dest=_TEST_INTERVAL_ARG,
        help="Interval in seconds for connectivity tests (default: 30)",
    )
    parser.add_argument(
        "-c",
        "--connection-timeout",
        type=int,
        default=2,
        dest=_CONNECTION_TIMEOUT_ARG,
        help="Timeout in seconds for connectivity tests (default: 2)",
    )
    parser.add_argument(
        "-l",
        "--log-level",
        type=str,
        default="info",
        dest=_LOG_LEVEL_ARG,
        help="Logging level (default: info)",
    )

    return parser


def main():
    args = _make_arg_parser().parse_args()
    args_dict = vars(args)

    # Set up logging
    try:
        numeric_level = getattr(logging, args_dict[_LOG_LEVEL_ARG].upper())
    except AttributeError:
        logging.error("Invalid log level: %s", args_dict[_LOG_LEVEL_ARG])
        return

    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s - %(levelname)s - %(module)s.%(funcName)s - %(message)s",
    )

    # Compose configuration
    config = dscf.make_config(args_dict)
    if config is None:
        logging.error("Invalid configuration")
        return

    # Start TCP connectivity tester
    try:
        connectivity_tester = TcpConnectivityTester(
            config, args_dict[_TEST_INTERVAL_ARG], args_dict[_CONNECTION_TIMEOUT_ARG]
        )
    except ValueError as e:
        logging.error("Error creating TCP connectivity tester: %s", e)
        return

    connectivity_tester.start()
    logging.info("TCP connectivity tester started")

    # Launch DNS server
    server_address = ("", args_dict[_PORT_ARG])
    with socketserver.UDPServer(server_address, DNSUDPHandler) as server:
        server.config = config

        logging.info("DNS server listening on port %d", args_dict[_PORT_ARG])
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            logging.info("Shutting down DNS server")
