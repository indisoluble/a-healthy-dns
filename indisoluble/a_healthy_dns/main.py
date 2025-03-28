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
                logging.debug("Responded to query for %s with %s", qname, ip)

            sock.sendto(response.to_wire(), self.client_address)
        except Exception as e:
            logging.error("Error processing DNS query: %s", e)


def main():
    # Set up argument parsing
    parser = argparse.ArgumentParser(description="DNS server")
    parser.add_argument(
        "--config", type=str, required=True, help="JSON string for config."
    )
    parser.add_argument(
        "--log-level", type=str, default="info", help="Logging level (default: info)"
    )
    args = parser.parse_args()

    # Set up logging
    numeric_level = getattr(logging, args.log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s - %(levelname)s - %(module)s.%(funcName)s - %(message)s",
    )

    # Load the configuration
    config = json.loads(args.config)

    # Launch the DNS server
    server_address = ("", 5053)
    with socketserver.UDPServer(server_address, DNSUDPHandler) as server:
        server.config = config

        logging.info("DNS server listening on port %d", server_address[1])
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            logging.info("Shutting down DNS server")
