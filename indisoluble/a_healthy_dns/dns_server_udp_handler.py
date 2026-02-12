#!/usr/bin/env python3

"""UDP DNS server request handler.

Handles incoming DNS queries over UDP, processes them against the configured
zone, and returns appropriate DNS responses with authoritative answers.
"""

import logging
import socketserver

import dns.exception
import dns.flags
import dns.message
import dns.name
import dns.rcode
import dns.rdatatype
import dns.rrset
import dns.versioned

from typing import FrozenSet, Optional


def _normalize_query_name(
    query_name: dns.name.Name,
    zone_origin: dns.name.Name,
    alias_zones: FrozenSet[dns.name.Name],
) -> Optional[dns.name.Name]:
    """Normalize query name from alias zones to the primary zone.
    
    If the query is for an alias zone, convert it to the primary zone.
    Returns None if the query is not for the primary zone or any alias zones.
    """
    # Handle relative names - they are implicitly for the primary zone
    if not query_name.is_absolute():
        return query_name
    
    # Check if query is for the primary zone
    if query_name.is_subdomain(zone_origin):
        return query_name
    
    # Check if query is for any alias zone
    for alias_zone in alias_zones:
        if query_name.is_subdomain(alias_zone):
            # Extract the subdomain part and rebase it on the primary origin
            relative_name = query_name.relativize(alias_zone)
            if relative_name == dns.name.empty:
                # Query is for the alias zone apex
                return zone_origin
            return relative_name.derelativize(zone_origin)
    
    return None


def _update_response(
    response: dns.message.Message,
    query_name: dns.name.Name,
    query_type: dns.rdatatype.RdataType,
    zone: dns.versioned.Zone,
    alias_zones: FrozenSet[dns.name.Name],
):
    # Normalize the query name (handle alias zones)
    normalized_name = _normalize_query_name(query_name, zone.origin, alias_zones)
    if not normalized_name:
        logging.warning(
            "Received query for domain not in hosted or alias zones: %s", query_name
        )
        response.set_rcode(dns.rcode.NXDOMAIN)
        return

    with zone.reader() as txn:
        node = None
        if not normalized_name.is_absolute():
            node = txn.get_node(normalized_name)
        elif normalized_name.is_subdomain(zone.origin):
            node = txn.get_node(normalized_name.relativize(zone.origin))

        if not node:
            logging.warning("Received query for unknown domain: %s", query_name)
            response.set_rcode(dns.rcode.NXDOMAIN)
            return

        rdataset = node.get_rdataset(zone.rdclass, query_type)
        if not rdataset:
            logging.debug(
                "Domain %s exists but has no %s records",
                query_name,
                dns.rdatatype.to_text(query_type),
            )
            response.set_rcode(dns.rcode.NXDOMAIN)
            return

        # Use the original query name in the response, not the normalized one
        rrset = dns.rrset.RRset(query_name, rdataset.rdclass, rdataset.rdtype)
        rrset.ttl = rdataset.ttl
        for rdata in rdataset:
            rrset.add(rdata)

        response.answer.append(rrset)
        logging.debug("Answered query for %s with %s", query_name, rrset)


class DnsServerUdpHandler(socketserver.BaseRequestHandler):
    """UDP request handler for DNS queries with health-aware responses."""

    def handle(self):
        """Handle incoming DNS query and send appropriate response."""
        data, sock = self.request

        try:
            query = dns.message.from_wire(data)
        except dns.exception.DNSException as ex:
            logging.warning("Failed to parse DNS query: %s", ex)
            return

        response = dns.message.make_response(query)
        response.flags |= dns.flags.AA  # Authoritative Answer

        if query.question:
            question = query.question[0]
            config = getattr(self.server, "config", None)
            if config:
                alias_zones = config.alias_zones
            else:
                alias_zones = frozenset()
            _update_response(
                response, question.name, question.rdtype, self.server.zone, alias_zones
            )
        else:
            logging.warning("Received query without question section")
            response.set_rcode(dns.rcode.FORMERR)

        # Send the response back to the client
        sock.sendto(response.to_wire(), self.client_address)
