#!/usr/bin/env python3

import json
import logging
import time

import dns.name
import dns.rdataclass
import dns.rdataset
import dns.rdatatype
import dns.versioned

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


def make_zone(args: dict[str, Any]) -> Optional[dns.versioned.Zone]:
    hosted_zone = args[HOSTED_ZONE_ARG]
    success, error = _is_valid_subdomain(hosted_zone)
    if not success:
        logging.error(f"Hosted zone '{hosted_zone}' is not a valid FQDN: {error}")
        return None

    origin_name = dns.name.from_text(hosted_zone, origin=dns.name.root)

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

    ttl_ns = int(args[TTL_NS_ARG])
    if ttl_ns <= 0:
        logging.error("TTL for NS records must be positive")
        return None

    ns_rec = dns.rdataset.from_text(
        dns.rdataclass.IN, dns.rdatatype.NS, ttl_ns, *abs_name_servers
    )

    ttl_a = int(args[TTL_A_ARG])
    if ttl_a <= 0:
        logging.error("TTL for A records must be positive")
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

    soa_rec = dns.rdataset.from_text(
        dns.rdataclass.IN,
        dns.rdatatype.SOA,
        ttl_a,
        " ".join(
            [
                abs_name_servers[0],
                f"hostmaster.{hosted_zone}.",
                str(soa_serial),
                str(soa_refresh),
                str(soa_retry),
                str(soa_expire),
                str(ttl_a),
            ]
        ),
    )

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

    resolutions = {}
    for subdomain, sub_config in raw_resolutions.items():
        success, error = _is_valid_subdomain(subdomain)
        if not success:
            logging.error(
                f"Zone resolution subdomain '{subdomain}' is not valid: {error}"
            )
            return None

        subdomain_name = dns.name.from_text(subdomain, origin=origin_name)

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

        a_rec = dns.rdataset.from_text(
            dns.rdataclass.IN, dns.rdatatype.A, ttl_a, *ip_list
        )

        resolutions[subdomain_name] = a_rec

    zone = dns.versioned.Zone(origin_name)
    with zone.writer() as txn:
        txn.add(dns.name.empty, soa_rec)
        txn.add(dns.name.empty, ns_rec)
        for subdomain_name, a_rec in resolutions.items():
            txn.add(subdomain_name, a_rec)

        txn.commit()

    logging.info(f"Successfully created versioned DNS zone for {hosted_zone}")
    return zone
