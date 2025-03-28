#!/usr/bin/env python3

import argparse
import json
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

    parser = argparse.ArgumentParser(description="DNS server")
    parser.add_argument(
        "--config", type=str, required=True, help="JSON string for config."
    )
    args = parser.parse_args()
    config = json.loads(args.config)

    server_address = ("", 5053)
    with socketserver.UDPServer(server_address, DNSUDPHandler) as server:
        server.config = config

        logging.info("DNS server listening on port %d", server_address[1])
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            logging.info("Shutting down DNS server")
