#!/usr/bin/env python3

import socketserver
import logging

import dns.exception
import dns.flags
import dns.message
import dns.name
import dns.rcode
import dns.rdatatype
import dns.rrset
import dns.versioned


def _update_response(
    response: dns.message.Message,
    query_name: dns.name.Name,
    query_type: dns.rdatatype.RdataType,
    zone: dns.versioned.Zone,
):
    with zone.reader() as txn:
        node = None
        if not query_name.is_absolute():
            node = txn.get_node(query_name)
        elif query_name.is_subdomain(zone.origin):
            node = txn.get_node(query_name.relativize(zone.origin))

        if not node:
            logging.warning("Received query for unknown domain: %s", query_name)
            response.set_rcode(dns.rcode.NXDOMAIN)
            return

        rdataset = node.get_rdataset(zone.rdclass, query_type)
        if not rdataset:
            logging.warning(
                "Domain %s exists but has no %s records",
                query_name,
                dns.rdatatype.to_text(query_type),
            )
            response.set_rcode(dns.rcode.NXDOMAIN)
            return

        rrset = dns.rrset.RRset(query_name, rdataset.rdclass, rdataset.rdtype)
        rrset.ttl = rdataset.ttl
        for rdata in rdataset:
            rrset.add(rdata)

        response.answer.append(rrset)
        logging.debug("Answered query for %s with %s", query_name, rrset)


class DnsServerUdpHandler(socketserver.BaseRequestHandler):
    def handle(self):
        data, sock = self.request

        try:
            query = dns.message.from_wire(data)
        except dns.exception.DNSException as ex:
            logging.exception("Failed to parse DNS query: %s", ex)
            return

        response = dns.message.make_response(query)
        response.flags |= dns.flags.AA  # Authoritative Answer

        if query.question:
            question = query.question[0]
            _update_response(response, question.name, question.rdtype, self.server.zone)
        else:
            logging.warning("Received query without question section")
            response.set_rcode(dns.rcode.FORMERR)

        # Send the response back to the client
        sock.sendto(response.to_wire(), self.client_address)
