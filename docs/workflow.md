# Workflow

Development, CI, and documentation workflow for **A Healthy DNS**.

This document is the canonical home for repository change process, CI validation, release readiness, and documentation update workflow. Versioning policy and release publication rules live in [`docs/release.md`](release.md). Engineering principles live in [`docs/engineering-rules.md`](engineering-rules.md); testing commands live in [`docs/testing.md`](testing.md); implementation notes live in [`docs/implementation-notes.md`](implementation-notes.md).

## CI Workflows

All workflows target the `master` branch.

The validation workflows `test python code`, `test integration`, and `test version` run on both pushes to `master` and pull requests targeting `master`. The remaining workflows are post-merge `workflow_run` chains on `master`: `validate tests` waits for the three validation workflows, `release version` runs only after successful validation, and `release docker` runs only after a successful GitHub release.

| Workflow | File | Trigger | Purpose |
|---|---|---|---|
| `test python code` | `test-py-code.yml` | push/PR -> master | Runs pytest with coverage, uploads to Codecov |
| `test integration` | `test-integration.yml` | push/PR -> master | Builds Docker image; runs end-to-end tests for alias zones, health-check-driven DNS state transitions, real container networking, and Compose syntax |
| `test version` | `test-version.yml` | push/PR -> master | Verifies version in `pyproject.toml` was increased |
| `validate tests` | `validate-tests.yml` | `workflow_run` on any of the three above | Gate: all three must pass for the same commit |
| `release version` | `release-version.yml` | after `validate tests` succeeds | Creates git tag and GitHub release from `pyproject.toml` version |
| `release docker` | `release-docker.yml` | after `release version` succeeds | Pushes `latest` and version-tagged Docker images for `linux/amd64` and `linux/arm64`, then updates the Docker Hub description from `README.md` |
| `security scan` | `security-scan.yml` | push -> master | Trivy vulnerability scan on Docker image, uploads SARIF to GitHub Security tab |

Rules:

- Do not merge or push a commit to `master` unless the required three gate workflows have passed for that commit or PR.
- Workflow names, triggers, workflow dependencies, and release-chain side effects are part of the automation contract. If you change a workflow's `name:`, trigger model, `workflow_run` dependency, release output, published artifact, or required secret, update every dependent workflow plus [`docs/testing.md`](testing.md), [`docs/release.md`](release.md), and this document as applicable.
- `security scan` is important, but it is not part of the three-workflow `validate tests` gate. The release chain depends on `test python code`, `test integration`, and `test version` only.

## Validate Tests Trigger Model

GitHub Actions `workflow_run` fires each time any one of the listed upstream workflows completes, not once after all three are done. This means `validate tests` may run before the other two upstream workflows have finished.

Early runs that fail because a sibling workflow has not completed yet are expected and are not the final picture. The meaningful result is the run that executes after all three required workflows for the same commit SHA have completed. The intended policy remains: all three required workflows must pass for the same commit.

## Documentation Workflow

- Use [`docs/table-of-contents.md`](table-of-contents.md) to identify the canonical owner before editing documentation.
- Update canonical documentation in the same change as any behavior, interface, architecture, configuration, operations, workflow, or constraint change.
- Keep `README.md` concise and entry-point oriented.
- Put long-form documentation under `docs/`.
- Avoid exact source line numbers in long-lived documentation; prefer module, class, function, and test references that survive ordinary code movement.
- If a legacy redirect document is introduced, keep it short and do not add new substantive content to it.
