#!/usr/bin/env python3

import logging
import socketserver

import dns.message
import dns.rdatatype
import dns.rrset


class DNSUDPHandler(socketserver.BaseRequestHandler):
    def handle(self):
        try:
            data, sock = self.request

            query = dns.message.from_wire(data)
            response = dns.message.make_response(query)

            question = query.question[0]
            qtype = question.rdtype
            qname = question.name.to_text()
            if qtype == dns.rdatatype.A and qname in self.server.config:
                ip = self.server.config[qname]
                rrset = dns.rrset.from_text(qname, 300, "IN", "A", ip)

                response.answer.append(rrset)

            sock.sendto(response.to_wire(), self.client_address)
        except Exception as e:
            logging.error("Error processing DNS query: %s", e)


def main():
    logging.basicConfig(level=logging.INFO)

    server_address = ("", 5053)
    config = {
        "example.com.": "1.2.3.4",
        "test.com.": "5.6.7.8",
    }
    with socketserver.UDPServer(server_address, DNSUDPHandler) as server:
        server.config = config

        logging.info(
            "DNS server listening on port %d", server_address[1]
        )
        server.serve_forever()
