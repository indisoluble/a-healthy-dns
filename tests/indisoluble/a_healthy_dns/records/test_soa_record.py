#!/usr/bin/env python3

import unittest.mock

import dns.name
import dns.rdataclass
import dns.rdatatype
import pytest

from indisoluble.a_healthy_dns.records.soa_record import (
    iter_soa_record,
    _iter_soa_serial,
)


@unittest.mock.patch("indisoluble.a_healthy_dns.records.soa_record._iter_soa_serial")
def test_iter_soa_record_first_iteration(mock_iter_soa_serial):
    mock_serial = 1234567890
    mock_iter_soa_serial.return_value = iter([mock_serial])

    max_interval = 60
    origin_name = dns.name.from_text("example.com")
    primary_ns = "ns1.example.com."

    soa_record_iterator = iter_soa_record(max_interval, origin_name, primary_ns)
    result = next(soa_record_iterator)

    expected_ttl = 3600  # max_interval * 2 * 30
    expected_refresh = 1200  # max_interval * 2 * 10
    expected_retry = 120  # max_interval * 2
    expected_expire = 600  # max_interval * 2 * 5
    expected_min_ttl = 120  # max_interval * 2

    assert result is not None
    assert result.ttl == expected_ttl
    assert result.rdtype == dns.rdatatype.SOA
    assert result.rdclass == dns.rdataclass.IN

    rdataset_str = str(result)
    assert primary_ns in rdataset_str
    assert f"hostmaster.{origin_name}" in rdataset_str
    assert str(mock_serial) in rdataset_str
    assert str(expected_refresh) in rdataset_str
    assert str(expected_retry) in rdataset_str
    assert str(expected_expire) in rdataset_str
    assert str(expected_min_ttl) in rdataset_str


@unittest.mock.patch("indisoluble.a_healthy_dns.records.soa_record._iter_soa_serial")
def test_iter_soa_record_multiple_iterations(mock_iter_soa_serial):
    serials = [1234567890, 1234567891, 1234567892]
    mock_iter_soa_serial.return_value = iter(serials)

    max_interval = 60
    origin_name = dns.name.from_text("example.com")
    primary_ns = "ns1.example.com"

    soa_record_iterator = iter_soa_record(max_interval, origin_name, primary_ns)

    for expected_serial in serials:
        result = next(soa_record_iterator)

        assert str(expected_serial) in str(result)


@unittest.mock.patch("indisoluble.a_healthy_dns.records.soa_record.time.sleep")
@unittest.mock.patch("indisoluble.a_healthy_dns.records.soa_record.uint32_current_time")
def test_iter_soa_serial_waits_on_duplicate(mock_uint32_current_time, mock_sleep):
    mock_uint32_current_time.side_effect = [1234567890, 1234567890, 1234567891]

    serial_iterator = _iter_soa_serial()

    first_serial = next(serial_iterator)
    assert first_serial == 1234567890

    # Second call should wait once and then return the new value
    second_serial = next(serial_iterator)
    assert second_serial == 1234567891

    # Verify that sleep was called once when duplicate was detected
    mock_sleep.assert_called_once_with(1)
