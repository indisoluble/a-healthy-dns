#!/usr/bin/env python3

import datetime
import unittest.mock

import dns.dnssec

from indisoluble.a_healthy_dns.records.dnssec import ExtendedPrivateKey, iter_rrsig_key

_MAX_INTERVAL = 60
_DNSKEY_TTL = 1200
_RRSIG_RESIGN_SECONDS = 1200
_RRSIG_EXPIRATION_SECONDS = 3120
_FIXED_NOW = datetime.datetime(2025, 6, 21, 12, 0, 0, tzinfo=datetime.timezone.utc)


def _make_extended_private_key():
    mock_private_key = unittest.mock.Mock(spec=dns.dnssec.PrivateKey)
    mock_dnskey = unittest.mock.Mock(spec=dns.dnssec.DNSKEY)

    return ExtendedPrivateKey(
        private_key=mock_private_key,
        dnskey=mock_dnskey,
    )


def _configure_datetime_mock(mock_datetime, timestamps):
    mock_datetime.datetime.now.side_effect = timestamps
    mock_datetime.timezone = datetime.timezone
    mock_datetime.timedelta = datetime.timedelta


def _assert_rrsig_key(result, *, ext_private_key, inception):
    assert result.resign == inception + datetime.timedelta(
        seconds=_RRSIG_RESIGN_SECONDS
    )
    assert result.key.keys == [(ext_private_key.private_key, ext_private_key.dnskey)]
    assert result.key.dnskey_ttl == _DNSKEY_TTL
    assert result.key.inception == inception
    assert result.key.expiration == inception + datetime.timedelta(
        seconds=_RRSIG_EXPIRATION_SECONDS
    )


class TestRRSigKeyGeneration:
    @unittest.mock.patch("indisoluble.a_healthy_dns.records.dnssec.datetime")
    def test_first_iteration_returns_expected_rrsig_key(self, mock_datetime):
        ext_private_key = _make_extended_private_key()
        _configure_datetime_mock(mock_datetime, [_FIXED_NOW])

        rrsig_key_iterator = iter_rrsig_key(_MAX_INTERVAL, ext_private_key)
        result = next(rrsig_key_iterator)

        _assert_rrsig_key(result, ext_private_key=ext_private_key, inception=_FIXED_NOW)

    @unittest.mock.patch("indisoluble.a_healthy_dns.records.dnssec.datetime")
    def test_multiple_iterations_use_current_timestamp(self, mock_datetime):
        timestamps = [
            datetime.datetime(2025, 6, 21, 12, 0, 0, tzinfo=datetime.timezone.utc),
            datetime.datetime(2025, 6, 22, 12, 0, 0, tzinfo=datetime.timezone.utc),
            datetime.datetime(2025, 6, 23, 12, 0, 0, tzinfo=datetime.timezone.utc),
        ]
        ext_private_key = _make_extended_private_key()
        _configure_datetime_mock(mock_datetime, timestamps)

        rrsig_key_iterator = iter_rrsig_key(_MAX_INTERVAL, ext_private_key)
        results = [next(rrsig_key_iterator) for _ in timestamps]

        assert len(results) == len(timestamps)
        for result, timestamp in zip(results, timestamps):
            _assert_rrsig_key(
                result,
                ext_private_key=ext_private_key,
                inception=timestamp,
            )
