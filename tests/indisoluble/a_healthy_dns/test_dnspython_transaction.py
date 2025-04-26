#!/usr/bin/env python3

import dns.name
import dns.rdataclass
import dns.rdataset
import dns.rdatatype
import dns.transaction
import dns.versioned
import pytest


@pytest.fixture
def dns_origin():
    return dns.name.from_text("example.com.")


@pytest.fixture
def dns_versioned_zone(dns_origin):
    return dns.versioned.Zone(dns_origin, dns.rdataclass.IN)


def test_transaction_write_without_commit(dns_origin, dns_versioned_zone):
    subdomain = dns.name.from_text("test", origin=dns_origin)
    a_rec = dns.rdataset.from_text(
        dns.rdataclass.IN, dns.rdatatype.A, 60, "192.168.1.1"
    )

    with dns_versioned_zone.writer() as txn:
        assert txn.changed() is False
        txn.add(subdomain, a_rec)
        assert txn.changed() is True

        assert txn.get(subdomain, dns.rdatatype.A) is not None

    with dns_versioned_zone.reader() as txn:
        assert txn.get(subdomain, dns.rdatatype.A) is not None


def test_transaction_use_after_commit(dns_origin, dns_versioned_zone):
    subdomain = dns.name.from_text("www", origin=dns_origin)
    a_rec = dns.rdataset.from_text(
        dns.rdataclass.IN, dns.rdatatype.A, 60, "192.168.1.1"
    )

    with dns_versioned_zone.writer() as txn:
        assert txn.changed() is False
        txn.add(subdomain, a_rec)
        assert txn.changed() is True

        txn.commit()

        with pytest.raises(dns.transaction.AlreadyEnded):
            txn.changed()


def test_transaction_replace_identical_record(dns_origin, dns_versioned_zone):
    subdomain1_name = "www"
    ip1 = "192.168.1.1"
    ip2 = "192.168.1.2"
    ttl_a = 60

    subdomain1 = dns.name.from_text(subdomain1_name, origin=dns_origin)
    a_rec1 = dns.rdataset.from_text(dns.rdataclass.IN, dns.rdatatype.A, ttl_a, ip1)

    same_subdomain1 = dns.name.from_text(subdomain1_name, origin=dns_origin)
    same_a_rec1 = dns.rdataset.from_text(dns.rdataclass.IN, dns.rdatatype.A, ttl_a, ip1)

    subdomain2 = dns.name.from_text("api", origin=dns_origin)
    a_rec2 = dns.rdataset.from_text(dns.rdataclass.IN, dns.rdatatype.A, ttl_a, ip2)

    same_a_rec2 = dns.rdataset.from_text(dns.rdataclass.IN, dns.rdatatype.A, ttl_a, ip2)
    different_a_rec2 = dns.rdataset.from_text(
        dns.rdataclass.IN, dns.rdatatype.A, ttl_a, "192.168.1.3"
    )

    with dns_versioned_zone.writer() as txn:
        txn.add(subdomain1, a_rec1)
        txn.add(subdomain2, a_rec2)

    with dns_versioned_zone.writer() as txn:
        assert txn.changed() is False

        txn.replace(same_subdomain1, same_a_rec1)
        assert txn.changed() is True

        txn.replace(subdomain2, same_a_rec2)
        assert txn.changed() is True

        txn.replace(subdomain2, different_a_rec2)
        assert txn.changed() is True
