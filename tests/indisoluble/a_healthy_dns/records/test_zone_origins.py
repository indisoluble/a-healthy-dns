#!/usr/bin/env python3

import dns.name
import pytest

from indisoluble.a_healthy_dns.records.zone_origins import ZoneOrigins


@pytest.mark.parametrize(
    "invalid_primary", [None, 123, 1.5, [], {}, "", "bad!primary", "example..com"]
)
def test_init_raises_for_invalid_primary(invalid_primary):
    with pytest.raises(ValueError):
        ZoneOrigins(invalid_primary, [])


@pytest.mark.parametrize(
    "invalid_alias",
    [
        None,
        123,
        1.5,
        [],
        {},
        "",
        "bad!alias",
        "alias..com",
    ],
)
def test_init_raises_for_invalid_alias(invalid_alias):
    with pytest.raises(ValueError):
        ZoneOrigins("example.com", [invalid_alias])


def test_primary_is_parsed_as_absolute_name():
    origins = ZoneOrigins("example.com", [])

    assert origins.primary == dns.name.from_text("example.com", origin=dns.name.root)


def test_relativize_keeps_relative_name_as_is():
    origins = ZoneOrigins("example.com", [])
    relative_name = dns.name.from_text("www", origin=None)

    result = origins.relativize(relative_name)

    assert result == relative_name


def test_relativize_absolute_name_under_primary():
    origins = ZoneOrigins("example.com", [])
    absolute_name = dns.name.from_text("www", origin=dns.name.from_text("example.com"))

    result = origins.relativize(absolute_name)

    assert result == dns.name.from_text("www", origin=None)


def test_relativize_absolute_name_under_alias():
    origins = ZoneOrigins("example.com", ["alias.com"])
    absolute_name = dns.name.from_text("www", origin=dns.name.from_text("alias.com"))

    result = origins.relativize(absolute_name)

    assert result == dns.name.from_text("www", origin=None)


def test_relativize_returns_none_for_unmatched_absolute_name():
    origins = ZoneOrigins("example.com", ["alias.com"])
    absolute_name = dns.name.from_text("www", origin=dns.name.from_text("other.com"))

    result = origins.relativize(absolute_name)

    assert result is None


def test_relativize_prefers_most_specific_matching_origin():
    origins = ZoneOrigins("example.com", ["dev.example.com"])
    absolute_name = dns.name.from_text(
        "api.dev", origin=dns.name.from_text("example.com")
    )

    result = origins.relativize(absolute_name)

    assert result == dns.name.from_text("api", origin=None)


def test_eq_returns_true_for_identical_zone_origins():
    origins1 = ZoneOrigins("example.com", ["alias1.com", "alias2.com"])
    origins2 = ZoneOrigins("example.com", ["alias1.com", "alias2.com"])

    assert origins1 == origins2


def test_eq_returns_true_for_same_zones_different_order():
    origins1 = ZoneOrigins("example.com", ["alias1.com", "alias2.com"])
    origins2 = ZoneOrigins("example.com", ["alias2.com", "alias1.com"])

    assert origins1 == origins2


def test_eq_returns_true_for_same_zones_with_repited_aliases():
    origins1 = ZoneOrigins("example.com", ["alias1.com", "alias2.com", "alias1.com"])
    origins2 = ZoneOrigins("example.com", ["alias2.com", "alias1.com"])

    assert origins1 == origins2


def test_eq_returns_false_for_different_primary():
    origins1 = ZoneOrigins("example.com", [])
    origins2 = ZoneOrigins("other.com", [])

    assert origins1 != origins2


def test_eq_returns_false_for_different_aliases():
    origins1 = ZoneOrigins("example.com", ["alias1.com"])
    origins2 = ZoneOrigins("example.com", ["alias2.com"])

    assert origins1 != origins2


def test_eq_returns_false_for_non_zone_origins():
    origins = ZoneOrigins("example.com", [])

    assert origins.__eq__("not a ZoneOrigins") is False


def test_hash_is_consistent():
    origins1 = ZoneOrigins("example.com", ["alias1.com", "alias2.com", "alias1.com"])
    origins2 = ZoneOrigins("example.com", ["alias2.com", "alias1.com"])

    assert hash(origins1) == hash(origins2)


def test_hash_allows_use_in_set():
    origins1 = ZoneOrigins("example.com", ["alias1.com"])
    origins2 = ZoneOrigins("example.com", ["alias1.com"])
    origins3 = ZoneOrigins("other.com", [])

    zone_set = {origins1, origins2, origins3}

    assert len(zone_set) == 2


def test_repr_shows_primary_and_aliases():
    origins = ZoneOrigins("example.com", ["alias1.com", "alias2.com"])

    result = repr(origins)

    assert "example.com." in result
    assert "alias1.com." in result
    assert "alias2.com." in result
    assert result.startswith("ZoneOrigins(")


def test_repr_shows_no_aliases_when_empty():
    origins = ZoneOrigins("example.com", [])

    result = repr(origins)

    assert "example.com." in result
    assert result == "ZoneOrigins(primary='example.com.', aliases=[])"
