#!/usr/bin/env python3

import json
import logging
import time

from typing import Any, Optional

from .checkable_ip import CheckableIp
from .dns_server_config import DNSServerConfig


HOSTED_ZONE_ARG = "hosted_zone"
NAME_SERVERS_ARG = "name_servers"
ZONE_RESOLUTIONS_ARG = "zone_resolutions"
TTL_A_ARG = "ttl_a"
TTL_NS_ARG = "ttl_ns"
SOA_REFRESH_ARG = "soa_refresh"
SOA_RETRY_ARG = "soa_retry"
SOA_EXPIRE_ARG = "soa_expire"
SUBDOMAIN_HEALTH_PORT_ARG = "health_port"
SUBDOMAIN_IP_LIST_ARG = "ips"


def make_config(args: dict[str, Any]) -> Optional[DNSServerConfig]:
    try:
        name_servers = json.loads(args[NAME_SERVERS_ARG])
    except json.JSONDecodeError as ex:
        logging.exception("Failed to parse name servers: %s", ex)
        return

    if not isinstance(name_servers, list):
        logging.error(
            "Name servers must be a list, got %s", type(name_servers).__name__
        )
        return

    try:
        raw_resolutions = json.loads(args[ZONE_RESOLUTIONS_ARG])
    except json.JSONDecodeError as ex:
        logging.exception("Failed to parse zone resolutions: %s", ex)
        return

    if not isinstance(raw_resolutions, dict):
        logging.error(
            "Zone resolutions must be a dictionary, got %s",
            type(raw_resolutions).__name__,
        )
        return

    resolutions = {}
    for subdomain, sub_config in raw_resolutions.items():
        if not isinstance(sub_config, dict):
            logging.error(
                "Zone resolution for '%s' must be a dictionary, got %s",
                subdomain,
                type(sub_config).__name__,
            )
            return

        health_port = sub_config[SUBDOMAIN_HEALTH_PORT_ARG]
        ip_list = sub_config[SUBDOMAIN_IP_LIST_ARG]
        if not isinstance(ip_list, list):
            logging.error(
                "IP list for '%s' must be a list, got %s",
                subdomain,
                type(ip_list).__name__,
            )
            return

        try:
            checkable_ips = [CheckableIp(ip, health_port) for ip in ip_list]
        except ValueError as ex:
            logging.exception("Invalid IP address in '%s': %s", subdomain, ex)
            return

        resolutions[subdomain] = checkable_ips

    try:
        config = DNSServerConfig(
            hosted_zone=args[HOSTED_ZONE_ARG],
            name_servers=name_servers,
            resolutions=resolutions,
            ttl_a=args[TTL_A_ARG],
            ttl_ns=args[TTL_NS_ARG],
            soa_serial=int(time.time()),
            soa_refresh=args[SOA_REFRESH_ARG],
            soa_retry=args[SOA_RETRY_ARG],
            soa_expire=args[SOA_EXPIRE_ARG],
        )
    except ValueError as ex:
        logging.exception("Failed to create DNS server config: %s", ex)
        return

    return config
