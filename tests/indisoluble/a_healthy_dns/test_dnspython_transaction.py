#!/usr/bin/env python3

import dns.dnssec
import dns.name
import dns.rdataclass
import dns.rdataset
import dns.rdatatype
import dns.transaction
import dns.versioned
import dns.zone
import pytest

from dns.dnssecalgs.rsa import PrivateRSASHA256


@pytest.fixture
def dns_origin():
    return dns.name.from_text("example.com.")


@pytest.fixture
def dns_versioned_zone(dns_origin):
    return dns.versioned.Zone(dns_origin, dns.rdataclass.IN)


@pytest.fixture
def dns_soa_record():
    ttl = 3600
    admin_info = (
        "ns1.example.com. hostmaster.example.com 20250701 7200 3600 1209600 3600"
    )
    return dns.rdataset.from_text(dns.rdataclass.IN, dns.rdatatype.SOA, ttl, admin_info)


@pytest.fixture
def dns_key():
    priv_key = PrivateRSASHA256.generate(key_size=2048)
    dnskey = dns.dnssec.make_dnskey(priv_key.public_key(), dns.dnssec.RSASHA256)

    return (priv_key, dnskey)


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


def test_transaction_sign_zone_bug(dns_versioned_zone, dns_soa_record, dns_key):
    with dns_versioned_zone.writer() as txn:
        txn.add(dns.name.empty, dns_soa_record)

        with pytest.raises(dns.zone.NoSOA) as exc_info:
            dns.dnssec.sign_zone(
                dns_versioned_zone,
                txn=txn,
                keys=[dns_key],
                dnskey_ttl=3600,
                inception=0,
                expiration=3600,
            )

    with dns_versioned_zone.writer() as txn:
        # Does not fail after previous transaction is completed
        dns.dnssec.sign_zone(
            dns_versioned_zone,
            txn=txn,
            keys=[dns_key],
            dnskey_ttl=3600,
            inception=0,
            expiration=3600,
        )
