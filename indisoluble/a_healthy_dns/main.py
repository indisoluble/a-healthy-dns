#!/usr/bin/env python3

import argparse
import json
import logging
import socketserver
import time

from .dns_udp_handler import DNSUDPHandler


_HOSTED_ZONE_ARG = "hosted_zone"
_NAME_SERVERS_ARG = "name_servers"
_ZONE_RESOLUTIONS_ARG = "zone_resolutions"
_PORT_ARG = "port"
_TTL_A_ARG = "ttl_a"
_TTL_NS_ARG = "ttl_ns"
_SOA_REFRESH_ARG = "soa_refresh"
_SOA_RETRY_ARG = "soa_retry"
_SOA_EXPIRE_ARG = "soa_expire"
_LOG_LEVEL_ARG = "log_level"


def _make_arg_parser():
    parser = argparse.ArgumentParser(description="DNS server")
    parser.add_argument(
        "-z",
        "--hosted-zone",
        type=str,
        required=True,
        dest=_HOSTED_ZONE_ARG,
        help="Hosted zone name"
    )
    parser.add_argument(
        "-n",
        "--name-servers",
        type=str,
        required=True,
        dest=_NAME_SERVERS_ARG,
        help="List of name servers as JSON string (ex. [fqdn1, fqdn2, ...])"
    )
    parser.add_argument(
        "-r",
        "--zone-resolutions",
        type=str,
        required=True,
        dest=_ZONE_RESOLUTIONS_ARG,
        help="List of subdomains with their respective IPs as JSON string (ex. {sd1: [ip1, ip2, ...], ...})"
    )
    parser.add_argument(
        "-p",
        "--port",
        type=int,
        default=5053,
        dest=_PORT_ARG,
        help="DNS server port (default: 5053)"
    )
    parser.add_argument(
        "-a",
        "--ttl-a",
        type=int,
        default=60,
        dest=_TTL_A_ARG,
        help="TTL in seconds for A records (default: 60)"
    )
    parser.add_argument(
        "-s",
        "--ttl-ns",
        type=int,
        default=86400,
        dest=_TTL_NS_ARG,
        help="TTL in seconds for NS records (default: 86400)"
    )
    parser.add_argument(
        "-f",
        "--soa-refresh",
        type=int,
        default=3600,
        dest=_SOA_REFRESH_ARG,
        help="SOA refresh time in seconds (default: 3600)"
    )
    parser.add_argument(
        "-t",
        "--soa-retry",
        type=int,
        default=600,
        dest=_SOA_RETRY_ARG,
        help="SOA retry time in seconds (default: 600)"
    )
    parser.add_argument(
        "-e",
        "--soa-expire",
        type=int,
        default=86400,
        dest=_SOA_EXPIRE_ARG,
        help="SOA expire time in seconds (default: 86400)"
    )
    parser.add_argument(
        "-l",
        "--log-level",
        type=str,
        default="info",
        dest=_LOG_LEVEL_ARG,
        help="Logging level (default: info)"
    )

    return parser


def main():
    args = _make_arg_parser().parse_args()
    args_dict = vars(args)  # transform args object into a dictionary

    # Set up logging
    numeric_level = getattr(logging, args_dict[_LOG_LEVEL_ARG].upper(), logging.INFO)
    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s - %(levelname)s - %(module)s.%(funcName)s - %(message)s",
    )

    # Parse name servers
    try:
        raw_name_servers = json.loads(args_dict[_NAME_SERVERS_ARG])
    except json.JSONDecodeError as ex:
        logging.exception("Failed to parse name servers: %s", ex)
        return

    name_servers = [f"{ns}." for ns in raw_name_servers]

    # Parse resolutions
    try:
        raw_resolutions = json.loads(args_dict[_ZONE_RESOLUTIONS_ARG])
    except json.JSONDecodeError as ex:
        logging.exception("Failed to parse zone resolutions: %s", ex)
        return

    resolutions = {
        f"{subdomain}.{args_dict[_HOSTED_ZONE_ARG]}.": ips
        for subdomain, ips in raw_resolutions.items()
    }

    # Launch DNS server
    server_address = ("", args_dict[_PORT_ARG])
    with socketserver.UDPServer(server_address, DNSUDPHandler) as server:
        server.hosted_zone = f"{args_dict[_HOSTED_ZONE_ARG]}."
        server.primary_name_server = name_servers[0]
        server.name_servers = name_servers
        server.resolutions = resolutions
        server.ttl_a = args_dict[_TTL_A_ARG]
        server.ttl_ns = args_dict[_TTL_NS_ARG]
        server.soa_serial = int(time.time())
        server.soa_refresh = args_dict[_SOA_REFRESH_ARG]
        server.soa_retry = args_dict[_SOA_RETRY_ARG]
        server.soa_expire = args_dict[_SOA_EXPIRE_ARG]

        logging.info("DNS server listening on port %d", args_dict[_PORT_ARG])
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            logging.info("Shutting down DNS server")


if __name__ == '__main__':
    main()