# GitHub Operations Runbook

This runbook records the repository, environment, package, and security settings
that are part of the platform's delivery controls but cannot be enforced by
files in this repository. A repository administrator should apply the baseline
and review it after workflow, team, GitHub plan, or repository visibility
changes.

## Ownership and Review Cadence

- Repository administrators own branch rules, Actions settings, and security
  feature enablement.
- Release or platform owners own deployment environments, reviewers, cluster
  credentials, and GHCR access.
- Review this baseline quarterly and after any default-branch, workflow job,
  environment, package visibility, or GitHub plan change.
- Record plan-dependent controls that are unavailable as known gaps. Do not
  silently weaken another control to compensate.

## Protect `main`

Configure an active branch ruleset targeting the default branch, or an
equivalent branch protection rule for `main`, under **Settings > Rules**. Use a
single authoritative rule where possible so overlapping rules do not produce
unexpected results.

Recommended baseline:

| Control | Setting |
| --- | --- |
| Changes enter through pull requests | Required |
| Approving reviews | At least one approval |
| Stale approvals after new commits | Dismiss |
| Most recent reviewable push | Require approval from someone other than the pusher |
| Review conversations | Require resolution before merge |
| Status checks | Require all checks listed below |
| Branch freshness | Require the branch to be up to date before merge |
| Force pushes and deletion | Block |
| Administrator or role bypass | Do not allow routine bypass |

Do not enable linear history while the repository uses merge commits for pull
requests. Introduce that policy separately if the merge strategy changes. A
merge queue is optional and is most useful only after concurrent pull request
volume makes repeated branch updates expensive.

### Required Checks

Select check contexts from a recent pull request after each workflow has run at
least once. GitHub may display a context with its workflow prefix; select the
context that contains the following job name. Keep names unique across
workflows.

From the `CI` workflow:

- `API contracts`
- `Test incidents-service`
- `Test alerts-service`
- `Test oncall-service`
- `Test status-page-service`
- `Test platform-common`
- `Build incidents-service`
- `Build alerts-service`
- `Build oncall-service`
- `Build status-page-service`
- `Trivy incidents-service`
- `Trivy alerts-service`
- `Trivy oncall-service`
- `Trivy status-page-service`
- `Kubernetes and Helm manifests`
- `Checkov Dockerfiles`

From the `Dependency Audit` workflow:

- `Python dependencies (incidents-service)`
- `Python dependencies (alerts-service)`
- `Python dependencies (oncall-service)`
- `Python dependencies (status-page-service)`

When a workflow job is renamed, added, or removed, update the rule and this
runbook in the same pull request. A stale required context that no workflow
reports will block every merge. Do not make deployment jobs required for pull
requests: `Deploy Helm Release` is a manually dispatched, environment-gated
release workflow rather than a pull request validation workflow.

## Configure GitHub Actions

Under **Settings > Actions > General**:

- Set the default `GITHUB_TOKEN` permission to **Read repository contents and
  packages permissions**.
- Leave **Allow GitHub Actions to create and approve pull requests** disabled
  unless a reviewed automation use case requires it.
- Keep the repository's approved-action policy compatible with every pinned or
  versioned action under `.github/workflows`.

The workflows declare their own least-privilege permissions. The CI image build
job is the only job with `packages: write`; deployment has `packages: read`;
other jobs use read-only contents access.

## Configure Deployment Environments

Create `staging` and `production` under **Settings > Environments**. The names
must remain aligned with the choices in `.github/workflows/deploy.yml`.

| Control | `staging` | `production` |
| --- | --- | --- |
| Deployment branches and tags | Selected branch: `main` | Selected branch: `main` |
| Required reviewers | Platform/release owner when available | At least one platform/release reviewer |
| Prevent self-review | Enable when reviewers are configured | Enable |
| Administrator bypass | Permit only under a documented break-glass policy | Disable |

GitHub plan and repository visibility determine whether required reviewers and
some other protection rules are available. If the production reviewer control
is unavailable, record that limitation as a production gap and require an
out-of-band approval record until the plan or visibility supports enforcement.

Store these values as environment secrets in both environments, using separate
credentials and secret values for each target:

| Secret | Operational requirement |
| --- | --- |
| `KUBE_CONFIG_B64` | Base64 kubeconfig scoped to the target cluster and only the required namespace permissions. |
| `PLATFORM_API_KEYS` | Target-specific accepted public API keys. |
| `INTERNAL_API_KEY` | Target-specific service-to-service key. |
| `INCIDENTS_DB_PASSWORD` | Target-specific incidents database password. |
| `ALERTS_DB_PASSWORD` | Target-specific alerts database password. |
| `ONCALL_DB_PASSWORD` | Target-specific on-call database password. |
| `STATUS_PAGE_DB_PASSWORD` | Target-specific status-page database password. |

Do not duplicate these as repository secrets. Environment secrets are withheld
from the deployment job until configured protection rules pass. Rotate the
kubeconfig and application secrets on the organization's normal secret rotation
schedule, after suspected exposure, and when an operator loses access.

## Configure GHCR Packages

CI publishes four organization packages:

- `ghcr.io/algocraftsman/incident-management-microservices-platform/incidents-service`
- `ghcr.io/algocraftsman/incident-management-microservices-platform/alerts-service`
- `ghcr.io/algocraftsman/incident-management-microservices-platform/oncall-service`
- `ghcr.io/algocraftsman/incident-management-microservices-platform/status-page-service`

For every package, verify in its package settings that:

1. The package is connected to this source repository.
2. GitHub Actions access includes this repository, preferably through inherited
   repository permissions.
3. Visibility is **Public** for the current deployment design.
4. The package page shows immutable commit-SHA tags and the expected SBOM and
   provenance attestations after a successful `main` build.

Public visibility is an explicit current requirement, not a general rule for
all production systems. The Helm chart does not configure Kubernetes
`imagePullSecrets`, so a cluster cannot pull private GHCR images with the
checked-in deployment configuration. Moving packages to private visibility
requires a separate change that adds registry credentials to the cluster and
`imagePullSecrets` support to the chart before visibility changes.

## Enable Security Features

Review **Settings > Advanced Security** and the repository **Security** tab.
Enable controls where the repository visibility and GitHub plan make them
available.

| Feature | Baseline | Verification |
| --- | --- | --- |
| Dependency graph | Enabled | Dependency graph lists supported manifests from the default branch. |
| Dependabot alerts | Enabled | Security tab exposes dependency alerts. |
| Dependabot security updates | Enabled | Vulnerable dependencies can produce remediation pull requests. |
| Dependabot version updates | Enabled through `.github/dependabot.yml` | Insights > Dependency graph > Dependabot shows scheduled ecosystems. |
| Grouped security updates | Enable if grouping matches the repository's review policy | Confirm security update PRs still receive the full required-check set. |
| Code scanning | Enable CodeQL default setup for Python if available | A code-scanning analysis completes, then its stable check can be considered for branch protection. |
| Secret scanning | Enabled if available | Security tab exposes secret-scanning status and alerts. |
| Push protection | Enabled if available | Test only with GitHub's documented test patterns; never commit a real credential. |

Do not mark a code-scanning context as required until CodeQL has completed
successfully and the context name is stable. The repository's `pip-audit`,
Trivy, and Checkov gates remain required regardless of GitHub-hosted security
feature availability.

## Validate the Baseline

After applying or changing settings:

1. Open a documentation-only pull request and confirm direct merge is blocked
   until review and every required check complete.
2. Confirm force-push and branch deletion controls are active for `main`.
3. Dispatch `Deploy Helm Release` from `main` against `staging`; verify the job
   waits for any configured reviewer before it can read environment secrets.
4. Confirm a production deployment cannot be self-approved and only runs from
   `main`.
5. Verify all four GHCR packages can be pulled by the target cluster and that
   package access still includes this repository's workflows.
6. Review the Dependabot and code-scanning pages for configuration errors or
   stale analyses.
7. Save the review date and administrator in the team's operational evidence
   system or an issue linked to the next quarterly review.

## GitHub References

- [About protected branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)
- [Managing environments for deployment](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments)
- [Configuring package access and visibility](https://docs.github.com/en/packages/learn-github-packages/configuring-a-packages-access-control-and-visibility)
- [Managing repository security and analysis settings](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/enabling-features-for-your-repository/managing-security-and-analysis-settings-for-your-repository)
- [Configuring Dependabot security updates](https://docs.github.com/en/code-security/how-tos/secure-your-supply-chain/secure-your-dependencies/configure-security-updates)
- [Code scanning setup types](https://docs.github.com/en/code-security/concepts/code-scanning/setup-types)
