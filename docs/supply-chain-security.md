# Supply Chain Security

The platform uses automated dependency monitoring and pull request review gates
to keep runtime, build, and workflow dependencies visible.

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

## Pull Request Dependency Review

The `Dependency Review` workflow runs on every pull request. It blocks changes
that introduce:

- Runtime, development, or unknown-scope vulnerabilities at high severity or
  higher.
- Dependencies outside the configured permissive-license allow list.

The workflow also includes OpenSSF Scorecard and patched-version details in the
job output to make dependency review easier during PR triage.

## Operator Notes

Treat Dependabot PRs like application changes:

- Let the full CI pipeline pass before merging.
- Review dependency release notes for runtime or deployment behavior changes.
- Prefer small grouped updates over broad upgrade batches when failures need
  investigation.
- Merge security updates promptly after validation, even outside the weekly
  version-update cadence.
