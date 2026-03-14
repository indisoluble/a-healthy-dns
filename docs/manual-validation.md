# Manual Level 1 DNS Validation

A guide for manually verifying wire-level DNS behaviour against the Level 1 authoritative UDP specification documented in [docs/RFC-conformance.md](RFC-conformance.md).

---

## Prerequisites

| Tool | Purpose |
|---|---|
| `dig` | Send DNS queries and inspect responses |
| `tcpdump` (or Wireshark) | Capture UDP packets on the wire |
| Python 3.10+ or Docker | Run the server locally |

Install `dig` via your OS package manager (`dnsutils` on Debian/Ubuntu, `bind-utils` on RHEL/Fedora).

---

## Starting the server locally

### Option A: Python source

```bash
# From the repository root
pip install -e .

a-healthy-dns \
  --hosted-zone example.local \
  --zone-resolutions '{"www":{"ips":["192.168.1.100"],"health_port":8080}}' \
  --ns '["ns1.example.local"]' \
  --port 53053
```

### Option B: Docker

```bash
docker run --rm \
  -p 53053:53053/udp \
  -e DNS_HOSTED_ZONE="example.local" \
  -e DNS_ZONE_RESOLUTIONS='{"www":{"ips":["192.168.1.100"],"health_port":8080}}' \
  -e DNS_NAME_SERVERS='["ns1.example.local"]' \
  -e DNS_PORT="53053" \
  indisoluble/a-healthy-dns
```

Both options expose the server on `127.0.0.1:53053/udp`.

---

## Capturing packets

In a separate terminal, start a `tcpdump` capture **before** sending queries:

```bash
# Linux loopback interface
sudo tcpdump -i lo -n -v 'udp port 53053'

# macOS loopback interface
sudo tcpdump -i lo0 -n -v 'udp port 53053'

# Save to file for later analysis in Wireshark
sudo tcpdump -i lo -n -w /tmp/dns-validation.pcap 'udp port 53053'
```

---

## Curated query set

The table below lists the queries to send and the Level 1 behavior expected for each.  Run them in order after starting the capture.  All commands assume the server is listening on `127.0.0.1:53053` with `example.local` as the hosted zone.

| # | Query | Expected RCODE | Expected answer | Expected authority |
|---|---|---|---|---|
| 1 | `www.example.local A` | `NOERROR` | 1 A RRset | empty |
| 2 | `missing-name.example.local A` | `NXDOMAIN` | empty | 1 apex SOA RRset |
| 3 | `www.example.local AAAA` | `NOERROR` | empty | 1 apex SOA RRset |
| 4 | `www.unrelated.test A` | `REFUSED` | empty | empty |

See `scripts/validate-level1.sh` for a script that emits all four commands.

### Query 1 — Positive A response

```bash
dig @127.0.0.1 -p 53053 www.example.local A +norecurse
```

Expected `dig` output (abbreviated):

```
;; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: <id>
;; flags: qr aa; QUERY: 1, ANSWER: 1, AUTHORITY: 0, ADDITIONAL: 0

;; ANSWER SECTION:
www.example.local.  <ttl>  IN  A  192.168.1.100
```

### Query 2 — In-zone NXDOMAIN

```bash
dig @127.0.0.1 -p 53053 missing-name.example.local A +norecurse
```

Expected output:

```
;; ->>HEADER<<- opcode: QUERY, status: NXDOMAIN, id: <id>
;; flags: qr aa; QUERY: 1, ANSWER: 0, AUTHORITY: 1, ADDITIONAL: 0

;; AUTHORITY SECTION:
example.local.  <ttl>  IN  SOA  ns1.example.local. ...
```

### Query 3 — In-zone NODATA (existing owner, absent type)

```bash
dig @127.0.0.1 -p 53053 www.example.local AAAA +norecurse
```

Expected output:

```
;; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: <id>
;; flags: qr aa; QUERY: 1, ANSWER: 0, AUTHORITY: 1, ADDITIONAL: 0

;; AUTHORITY SECTION:
example.local.  <ttl>  IN  SOA  ns1.example.local. ...
```

### Query 4 — Out-of-zone REFUSED

```bash
dig @127.0.0.1 -p 53053 www.unrelated.test A +norecurse
```

Expected output:

```
;; ->>HEADER<<- opcode: QUERY, status: REFUSED, id: <id>
;; flags: qr aa; QUERY: 1, ANSWER: 0, AUTHORITY: 0, ADDITIONAL: 0
```

---

## What to inspect in captures

For each request/response pair in `tcpdump` or Wireshark, verify the following fields.

### Header fields

| Field | Expected value | How to read it |
|---|---|---|
| **QR** | `1` (response) | `dig` shows `qr` in the flags line; Wireshark shows `Response: 1` |
| **ID** | Matches the query ID | `dig` prints `id:` in both query and response; confirm they are equal |
| **AA** | `1` (authoritative answer) | `dig` shows `aa` in the flags line |
| **RA** | `0` (not a recursive resolver) | `ra` must **not** appear in `dig` flags |
| **TC** | `0` (not truncated) | `tc` must **not** appear in `dig` flags for normal small responses |
| **RCODE** | Per table above | `dig` shows `status:` in the header line |

### Section shapes

| Response class | ANSWER | AUTHORITY | ADDITIONAL |
|---|---|---|---|
| Positive A | 1 A RRset | empty | empty |
| NXDOMAIN | empty | 1 SOA RRset (apex) | empty |
| NODATA (NOERROR) | empty | 1 SOA RRset (apex) | empty |
| REFUSED (out-of-zone) | empty | empty | empty |

### Authority section (negative responses)

For NXDOMAIN and NODATA responses, the single RRset in the authority section must be the zone apex SOA.  Confirm:

- Owner name matches the hosted zone apex (e.g. `example.local.`)
- `rdtype` is `SOA`
- TTL is present and non-zero

---

## Normative reference

All expected behaviors above are documented in [docs/RFC-conformance.md](RFC-conformance.md).  The relevant sections are:

- §1 (Level 1 behaviour table) — overall response classification
- §3.1 (RFC 1034) — AA flag, NXDOMAIN, REFUSED
- §3.2 (RFC 1035) — header fields, section structure
- §3.4 (RFC 2308) — SOA in authority for negative responses
