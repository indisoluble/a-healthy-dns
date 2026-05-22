#!/usr/bin/env python3

import unittest.mock

import dns.name
import dns.rdataclass
import dns.rdatatype

from indisoluble.a_healthy_dns.records.soa_record import (
    iter_soa_record,
    _iter_soa_serial,
)
from indisoluble.a_healthy_dns.records.time import _RFC8767_MAX_TTL as RFC8767_MAX_TTL

_MAX_INTERVAL = 60
_ORIGIN_NAME = dns.name.from_text("example.com")
_PRIMARY_NS = "ns1.example.com."
_SERIAL = 1234567890


def _next_soa_rdataset(serials=None, max_interval=_MAX_INTERVAL):
    serials = [_SERIAL] if serials is None else serials

    with unittest.mock.patch(
        "indisoluble.a_healthy_dns.records.soa_record._iter_soa_serial",
        return_value=iter(serials),
    ):
        soa_record_iterator = iter_soa_record(max_interval, _ORIGIN_NAME, _PRIMARY_NS)
        return next(soa_record_iterator)


def _soa_rdata(rdataset):
    return next(iter(rdataset))


def _assert_soa_rdataset(rdataset, *, ttl):
    assert rdataset is not None
    assert rdataset.ttl == ttl
    assert rdataset.rdtype == dns.rdatatype.SOA
    assert rdataset.rdclass == dns.rdataclass.IN


class TestSoaRecordGeneration:
    def test_first_iteration_returns_expected_soa_rdataset(self):
        result = _next_soa_rdataset()
        soa_rdata = _soa_rdata(result)

        _assert_soa_rdataset(result, ttl=3600)
        assert soa_rdata.mname == dns.name.from_text(_PRIMARY_NS)
        assert soa_rdata.rname == dns.name.from_text(f"hostmaster.{_ORIGIN_NAME}")
        assert soa_rdata.serial == _SERIAL
        assert soa_rdata.refresh == 1200
        assert soa_rdata.retry == 120
        assert soa_rdata.expire == 600
        assert soa_rdata.minimum == 120

    @unittest.mock.patch(
        "indisoluble.a_healthy_dns.records.soa_record._iter_soa_serial"
    )
    def test_multiple_iterations_use_next_serial(self, mock_iter_soa_serial):
        serials = [1234567890, 1234567891, 1234567892]
        mock_iter_soa_serial.return_value = iter(serials)
        soa_record_iterator = iter_soa_record(_MAX_INTERVAL, _ORIGIN_NAME, _PRIMARY_NS)

        for expected_serial in serials:
            result = next(soa_record_iterator)

            assert _soa_rdata(result).serial == expected_serial

    def test_caps_ttls_and_soa_time_values_to_rfc8767_max(self):
        max_interval = 2_000_000_000

        result = _next_soa_rdataset(max_interval=max_interval)
        soa_rdata = _soa_rdata(result)

        _assert_soa_rdataset(result, ttl=RFC8767_MAX_TTL)
        assert soa_rdata.refresh == RFC8767_MAX_TTL
        assert soa_rdata.retry == RFC8767_MAX_TTL
        assert soa_rdata.expire == RFC8767_MAX_TTL
        assert soa_rdata.minimum == RFC8767_MAX_TTL


class TestSoaSerialGeneration:
    @unittest.mock.patch("indisoluble.a_healthy_dns.records.soa_record.time.sleep")
    @unittest.mock.patch(
        "indisoluble.a_healthy_dns.records.soa_record.uint32_current_time"
    )
    def test_waits_on_duplicate_timestamp(self, mock_uint32_current_time, mock_sleep):
        mock_uint32_current_time.side_effect = [1234567890, 1234567890, 1234567891]
        serial_iterator = _iter_soa_serial()

        assert next(serial_iterator) == 1234567890
        assert next(serial_iterator) == 1234567891
        mock_sleep.assert_called_once_with(1)
