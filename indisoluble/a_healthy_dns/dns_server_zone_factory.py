#!/usr/bin/env python3

import json
import logging
import time

import dns.name
import dns.rdataclass
import dns.rdataset
import dns.rdatatype
import dns.zone

from typing import Any, Optional, Tuple

HOSTED_ZONE_ARG = "hosted_zone"
NAME_SERVERS_ARG = "name_servers"
ZONE_RESOLUTIONS_ARG = "zone_resolutions"
TTL_A_ARG = "ttl_a"
TTL_NS_ARG = "ttl_ns"
SOA_REFRESH_ARG = "soa_refresh"
SOA_RETRY_ARG = "soa_retry"
SOA_EXPIRE_ARG = "soa_expire"
SUBDOMAIN_IP_LIST_ARG = "ips"


def _is_valid_subdomain(name: str) -> Tuple[bool, str]:
    if not name:
        return (False, "It cannot be empty")

    if not all(
        label and all(c.isalnum() or c == "-" for c in label)
        for label in name.split(".")
    ):
        return (False, "Labels must contain only alphanumeric characters or hyphens")

    return (True, "")


def _is_valid_ip(ip: str) -> Tuple[bool, str]:
    parts = ip.split(".")
    if len(parts) != 4:
        return (False, "IP address must have 4 octets")

    if not all(part.isdigit() and (0 <= int(part) <= 255) for part in parts):
        return (False, "Each octet must be a number between 0 and 255")

    return (True, "")


def make_zone(args: dict[str, Any]) -> Optional[dns.zone.Zone]:
    hosted_zone = args[HOSTED_ZONE_ARG]
    success, error = _is_valid_subdomain(hosted_zone)
    if not success:
        logging.error(f"Hosted zone '{hosted_zone}' is not a valid FQDN: {error}")
        return None

    abs_hosted_zone = f"{hosted_zone}."

    try:
        name_servers = json.loads(args[NAME_SERVERS_ARG])
    except json.JSONDecodeError as ex:
        logging.exception("Failed to parse name servers: %s", ex)
        return None

    if not isinstance(name_servers, list):
        logging.error(
            "Name servers must be a list, got %s", type(name_servers).__name__
        )
        return None

    if not name_servers:
        logging.error("Name server list cannot be empty")
        return None

    abs_name_servers = []
    for ns in name_servers:
        success, error = _is_valid_subdomain(ns)
        if not success:
            logging.error(f"Name server '{ns}' is not a valid FQDN: {error}")
            return None

        abs_name_servers.append(f"{ns}.")

    primary_abs_name_server = abs_name_servers[0]

    ttl_a = int(args[TTL_A_ARG])
    if ttl_a <= 0:
        logging.error("TTL for A records must be positive")
        return None

    ttl_ns = int(args[TTL_NS_ARG])
    if ttl_ns <= 0:
        logging.error("TTL for NS records must be positive")
        return None

    soa_refresh = int(args[SOA_REFRESH_ARG])
    if soa_refresh <= 0:
        logging.error("SOA refresh value must be positive")
        return None

    soa_retry = int(args[SOA_RETRY_ARG])
    if soa_retry <= 0:
        logging.error("SOA retry value must be positive")
        return None

    soa_expire = int(args[SOA_EXPIRE_ARG])
    if soa_expire <= 0:
        logging.error("SOA expire value must be positive")
        return None

    soa_serial = int(time.time())

    try:
        raw_resolutions = json.loads(args[ZONE_RESOLUTIONS_ARG])
    except json.JSONDecodeError as ex:
        logging.exception("Failed to parse zone resolutions: %s", ex)
        return None

    if not isinstance(raw_resolutions, dict):
        logging.error(
            "Zone resolutions must be a dictionary, got %s",
            type(raw_resolutions).__name__,
        )
        return None

    if not raw_resolutions:
        logging.error("Zone resolutions cannot be empty")
        return None

    abs_resolutions = {}
    for subdomain, sub_config in raw_resolutions.items():
        success, error = _is_valid_subdomain(subdomain)
        if not success:
            logging.error(
                f"Zone resolution subdomain '{subdomain}' is not valid: {error}"
            )
            return None

        if not isinstance(sub_config, dict):
            logging.error(
                f"Zone resolution for '{subdomain}' must be a dictionary, got {type(sub_config).__name__}"
            )
            return None

        ip_list = sub_config[SUBDOMAIN_IP_LIST_ARG]
        if not isinstance(ip_list, list):
            logging.error(
                "IP list for '%s' must be a list, got %s",
                subdomain,
                type(ip_list).__name__,
            )
            return None

        if not ip_list:
            logging.error(f"IP list for '{subdomain}' cannot be empty")
            return None

        for ip in ip_list:
            success, error = _is_valid_ip(ip)
            if not success:
                logging.error(f"Invalid IP address '{ip}' in '{subdomain}': {error}")
                return None

        abs_resolutions[f"{subdomain}.{abs_hosted_zone}"] = ip_list

    try:
        origin_name = dns.name.from_text(abs_hosted_zone)
        zone = dns.zone.Zone(origin_name)

        origin_node = zone.get_node(origin_name, create=True)

        soa_rec = dns.rdataset.from_text(
            dns.rdataclass.IN,
            dns.rdatatype.SOA,
            ttl_a,
            " ".join(
                [
                    primary_abs_name_server,
                    f"hostmaster.{abs_hosted_zone}",
                    str(soa_serial),
                    str(soa_refresh),
                    str(soa_retry),
                    str(soa_expire),
                    str(ttl_a),
                ]
            ),
        )
        origin_node.rdatasets.append(soa_rec)

        ns_rec = dns.rdataset.from_text(
            dns.rdataclass.IN, dns.rdatatype.NS, ttl_ns, *abs_name_servers
        )
        origin_node.rdatasets.append(ns_rec)

        for subdomain, ips in abs_resolutions.items():
            subdomain_name = dns.name.from_text(subdomain)
            subdomain_node = zone.get_node(subdomain_name, create=True)

            a_rec = dns.rdataset.from_text(
                dns.rdataclass.IN, dns.rdatatype.A, ttl_a, *ips
            )
            subdomain_node.replace_rdataset(a_rec)

        logging.info(f"Successfully created DNS zone for {abs_hosted_zone}")
        return zone

    except Exception as ex:
        logging.exception(f"Failed to create DNS zone: {ex}")
        return None
