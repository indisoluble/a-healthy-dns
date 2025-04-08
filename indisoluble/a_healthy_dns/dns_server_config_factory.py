#!/usr/bin/env python3

import json
import logging
import time

from typing import Any, Optional

from .dns_server_config import DNSServerConfig


HOSTED_ZONE_ARG = "hosted_zone"
NAME_SERVERS_ARG = "name_servers"
ZONE_RESOLUTIONS_ARG = "zone_resolutions"
TTL_A_ARG = "ttl_a"
TTL_NS_ARG = "ttl_ns"
SOA_REFRESH_ARG = "soa_refresh"
SOA_RETRY_ARG = "soa_retry"
SOA_EXPIRE_ARG = "soa_expire"


def make_config(args: dict[str, Any]) -> Optional[DNSServerConfig]:
    try:
        name_servers = json.loads(args[NAME_SERVERS_ARG])
    except json.JSONDecodeError as ex:
        logging.exception("Failed to parse name servers: %s", ex)
        return

    try:
        resolutions = json.loads(args[ZONE_RESOLUTIONS_ARG])
    except json.JSONDecodeError as ex:
        logging.exception("Failed to parse zone resolutions: %s", ex)
        return

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
