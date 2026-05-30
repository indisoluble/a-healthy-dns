#!/usr/bin/env python3

import pytest

from indisoluble.a_healthy_dns.tools.is_valid_subdomain import (
    is_valid_fqdn,
    is_valid_subdomain,
)

_LABEL_ERROR = "Labels must contain only ASCII letters, digits, or hyphens"
_LABEL_LENGTH_ERROR = "Labels must be 63 characters or fewer"
_LABEL_POSITION_ERROR = "Labels must start and end with an ASCII letter or digit"
_NAME_LENGTH_ERROR = "It must be 253 characters or fewer"


def _assert_valid(result):
    success, message = result

    assert success is True
    assert message == ""


def _assert_invalid(result, expected_message):
    success, message = result

    assert success is False
    assert message == expected_message


class TestValidSubdomains:
    @pytest.mark.parametrize(
        "valid_subdomain",
        [
            "example",
            "sub-domain",
            "sub.domain",
            "sub-domain.example",
            "123.example",
            "example123",
            "123domain456",
            "a",
            "1",
            "a-1-b",
            "a.b.c.d",
            "a.b.c.d.e",
        ],
    )
    def test_accepts_subdomain(self, valid_subdomain):
        _assert_valid(is_valid_subdomain(valid_subdomain))


class TestInvalidSubdomains:
    @pytest.mark.parametrize(
        "invalid_subdomain",
        [
            None,
            123,
            1.5,
            [],
            {},
        ],
    )
    def test_rejects_non_string_values(self, invalid_subdomain):
        _assert_invalid(is_valid_subdomain(invalid_subdomain), "It must be a string")

    def test_rejects_empty_string(self):
        _assert_invalid(is_valid_subdomain(""), "It cannot be empty")

    @pytest.mark.parametrize(
        "invalid_subdomain",
        [
            "domain@example",
            "domain_example",
            "domain.example!",
            "domain..example",
            ".domain",
            "domain.",
            "domain example",
            "mañana.example",
            "漢.example",
        ],
    )
    def test_rejects_invalid_labels(self, invalid_subdomain):
        _assert_invalid(is_valid_subdomain(invalid_subdomain), _LABEL_ERROR)

    @pytest.mark.parametrize(
        "invalid_subdomain",
        [
            " example",
            "example ",
            "sub domain",
        ],
    )
    def test_rejects_whitespace(self, invalid_subdomain):
        _assert_invalid(is_valid_subdomain(invalid_subdomain), _LABEL_ERROR)

    def test_rejects_label_longer_than_dns_limit(self):
        _assert_invalid(is_valid_subdomain("a" * 64), _LABEL_LENGTH_ERROR)

    @pytest.mark.parametrize(
        "invalid_subdomain",
        [
            "-example",
            "example-",
            "api.-example",
            "api.example-",
        ],
    )
    def test_rejects_labels_that_start_or_end_with_hyphen(self, invalid_subdomain):
        _assert_invalid(is_valid_subdomain(invalid_subdomain), _LABEL_POSITION_ERROR)

    def test_rejects_name_longer_than_dns_text_limit(self):
        _assert_invalid(
            is_valid_subdomain(".".join(["a" * 63] * 4)), _NAME_LENGTH_ERROR
        )

    def test_rejects_name_that_becomes_too_long_with_origin(self):
        _assert_invalid(
            is_valid_subdomain(
                ".".join(["a" * 63, "b" * 63, "c" * 63, "d" * 47]),
                "origin.example",
            ),
            "It must be 253 characters or fewer with the origin",
        )


class TestValidFqdns:
    @pytest.mark.parametrize(
        "valid_fqdn",
        [
            "ns1.example.com",
            "sub-domain.example",
            "a.b",
        ],
    )
    def test_accepts_dotted_hostname(self, valid_fqdn):
        _assert_valid(is_valid_fqdn(valid_fqdn))


class TestInvalidFqdns:
    def test_rejects_hostname_without_dot(self):
        _assert_invalid(
            is_valid_fqdn("ns1"),
            "It must be a fully-qualified hostname",
        )

    def test_rejects_empty_string(self):
        _assert_invalid(is_valid_fqdn(""), "It cannot be empty")

    def test_rejects_invalid_labels(self):
        _assert_invalid(is_valid_fqdn("ns1.example@.com"), _LABEL_ERROR)

    def test_rejects_label_longer_than_dns_limit(self):
        _assert_invalid(
            is_valid_fqdn(f"{'a' * 64}.example.com"), _LABEL_LENGTH_ERROR
        )

    def test_rejects_unicode_hostname(self):
        _assert_invalid(is_valid_fqdn("mañana.example.com"), _LABEL_ERROR)

    def test_rejects_label_that_starts_or_ends_with_hyphen(self):
        _assert_invalid(is_valid_fqdn("-ns.example.com"), _LABEL_POSITION_ERROR)
