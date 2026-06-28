#!/usr/bin/env python3

import dns.message
import dns.rcode

from . import support as s


class TestQuestionCount:
    def test_standard_query_with_multiple_questions_returns_formerr(self, live_server):
        host, port = live_server
        wire = s.make_multi_question_wire(s.SUBDOMAIN_FQDN, s.ABSENT_FQDN)
        response = s.udp_raw_query(host, port, wire)

        assert response.rcode() == dns.rcode.FORMERR
        assert response.id == dns.message.from_wire(wire).id
        s.assert_section_counts(response)
        s.assert_response_flags(response, aa=False)
