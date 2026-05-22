#!/usr/bin/env python3

import dns.name
import pytest

from indisoluble.a_healthy_dns.records.a_healthy_ip import AHealthyIp
from indisoluble.a_healthy_dns.records.a_healthy_record import AHealthyRecord

_SUBDOMAIN = dns.name.from_text("test.example.com")
_OTHER_SUBDOMAIN = dns.name.from_text("other.example.com")


def _make_ip(ip="192.168.1.1", health_port=80, is_healthy=True):
    return AHealthyIp(ip, health_port, is_healthy)


def _make_record(subdomain=_SUBDOMAIN, healthy_ips=None):
    healthy_ips = [_make_ip()] if healthy_ips is None else healthy_ips
    return AHealthyRecord(subdomain=subdomain, healthy_ips=healthy_ips)


def _assert_record_state(record, *, subdomain=_SUBDOMAIN, healthy_ips):
    assert record.subdomain == subdomain
    assert record.healthy_ips == frozenset(healthy_ips)


class TestAHealthyRecordInitialization:
    def test_init_stores_subdomain_and_ips_as_frozenset(self):
        healthy_ips = [
            _make_ip("192.168.1.1", 80, True),
            _make_ip("192.168.1.2", 80, True),
        ]

        record = _make_record(healthy_ips=healthy_ips)

        _assert_record_state(record, healthy_ips=healthy_ips)


class TestAHealthyRecordEqualityAndHashing:
    def test_equal_when_subdomain_matches_regardless_of_ip_state(self):
        record = _make_record(healthy_ips=[_make_ip("192.168.1.1", 80, True)])
        same_subdomain_record = _make_record(
            healthy_ips=[_make_ip("192.168.1.2", 443, False)]
        )

        assert record == same_subdomain_record
        assert {record, same_subdomain_record} == {record}

    def test_not_equal_when_subdomain_differs(self):
        record = _make_record(subdomain=_SUBDOMAIN)
        other_record = _make_record(subdomain=_OTHER_SUBDOMAIN)

        assert record != other_record
        assert {record} != {other_record}

    @pytest.mark.parametrize(
        "other",
        [
            "test.example.com",
            None,
        ],
    )
    def test_not_equal_to_other_types(self, other):
        assert _make_record() != other


class TestAHealthyRecordUpdates:
    def test_updated_ips_returns_same_instance_when_ips_are_unchanged(self):
        healthy_ips = [
            _make_ip("192.168.1.1", 80, True),
            _make_ip("192.168.1.2", 80, True),
        ]
        record = _make_record(healthy_ips=healthy_ips)

        updated_record = record.updated_ips(healthy_ips)

        assert updated_record is record
        _assert_record_state(updated_record, healthy_ips=healthy_ips)

    def test_updated_ips_returns_new_record_when_ips_change(self):
        original_ips = [
            _make_ip("192.168.1.1", 80, True),
            _make_ip("192.168.1.2", 80, True),
        ]
        new_ips = [
            _make_ip("192.168.1.3", 80, True),
            _make_ip("192.168.1.4", 443, True),
        ]
        record = _make_record(healthy_ips=original_ips)

        updated_record = record.updated_ips(new_ips)

        assert updated_record is not record
        assert updated_record == record
        _assert_record_state(updated_record, healthy_ips=new_ips)
        assert updated_record.healthy_ips != record.healthy_ips


class TestAHealthyRecordRepresentation:
    def test_repr_shows_subdomain_and_ips(self):
        healthy_ips = [
            _make_ip("192.168.1.1", 80, True),
            _make_ip("192.168.1.2", 80, True),
        ]
        record = _make_record(healthy_ips=healthy_ips)

        as_text = repr(record)

        assert as_text.startswith(
            f"AHealthyRecord(subdomain={_SUBDOMAIN}, healthy_ips=["
        )
        assert as_text.endswith("])")
        assert all(repr(healthy_ip) in as_text for healthy_ip in healthy_ips)
