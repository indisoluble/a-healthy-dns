#!/usr/bin/env bash
# validate-level1.sh — curated Level 1 DNS validation queries
#
# Sends the four curated dig queries for manual smoke-validation of the primary
# Level 1 response scenarios documented in docs/manual-validation.md.
#
# Usage:
#   ./scripts/validate-level1.sh [HOST] [PORT] [ZONE] [SUBDOMAIN]
#
# Defaults:
#   HOST=127.0.0.1   PORT=53053   ZONE=example.local   SUBDOMAIN=www
#
# Prerequisites: dig must be installed (dnsutils on Debian/Ubuntu,
#                bind-utils on RHEL/Fedora).

set -euo pipefail

HOST="${1:-127.0.0.1}"
PORT="${2:-53053}"
ZONE="${3:-example.local}"
SUBDOMAIN="${4:-www}"

DIG="dig @${HOST} -p ${PORT} +norecurse +noadditional"

echo "=== Level 1 DNS validation ==="
echo "Server : ${HOST}:${PORT}"
echo "Zone   : ${ZONE}"
echo ""

echo "--- Query 1: Positive A response ---"
echo "Expected: NOERROR, answer=1 A RRset, authority=empty, additional=empty"
${DIG} "${SUBDOMAIN}.${ZONE}" A
echo ""

echo "--- Query 2: In-zone NXDOMAIN ---"
echo "Expected: NXDOMAIN, answer=empty, authority=1 apex SOA, additional=empty"
${DIG} "missing-name.${ZONE}" A
echo ""

echo "--- Query 3: In-zone NODATA (existing owner, absent type) ---"
echo "Expected: NOERROR, answer=empty, authority=1 apex SOA, additional=empty"
${DIG} "${SUBDOMAIN}.${ZONE}" AAAA
echo ""

echo "--- Query 4: Out-of-zone REFUSED ---"
echo "Expected: REFUSED, answer=empty, authority=empty, additional=empty"
${DIG} "${SUBDOMAIN}.unrelated.test" A
echo ""

echo "=== Done ==="
