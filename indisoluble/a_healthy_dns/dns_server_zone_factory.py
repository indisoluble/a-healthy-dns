#!/usr/bin/env python3

import json
import logging

import dns.dnssec
import dns.dnssecalgs
import dns.name
import dns.rdataclass
import dns.rdataset
import dns.rdatatype
import dns.versioned

from typing import Any, Dict, List, NamedTuple, Optional, Set, Union

from .healthy_a_record import HealthyARecord
from .healthy_ip import HealthyIp
from .tools.is_valid_subdomain import is_valid_subdomain


class ExtendedNsRecord(NamedTuple):
    ns_rec: dns.rdataset.ImmutableRdataset
    primary_ns: str


class ExtendedPrivateKey(NamedTuple):
    private_key: dns.dnssec.PrivateKey
    dnskey: dns.dnssec.DNSKEY
    dnskey_ttl: int
    rrsig_lifetime: int


class ExtendedZone(NamedTuple):
    zone: dns.versioned.Zone
    ns_rec: dns.rdataset.ImmutableRdataset
    soa_rec: dns.rdataset.ImmutableRdataset
    a_recs: Set[HealthyARecord]
    ext_priv_key: Optional[ExtendedPrivateKey]


ARG_DNSSEC_ALGORITHM = "priv_key_alg"
ARG_DNSSEC_LIFETIME = "lifetime"
ARG_DNSSEC_PRIVATE_KEY_PEM = "priv_key_pem"
ARG_DNSSEC_TTL_DNSKEY = "dnskey_ttl"
ARG_HOSTED_ZONE = "zone"
ARG_NAME_SERVERS = "name_servers"
ARG_SOA_EXPIRE = "expire"
ARG_SOA_MIN_TTL = "min_ttl"
ARG_SOA_REFRESH = "refresh"
ARG_SOA_RETRY = "retry"
ARG_SUBDOMAIN_HEALTH_PORT = "health_port"
ARG_SUBDOMAIN_IP_LIST = "ips"
ARG_TTL_A = "a_ttl"
ARG_TTL_NS = "ns_ttl"
ARG_TTL_SOA = "soa_ttl"
ARG_ZONE_RESOLUTIONS = "resolutions"


def _make_origin_name(args: Dict[str, Any]) -> Optional[dns.name.Name]:
    hosted_zone = args[ARG_HOSTED_ZONE]
    success, error = is_valid_subdomain(hosted_zone)
    if not success:
        logging.error("Hosted zone '%s' is not a valid FQDN: %s", hosted_zone, error)
        return None

    return dns.name.from_text(hosted_zone, origin=dns.name.root)


def _make_healthy_a_record(
    origin_name: dns.name.Name,
    ttl_a: int,
    subdomain: str,
    sub_config: Dict[str, Union[List[str], int]],
) -> Optional[HealthyARecord]:
    success, error = is_valid_subdomain(subdomain)
    if not success:
        logging.error(
            "Zone resolution subdomain '%s' is not valid: %s", subdomain, error
        )
        return None

    subdomain_name = dns.name.from_text(subdomain, origin=origin_name)

    if not isinstance(sub_config, dict):
        logging.error(
            "Zone resolution for '%s' must be a dictionary, got %s",
            subdomain,
            type(sub_config).__name__,
        )
        return None

    ip_list = sub_config[ARG_SUBDOMAIN_IP_LIST]
    if not isinstance(ip_list, list):
        logging.error(
            "IP list for '%s' must be a list, got %s", subdomain, type(ip_list).__name__
        )
        return None

    if not ip_list:
        logging.error("IP list for '%s' cannot be empty", subdomain)
        return None

    health_port = sub_config[ARG_SUBDOMAIN_HEALTH_PORT]
    if not isinstance(health_port, int):
        logging.error(
            "Health port for '%s' must be an integer, got %s",
            subdomain,
            type(health_port).__name__,
        )
        return None

    try:
        healthy_ips = {HealthyIp(ip, health_port, False) for ip in ip_list}
    except ValueError as ex:
        logging.error("Invalid IP address in '%s': %s", subdomain, ex)
        return None

    try:
        return HealthyARecord(subdomain_name, ttl_a, healthy_ips)
    except ValueError as ex:
        logging.error("Invalid A record for '%s': %s", subdomain, ex)
        return None


def _make_a_records(
    origin_name: dns.name.Name, args: Dict[str, Any]
) -> Optional[Set[HealthyARecord]]:
    try:
        raw_resolutions = json.loads(args[ARG_ZONE_RESOLUTIONS])
    except json.JSONDecodeError as ex:
        logging.error("Failed to parse zone resolutions: %s", ex)
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

    ttl_a = args[ARG_TTL_A]

    a_records = set()
    for subdomain, sub_config in raw_resolutions.items():
        a_record = _make_healthy_a_record(origin_name, ttl_a, subdomain, sub_config)
        if not a_record:
            logging.error("Failed to create A record for '%s'", subdomain)
            return None

        a_records.add(a_record)

    return a_records


def _make_ns_record(args: Dict[str, Any]) -> Optional[ExtendedNsRecord]:
    try:
        name_servers = json.loads(args[ARG_NAME_SERVERS])
    except json.JSONDecodeError as ex:
        logging.error("Failed to parse name servers: %s", ex)
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
            logging.error("Name server '%s' is not a valid FQDN: %s", ns, error)
            return None

        abs_name_servers.append(f"{ns}.")

    ttl_ns = args[ARG_TTL_NS]
    if ttl_ns <= 0:
        logging.error("TTL for NS records must be positive")
        return None

    return ExtendedNsRecord(
        dns.rdataset.ImmutableRdataset(
            dns.rdataset.from_text(
                dns.rdataclass.IN, dns.rdatatype.NS, ttl_ns, *abs_name_servers
            )
        ),
        abs_name_servers[0],
    )


def _make_soa_record(
    origin_name: dns.name.Name, primary_ns: str, args: Dict[str, Any]
) -> Optional[dns.rdataset.ImmutableRdataset]:
    ttl_soa = args[ARG_TTL_SOA]
    if ttl_soa <= 0:
        logging.error("TTL for SOA records must be positive")
        return None

    soa_refresh = args[ARG_SOA_REFRESH]
    if soa_refresh <= 0:
        logging.error("SOA refresh value must be positive")
        return None

    soa_retry = args[ARG_SOA_RETRY]
    if soa_retry <= 0:
        logging.error("SOA retry value must be positive")
        return None

    soa_expire = args[ARG_SOA_EXPIRE]
    if soa_expire <= 0:
        logging.error("SOA expire value must be positive")
        return None

    soa_min_ttl = args[ARG_SOA_MIN_TTL]
    if soa_min_ttl <= 0:
        logging.error("SOA minimum TTL value must be positive")
        return None

    soa_serial = 0

    return dns.rdataset.ImmutableRdataset(
        dns.rdataset.from_text(
            dns.rdataclass.IN,
            dns.rdatatype.SOA,
            ttl_soa,
            " ".join(
                [
                    primary_ns,
                    f"hostmaster.{origin_name}",
                    str(soa_serial),
                    str(soa_refresh),
                    str(soa_retry),
                    str(soa_expire),
                    str(soa_min_ttl),
                ]
            ),
        )
    )


def _make_private_key(args: Dict[str, Any]) -> Optional[ExtendedPrivateKey]:
    dnskey_ttl = args[ARG_DNSSEC_TTL_DNSKEY]
    if dnskey_ttl <= 0:
        logging.error("TTL for DNSKEY records must be positive")
        return None

    lifetime = args[ARG_DNSSEC_LIFETIME]
    if lifetime <= 0:
        logging.error("DNSSEC lifetime must be positive")
        return None

    try:
        alg = dns.dnssec.algorithm_from_text(args[ARG_DNSSEC_ALGORITHM])
        priv_key_pem = args[ARG_DNSSEC_PRIVATE_KEY_PEM]

        priv_key = dns.dnssecalgs.get_algorithm_cls(alg).from_pem(priv_key_pem)

        dnskey = dns.dnssec.make_dnskey(priv_key.public_key(), alg)
    except Exception as ex:
        logging.error("Failed to load private key: %s", ex)
        return None

    return ExtendedPrivateKey(priv_key, dnskey, dnskey_ttl, lifetime)


def make_zone(args: Dict[str, Any]) -> Optional[ExtendedZone]:
    origin_name = _make_origin_name(args)
    if not origin_name:
        return None

    a_records = _make_a_records(origin_name, args)
    if not a_records:
        return None

    ext_ns_rec = _make_ns_record(args)
    if not ext_ns_rec:
        return None

    soa_rec = _make_soa_record(origin_name, ext_ns_rec.primary_ns, args)
    if not soa_rec:
        return None

    ext_private_key = None
    if args[ARG_DNSSEC_PRIVATE_KEY_PEM]:
        ext_private_key = _make_private_key(args)
        if not ext_private_key:
            return None

    zone = dns.versioned.Zone(origin_name)

    return ExtendedZone(zone, ext_ns_rec.ns_rec, soa_rec, a_records, ext_private_key)
