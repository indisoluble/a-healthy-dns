#!/usr/bin/env python3

import logging

import dns.rdataclass
import dns.rdataset
import dns.rdatatype

from typing import Optional

from indisoluble.a_healthy_dns.records.a_healthy_record import AHealthyRecord
from indisoluble.a_healthy_dns.records.time import calculate_a_ttl


def make_a_record(
    max_interval: int, healthy_record: AHealthyRecord
) -> Optional[dns.rdataset.Rdataset]:
    ips = [ip.ip for ip in healthy_record.healthy_ips if ip.is_healthy]
    if not ips:
        logging.debug("No healthy IPs for A record %s", healthy_record.subdomain)
        return None

    ttl = calculate_a_ttl(max_interval)
    rdataset = dns.rdataset.from_text(dns.rdataclass.IN, dns.rdatatype.A, ttl, *ips)
    logging.debug("Created A record with ttl: %d, and IPs: %s", ttl, ips)

    return rdataset
