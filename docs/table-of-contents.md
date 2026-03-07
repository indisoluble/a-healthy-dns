# Documentation Index

This document serves as the authoritative index for all project documentation.

## Minimum Reading Set / Core Docs

**Required reading for all contributors and agents working on this repository:**

1. [README.md](../README.md) — Quick-start guide and project overview
2. [AGENTS.md](../AGENTS.md) — Non-negotiable coding agent contract
3. [docs/project-brief.md](project-brief.md) — Project goals, non-goals, constraints, and requirements
4. [docs/system-patterns.md](system-patterns.md) — Architecture patterns and component design
5. [docs/project-rules.md](project-rules.md) — Python conventions, testing strategy, and QA commands

## Reference Documentation

### Configuration and Deployment
- [docs/configuration.md](configuration.md) — Detailed configuration reference
- [docs/docker.md](docker.md) — Docker deployment guide

### Operations
- [docs/troubleshooting.md](troubleshooting.md) — Troubleshooting and debugging guide

## External References

- [dnspython documentation](https://dnspython.readthedocs.io/) — DNS protocol library
- [cryptography documentation](https://cryptography.io/) — DNSSEC cryptographic operations

## Documentation Maintenance

### Adding New Documentation

When adding new documentation:
1. Create the file under `docs/`
2. Add an entry to this index in the appropriate section
3. If the document influences implementation decisions, add it to the Minimum Reading Set
4. Update links from `README.md` if the content is part of the quick-start path

### Documentation Structure

- **README.md** — Quick-start entrypoint; minimal content, maximum clarity
- **docs/** — All detailed/reference documentation lives here
- **AGENTS.md** — Coding standards and agent workflow contract (root level)

---

**Last Updated:** March 7, 2026  
**Documentation Version:** 1.0 (Bootstrap)
