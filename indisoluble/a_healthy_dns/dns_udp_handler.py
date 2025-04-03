#!/usr/bin/env python3

import logging
import socketserver

import dns.message
import dns.rdatatype
import dns.rrset


class DNSUDPHandler(socketserver.BaseRequestHandler):
    def _response_for_a_record(self, response, qname):
        if qname not in self.server.resolutions:
            logging.warning("Received query for unknown domain: %s", qname)
            response.set_rcode(dns.rcode.NXDOMAIN)
            return

        ips = self.server.resolutions[qname]

        rrset = dns.rrset.from_text(
            qname, self.server.ttl_a, dns.rdataclass.IN, dns.rdatatype.A, *ips
        )
        response.answer.append(rrset)
        logging.debug("Responded to A query for %s with %s", qname, ips)

    def _response_for_ns_record(self, response, qname):
        if qname != self.server.hosted_zone:
            logging.warning("Received NS query for unknown zone: %s", qname)
            response.set_rcode(dns.rcode.NXDOMAIN)
            return

        rrset = dns.rrset.from_text(
            qname,
            self.server.ttl_ns,
            dns.rdataclass.IN,
            dns.rdatatype.NS,
            *self.server.name_servers,
        )
        response.answer.append(rrset)
        logging.debug(
            "Responded to NS query for %s with %s", qname, self.server.name_servers
        )

    def _response_for_soa_record(self, response, qname):
        if qname != self.server.hosted_zone:
            logging.warning("Received SOA query for unknown zone: %s", qname)
            response.set_rcode(dns.rcode.NXDOMAIN)
            return

        rrset = dns.rrset.from_text(
            qname,
            self.server.ttl_a,
            dns.rdataclass.IN,
            dns.rdatatype.SOA,
            " ".join(
                [
                    self.server.primary_name_server,
                    f"hostmaster.{self.server.hosted_zone}",
                    str(self.server.soa_serial),
                    str(self.server.soa_refresh),
                    str(self.server.soa_retry),
                    str(self.server.soa_expire),
                    str(self.server.ttl_a),
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
