# Release

Versioning, changelog, release publication, artifact publication, and compatibility rules for **A Healthy DNS**.

This document is the canonical home for version policy, release steps, and published artifact rules. CI validation gates and documentation update workflow live in [`docs/workflow.md`](workflow.md).

## Versioning

The single source of truth for the package version is the `version` field in `pyproject.toml`.

Rules:

- Every merge result on `master` must increase the version relative to its first parent.
- Version checks are enforced by `.github/workflows/test-version.yml`, which compares the current `pyproject.toml` version against `HEAD~1` using `packaging.version`.
- Use PEP 440 version strings, for example `0.1.39`.
- Do not create git tags or GitHub releases manually; the `release version` CI workflow handles this automatically after all required checks pass on `master`.

## Release Publication

Releases are fully automated. No manual tagging or Docker Hub pushes are required.

Steps triggered on every merge to `master`:

1. Before merging, update `version` in `pyproject.toml` to a new PEP 440 value higher than the current version on `master`.
2. Merge to `master`.
3. CI runs `test python code`, `test integration`, and `test version` in parallel.
4. If all three pass, `validate tests` succeeds.
5. `release version` creates the git tag and GitHub release.
6. `release docker` pushes the tagged Docker image to Docker Hub.

## Artifacts

Each release produces two artifacts:

| Artifact | Location | Tag convention |
|---|---|---|
| GitHub release | GitHub Releases page | `v<version>` from `pyproject.toml` |
| Docker image | `indisoluble/a-healthy-dns` on Docker Hub | version from `pyproject.toml` |

Release notes are generated automatically from the commit and PR history by the `release version` workflow.

## Changelog

The GitHub Releases page is the canonical changelog. Each release entry corresponds to one version increment merged to `master`.

## Compatibility and Migration

No formal compatibility policy is defined yet. When a change breaks existing configuration or behavior:

- Note the breaking change in the commit message.
- Note it in the PR description so it appears in the auto-generated release notes.
- Update [`docs/configuration-reference.md`](configuration-reference.md) to reflect the new configuration contract.
