# Quick Start

All commands below are derived from executable code/config.

## Local Setup
```bash
python -m pip install --upgrade pip
pip install .
```
Evidence: `setup.py:3-12`, `.github/workflows/test-py-code.yml:24-29`.

## Run Tests
```bash
pytest
```
Coverage variant used in CI:
```bash
pytest --cov=indisoluble.a_healthy_dns --cov-report=term --cov-report=xml
```
Evidence: `.github/workflows/test-py-code.yml:30-33`.

## Run Service (CLI)
```bash
a-healthy-dns \
  --hosted-zone example.com \
  --zone-resolutions '{"www":{"ips":["127.0.0.1"],"health_port":80}}' \
  --ns '["ns1.example.com"]' \
  --port 53053 \
  --log-level info \
  --test-min-interval 30 \
  --test-timeout 2
```
Required flags and defaults: `indisoluble/a_healthy_dns/main.py:115-201`.

## Optional DNSSEC Args
```bash
--priv-key-path /app/keys/private.pem --priv-key-alg RSASHA256
```
Evidence: `indisoluble/a_healthy_dns/main.py:184-201`, `indisoluble/a_healthy_dns/dns_server_config_factory.py:201-216`.

## Run with Docker
```bash
docker build -t a-healthy-dns:test .
docker run --rm -p 53053:53053/udp \
  -e DNS_PORT="53053" \
  -e DNS_HOSTED_ZONE="example.com" \
  -e DNS_ZONE_RESOLUTIONS='{"www":{"ips":["127.0.0.1"],"health_port":80}}' \
  -e DNS_NAME_SERVERS='["ns1.example.com"]' \
  a-healthy-dns:test
```
Evidence: `Dockerfile:66-127`, `.github/workflows/test-docker.yml:45-57`.
