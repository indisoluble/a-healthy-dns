#!/usr/bin/env python3

import logging
import socketserver

import dns.message
import dns.rdatatype
import dns.rrset

from .dns_server_config import DNSServerConfig


def _handle_a_record(
    response: dns.message.Message, qname: str, config: DNSServerConfig
):
    if qname not in config.abs_resolutions:
        logging.warning("Received query for unknown domain: %s", qname)
        response.set_rcode(dns.rcode.NXDOMAIN)
        return

    ips = config.abs_resolutions[qname]

    rrset = dns.rrset.from_text(
        qname, config.ttl_a, dns.rdataclass.IN, dns.rdatatype.A, *ips
    )
    response.answer.append(rrset)
    logging.debug("Responded to A query for %s with %s", qname, ips)


def _handle_ns_record(
    response: dns.message.Message, qname: str, config: DNSServerConfig
):
    if qname != config.abs_hosted_zone:
        logging.warning("Received NS query for unknown zone: %s", qname)
        response.set_rcode(dns.rcode.NXDOMAIN)
        return

    rrset = dns.rrset.from_text(
        qname,
        config.ttl_ns,
        dns.rdataclass.IN,
        dns.rdatatype.NS,
        *config.abs_name_servers,
    )
    response.answer.append(rrset)
    logging.debug(
        "Responded to NS query for %s with %s", qname, config.abs_name_servers
    )


def _handle_soa_record(
    response: dns.message.Message, qname: str, config: DNSServerConfig
):
    if qname != config.abs_hosted_zone:
        logging.warning("Received SOA query for unknown zone: %s", qname)
        response.set_rcode(dns.rcode.NXDOMAIN)
        return

    rrset = dns.rrset.from_text(
        qname,
        config.ttl_a,
        dns.rdataclass.IN,
        dns.rdatatype.SOA,
        " ".join(
            [
                config.primary_abs_name_server,
                f"hostmaster.{config.abs_hosted_zone}",
                str(config.soa_serial),
                str(config.soa_refresh),
                str(config.soa_retry),
                str(config.soa_expire),
                str(config.ttl_a),
            ]
        ),
    )
    response.answer.append(rrset)
    logging.debug("Responded to SOA query for %s", qname)


_HANDLERS = {
    dns.rdatatype.A: _handle_a_record,
    dns.rdatatype.NS: _handle_ns_record,
    dns.rdatatype.SOA: _handle_soa_record,
}


class DNSUDPHandler(socketserver.BaseRequestHandler):
    def handle(self):
        data, sock = self.request

        try:
            query = dns.message.from_wire(data)
        except dns.exception.DNSException as ex:
            logging.exception("Failed to parse DNS query: %s", ex)
            return

        response = dns.message.make_response(query)
        response.flags |= dns.flags.AA  # Authoritative Answer

        if not query.question:
            logging.warning("Received query without question section")
            response.set_rcode(dns.rcode.FORMERR)
        else:
            question = query.question[0]

            if question.rdtype in _HANDLERS:
                _HANDLERS[question.rdtype](
                    response, question.name.to_text(), self.server.config
                )
            else:
                logging.warning("Received unsupported query type: %s", question.rdtype)
                response.set_rcode(dns.rcode.NOTIMP)

        sock.sendto(response.to_wire(), self.client_address)
