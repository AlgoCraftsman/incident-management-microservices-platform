# Supply Chain Security

The platform uses automated dependency monitoring and pull request audit gates to
keep runtime, build, and workflow dependencies visible.

## Dependabot Version Updates

Dependabot is configured in `.github/dependabot.yml` for:

| Ecosystem | Scope | Schedule |
| --- | --- | --- |
| GitHub Actions | `.github/workflows` | Weekly on Monday |
| Docker | Service Dockerfiles, Kubernetes base manifests, and Helm chart image references | Weekly on Monday |
| Docker Compose | Local PostgreSQL and Redis images | Weekly on Monday |
| Pip | Service requirements and `platform-common` | Weekly on Tuesday |

Python minor and patch updates are grouped by dependency name across service
directories so shared runtime dependencies move together. Major updates remain
separate for more deliberate review.

## Pull Request Dependency Audit

The `Dependency Audit` workflow runs on every pull request and on pushes to
`main`. It audits each service requirements file with `pip-audit` and blocks
known vulnerable Python dependency resolutions before merge.

The workflow does not depend on GitHub Advanced Security or the repository
dependency review API. That keeps the PR gate portable for repositories where
GitHub dependency review is not available.

GitHub's Dependency Review action can be reintroduced later if dependency graph
and GitHub Advanced Security support are enabled for the repository.

## Release Image Attestations

CI publishes service images to GitHub Container Registry on pushes to `main`.
Those release-image builds generate:

- SBOM attestations for package inventory visibility.
- Provenance attestations with `mode=max` for build metadata and source
  traceability.

Pull request builds still compile and scan images, but attestation publishing is
limited to main-branch GHCR releases because unpublished PR images do not have a
registry artifact to attach attestations to.

## Operator Notes

Treat Dependabot PRs like application changes:

- Let the full CI pipeline pass before merging.
- Review dependency release notes for runtime or deployment behavior changes.
- Prefer small grouped updates over broad upgrade batches when failures need
  investigation.
- Merge security updates promptly after validation, even outside the weekly
  version-update cadence.
