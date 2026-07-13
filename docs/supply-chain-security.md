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
| Pip | Security tooling, service requirements, and `platform-common` | Weekly on Tuesday |

Python minor and patch updates are grouped by dependency name across service
directories so shared runtime dependencies move together. Major updates remain
separate for more deliberate review.

Dependabot ignores SemVer major version updates for routine version-update PRs.
Major upgrades such as Python runtime, PostgreSQL, Redis, or GitHub Actions major
releases should be handled as planned migration branches with explicit release
notes review and validation.

## Pull Request Dependency Audit

The `Dependency Audit` workflow runs on every pull request and on pushes to
`main`. It audits each service requirements file with `pip-audit` and blocks
known vulnerable Python dependency resolutions before merge.

The `pip-audit` CLI version is pinned in `.github/requirements-security.txt`
instead of installed as an unbounded latest package. Dependabot monitors that
pin with the rest of the Python dependency manifests.

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

## Workflow Token Permissions

GitHub Actions workflows default to read-only repository contents access unless
a job needs a broader scope. The main CI workflow grants `packages: write` only
to the image build job because that job publishes GHCR images on `main`. Test,
manifest validation, dependency audit, and deployment jobs do not receive package
write access.

## Workflow Runtime Bounds

CI, dependency audit, and deployment jobs define explicit `timeout-minutes`
limits. Short validation jobs fail quickly when package resolution, scanner
execution, or cluster calls hang. Image build and deployment jobs get larger
budgets because they perform Docker builds, registry checks, Helm waits, and
rollout verification.

## Workflow Concurrency

CI and dependency audit workflows cancel older in-progress runs for the same
branch or pull request ref when a newer commit starts. This keeps required checks
focused on the latest revision and avoids spending runner time on stale commits.
The deployment workflow remains serialized per target environment and does not
cancel an in-progress deployment.

## Deployment Secret Handling

The release deployment workflow passes secret values to Helm from temporary
files and runs its pre-deploy Helm dry-run with `--hide-secret`. Sanitized
dry-run output is written under the runner temporary directory rather than the
repository workspace, reducing the chance that rendered Kubernetes Secret values
are retained in workflow files. The temporary Helm secret files are removed in a
final cleanup step that runs after both successful and failed deployment
attempts.

## Operator Notes

Treat Dependabot PRs like application changes:

- Let the full CI pipeline pass before merging.
- Review dependency release notes for runtime or deployment behavior changes.
- Prefer small grouped updates over broad upgrade batches when failures need
  investigation.
- Merge security updates promptly after validation, even outside the weekly
  version-update cadence.
- Treat major runtime, datastore, base image, or workflow action updates as
  planned migration work rather than routine Dependabot maintenance.
