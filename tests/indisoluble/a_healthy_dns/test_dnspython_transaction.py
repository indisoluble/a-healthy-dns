#!/usr/bin/env python3

import dns.name
import dns.rdataclass
import dns.rdataset
import dns.rdatatype
import dns.transaction
import dns.versioned
import pytest

_ORIGIN = dns.name.from_text("example.com.")
_TTL = 60


def _absolute_name(label):
    return dns.name.from_text(label, origin=_ORIGIN)


def _a_rdataset(ip):
    return dns.rdataset.from_text(dns.rdataclass.IN, dns.rdatatype.A, _TTL, ip)


@pytest.fixture
def dns_versioned_zone():
    return dns.versioned.Zone(_ORIGIN, dns.rdataclass.IN)


class TestDnspythonVersionedZoneTransactions:
    def test_writer_context_commits_changes_on_exit(self, dns_versioned_zone):
        subdomain = _absolute_name("test")
        a_rdataset = _a_rdataset("192.168.1.1")

        with dns_versioned_zone.writer() as txn:
            assert txn.changed() is False

            txn.add(subdomain, a_rdataset)

            assert txn.changed() is True
            assert txn.get(subdomain, dns.rdatatype.A) is not None

        with dns_versioned_zone.reader() as txn:
            assert txn.get(subdomain, dns.rdatatype.A) is not None

    def test_transaction_cannot_be_used_after_explicit_commit(self, dns_versioned_zone):
        subdomain = _absolute_name("www")
        a_rdataset = _a_rdataset("192.168.1.1")

        with dns_versioned_zone.writer() as txn:
            assert txn.changed() is False
            txn.add(subdomain, a_rdataset)
            assert txn.changed() is True

            txn.commit()

            with pytest.raises(dns.transaction.AlreadyEnded):
                txn.changed()

    def test_replace_marks_transaction_changed_even_for_identical_rdataset(
        self, dns_versioned_zone
    ):
        www_name = _absolute_name("www")
        api_name = _absolute_name("api")
        www_rdataset = _a_rdataset("192.168.1.1")
        api_rdataset = _a_rdataset("192.168.1.2")
        changed_api_rdataset = _a_rdataset("192.168.1.3")

        with dns_versioned_zone.writer() as txn:
            txn.add(www_name, www_rdataset)
            txn.add(api_name, api_rdataset)

        with dns_versioned_zone.writer() as txn:
            assert txn.changed() is False

            txn.replace(www_name, _a_rdataset("192.168.1.1"))
            assert txn.changed() is True

            txn.replace(api_name, _a_rdataset("192.168.1.2"))
            assert txn.changed() is True

            txn.replace(api_name, changed_api_rdataset)
            assert txn.changed() is True
