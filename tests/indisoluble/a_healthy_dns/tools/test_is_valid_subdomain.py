#!/usr/bin/env python3

import pytest

from indisoluble.a_healthy_dns.tools.is_valid_subdomain import is_valid_subdomain


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
def test_valid_subdomains(valid_subdomain):
    result, message = is_valid_subdomain(valid_subdomain)
    assert result is True
    assert message == ""


@pytest.mark.parametrize(
    "invalid_subdomain,expected_message",
    [
        (None, "It must be a string"),
        (123, "It must be a string"),
        (1.5, "It must be a string"),
        ([], "It must be a string"),
        ({}, "It must be a string"),
        ("", "It cannot be empty"),
        (
            "domain@example",
            "Labels must contain only alphanumeric characters or hyphens",
        ),
        (
            "domain_example",
            "Labels must contain only alphanumeric characters or hyphens",
        ),
        (
            "domain.example!",
            "Labels must contain only alphanumeric characters or hyphens",
        ),
        (
            "domain..example",
            "Labels must contain only alphanumeric characters or hyphens",
        ),
        (".domain", "Labels must contain only alphanumeric characters or hyphens"),
        ("domain.", "Labels must contain only alphanumeric characters or hyphens"),
        (
            "domain example",
            "Labels must contain only alphanumeric characters or hyphens",
        ),
    ],
)
def test_invalid_subdomains(invalid_subdomain, expected_message):
    result, message = is_valid_subdomain(invalid_subdomain)
    assert result is False
    assert message == expected_message


@pytest.mark.parametrize(
    "subdomain,expected_message",
    [
        (" example", "Labels must contain only alphanumeric characters or hyphens"),
        ("example ", "Labels must contain only alphanumeric characters or hyphens"),
        ("sub domain", "Labels must contain only alphanumeric characters or hyphens"),
    ],
)
def test_subdomain_with_whitespace(subdomain, expected_message):
    result, message = is_valid_subdomain(subdomain)
    assert result is False
    assert message == expected_message
