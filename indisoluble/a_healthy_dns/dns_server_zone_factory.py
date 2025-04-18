#!/usr/bin/env python3

import json
import logging
import time

import dns.name
import dns.rdataclass
import dns.rdataset
import dns.rdatatype
import dns.versioned

from typing import Any, Dict, Optional, NamedTuple

from .checkable_ips import CheckableIps
from .tools.is_valid_subdomain import is_valid_subdomain


class ExtendedARecords(NamedTuple):
    a_recs: Dict[dns.name.Name, dns.rdataset.Rdataset]
    resolutions: Dict[dns.name.Name, CheckableIps]
    ttl_a: int


class ExtendedNsRecord(NamedTuple):
    ns_rec: dns.rdataset.Rdataset
    primary_ns: str


class ExtendedZone(NamedTuple):
    zone: dns.versioned.Zone
    resolutions: Dict[dns.name.Name, CheckableIps]


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


def _make_origin_name(args: dict[str, Any]) -> Optional[dns.name.Name]:
    hosted_zone = args[HOSTED_ZONE_ARG]
    success, error = is_valid_subdomain(hosted_zone)
    if not success:
        logging.error(f"Hosted zone '{hosted_zone}' is not a valid FQDN: {error}")
        return None

    return dns.name.from_text(hosted_zone, origin=dns.name.root)


def _make_a_records(
    origin_name: dns.name.Name, args: dict[str, Any]
) -> Optional[ExtendedARecords]:
    ttl_a = int(args[TTL_A_ARG])
    if ttl_a <= 0:
        logging.error("TTL for A records must be positive")
        return None

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

    a_recs = {}
    resolutions = {}
    for subdomain, sub_config in raw_resolutions.items():
        success, error = is_valid_subdomain(subdomain)
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

        health_port = sub_config[SUBDOMAIN_HEALTH_PORT_ARG]
        if not isinstance(health_port, int):
            logging.error(
                "Health port for '%s' must be an integer, got %s",
                subdomain,
                type(health_port).__name__,
            )
            return None

        try:
            checkable_ips = CheckableIps(ip_list, health_port)
        except ValueError as ex:
            logging.exception("Invalid IP address in '%s': %s", subdomain, ex)
            return None

        a_recs[subdomain_name] = dns.rdataset.from_text(
            dns.rdataclass.IN, dns.rdatatype.A, ttl_a, *checkable_ips.ips
        )
        resolutions[subdomain_name] = checkable_ips

    return ExtendedARecords(a_recs, resolutions, ttl_a)


def _make_ns_record(args: dict[str, Any]) -> Optional[ExtendedNsRecord]:
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
        success, error = is_valid_subdomain(ns)
        if not success:
            logging.error(f"Name server '{ns}' is not a valid FQDN: {error}")
            return None

        abs_name_servers.append(f"{ns}.")

    ttl_ns = int(args[TTL_NS_ARG])
    if ttl_ns <= 0:
        logging.error("TTL for NS records must be positive")
        return None

    return ExtendedNsRecord(
        dns.rdataset.from_text(
            dns.rdataclass.IN, dns.rdatatype.NS, ttl_ns, *abs_name_servers
        ),
        abs_name_servers[0],
    )


def _make_soa_record(
    origin_name: dns.name.Name,
    primary_ns: str,
    soa_serial: int,
    ttl_a: int,
    args: dict[str, Any],
) -> Optional[dns.rdataset.Rdataset]:
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

    return dns.rdataset.from_text(
        dns.rdataclass.IN,
        dns.rdatatype.SOA,
        ttl_a,
        " ".join(
            [
                primary_ns,
                f"hostmaster.{origin_name}",
                str(soa_serial),
                str(soa_refresh),
                str(soa_retry),
                str(soa_expire),
                str(ttl_a),
            ]
        ),
    )


def make_zone(args: dict[str, Any]) -> Optional[ExtendedZone]:
    origin_name = _make_origin_name(args)
    if origin_name is None:
        return None

    ext_a_recs = _make_a_records(origin_name, args)
    if ext_a_recs is None:
        return None

    ext_ns_rec = _make_ns_record(args)
    if ext_ns_rec is None:
        return None

    soa_rec = _make_soa_record(
        origin_name, ext_ns_rec.primary_ns, int(time.time()), ext_a_recs.ttl_a, args
    )
    if soa_rec is None:
        return None

    zone = dns.versioned.Zone(origin_name)
    with zone.writer() as txn:
        txn.add(dns.name.empty, ext_ns_rec.ns_rec)
        txn.add(dns.name.empty, soa_rec)
        for subdomain_name, a_rec in ext_a_recs.a_recs.items():
            txn.add(subdomain_name, a_rec)

        txn.commit()

    logging.info(f"Successfully created versioned DNS zone for {origin_name}")
    return ExtendedZone(zone, ext_a_recs.resolutions)
