#!/usr/bin/env python3

import logging
import socketserver

import dns.message
import dns.rdatatype
import dns.rrset

from .dns_server_config import DNSServerConfig


class DNSUDPHandler(socketserver.BaseRequestHandler):
    def _response_for_a_record(self, response, qname):
        config: DNSServerConfig = self.server.config

        if qname not in config.resolutions:
            logging.warning("Received query for unknown domain: %s", qname)
            response.set_rcode(dns.rcode.NXDOMAIN)
            return

        ips = config.resolutions[qname]

        rrset = dns.rrset.from_text(
            qname, config.ttl_a, dns.rdataclass.IN, dns.rdatatype.A, *ips
        )
        response.answer.append(rrset)
        logging.debug("Responded to A query for %s with %s", qname, ips)

    def _response_for_ns_record(self, response, qname):
        config: DNSServerConfig = self.server.config

        if qname != config.hosted_zone:
            logging.warning("Received NS query for unknown zone: %s", qname)
            response.set_rcode(dns.rcode.NXDOMAIN)
            return

        rrset = dns.rrset.from_text(
            qname,
            config.ttl_ns,
            dns.rdataclass.IN,
            dns.rdatatype.NS,
            *config.name_servers,
        )
        response.answer.append(rrset)
        logging.debug(
            "Responded to NS query for %s with %s", qname, config.name_servers
        )

    def _response_for_soa_record(self, response, qname):
        config: DNSServerConfig = self.server.config

        if qname != config.hosted_zone:
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
                    config.primary_name_server,
                    f"hostmaster.{config.hosted_zone}",
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

            if question.rdtype == dns.rdatatype.A:
                self._response_for_a_record(response, question.name.to_text())
            elif question.rdtype == dns.rdatatype.NS:
                self._response_for_ns_record(response, question.name.to_text())
            elif question.rdtype == dns.rdatatype.SOA:
                self._response_for_soa_record(response, question.name.to_text())
            else:
                logging.warning("Received unsupported query type: %s", question.rdtype)
                response.set_rcode(dns.rcode.NOTIMP)

        sock.sendto(response.to_wire(), self.client_address)
