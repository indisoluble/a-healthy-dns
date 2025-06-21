#!/usr/bin/env python3

import datetime
import unittest.mock

import dns.dnssec

from indisoluble.a_healthy_dns.dns_server_config_factory import ExtendedPrivateKey
from indisoluble.a_healthy_dns.records.dnssec import iter_rrsig_key


@unittest.mock.patch("indisoluble.a_healthy_dns.records.dnssec.datetime")
def test_iter_rrsig_key_first_iteration(mock_datetime):
    fixed_now = datetime.datetime(2025, 6, 21, 12, 0, 0, tzinfo=datetime.timezone.utc)
    mock_datetime.datetime.now.return_value = fixed_now
    mock_datetime.timezone = datetime.timezone
    mock_datetime.timedelta = datetime.timedelta

    mock_private_key = unittest.mock.Mock(spec=dns.dnssec.PrivateKey)
    mock_dnskey = unittest.mock.Mock(spec=dns.dnssec.DNSKEY)
    ext_private_key = ExtendedPrivateKey(
        private_key=mock_private_key, dnskey=mock_dnskey
    )

    max_interval = 60

    rrsig_key_iterator = iter_rrsig_key(max_interval, ext_private_key)
    result = next(rrsig_key_iterator)

    expected_ttl = 1200
    expected_resign = fixed_now + datetime.timedelta(seconds=1200)
    expected_expiration = fixed_now + datetime.timedelta(seconds=3120)

    assert result.resign == expected_resign

    assert result.key.keys == [(mock_private_key, mock_dnskey)]
    assert result.key.dnskey_ttl == expected_ttl
    assert result.key.inception == fixed_now
    assert result.key.expiration == expected_expiration


@unittest.mock.patch("indisoluble.a_healthy_dns.records.dnssec.datetime")
def test_iter_rrsig_key_multiple_iterations(mock_datetime):
    timestamps = [
        datetime.datetime(2025, 6, 21, 12, 0, 0, tzinfo=datetime.timezone.utc),
        datetime.datetime(2025, 6, 22, 12, 0, 0, tzinfo=datetime.timezone.utc),
        datetime.datetime(2025, 6, 23, 12, 0, 0, tzinfo=datetime.timezone.utc),
    ]
    mock_datetime.datetime.now.side_effect = timestamps
    mock_datetime.timezone = datetime.timezone
    mock_datetime.timedelta = datetime.timedelta

    mock_private_key = unittest.mock.Mock(spec=dns.dnssec.PrivateKey)
    mock_dnskey = unittest.mock.Mock(spec=dns.dnssec.DNSKEY)
    ext_private_key = ExtendedPrivateKey(
        private_key=mock_private_key, dnskey=mock_dnskey
    )

    max_interval = 60

    rrsig_key_iterator = iter_rrsig_key(max_interval, ext_private_key)
    results = [next(rrsig_key_iterator) for _ in range(len(timestamps))]

    assert len(results) == len(timestamps)
    for i in range(len(results)):
        assert results[i].key.inception == timestamps[i]
