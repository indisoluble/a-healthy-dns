# Build and Deployment

## Package Build
- Packaging uses `setuptools` with console script export.
- Version source is `setup.py` `version="0.1.26"` at time of analysis.
- Evidence: `setup.py:3-12`, `setup.py:5`.

## Docker Build
- Multi-stage image:
  - Builder installs compile dependencies and `pip install --user .`.
  - Runtime stage runs non-root and copies built artifacts.
- Evidence: `Dockerfile:2-24`, `Dockerfile:26-63`.

## Runtime Configuration
- Required container env vars:
  - `DNS_HOSTED_ZONE`
  - `DNS_ZONE_RESOLUTIONS`
  - `DNS_NAME_SERVERS`
- Entrypoint validates required vars and maps env vars to CLI args.
- Evidence: `Dockerfile:86-97`, `Dockerfile:98-125`.

## CI Workflows
- Python tests + coverage: `.github/workflows/test-py-code.yml`.
- Docker build + functional DNS checks: `.github/workflows/test-docker.yml`.
- Version bump enforcement on pushes/PRs: `.github/workflows/test-version.yml`.
- Aggregate pass gate before releases: `.github/workflows/validate-tests.yml`.
- Security scan using Trivy on built image: `.github/workflows/security-scan.yml`.

## Release Workflows
- Git tag + GitHub release is automated after `validate tests` success.
  - Evidence: `.github/workflows/release-version.yml:4-76`.
- Multi-arch Docker publish (`amd64`, `arm64`) with `latest` and version tags.
  - Evidence: `.github/workflows/release-docker.yml:39-49`.

## Local Commands
```bash
pip install .
pytest
docker build -t a-healthy-dns:test .
```
