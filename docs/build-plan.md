# Build Plan and Delivery Status

The repository has completed the first four delivery phases for a
production-shaped engineering baseline. In this plan, **complete** means the
agreed repository scope is implemented and validated; it does not mean the
platform is ready to carry production traffic without the gap work below.

## Phase Status

| Phase | Status | Delivered outcome |
| --- | --- | --- |
| 1. Incident lifecycle foundation | Complete | Alert ingestion and deduplication, incident promotion and lifecycle history, transactional outboxes, Redis Stream events, service-owned PostgreSQL schemas, and an end-to-end smoke test. |
| 2. On-call and stakeholder workflow | Complete | On-call schedules, notification attempts and delivery adapters, status-page updates, durable and idempotent event consumers, scoped API-key authentication, readiness and metrics endpoints, and OpenAPI contracts. |
| 3. Kubernetes delivery baseline | Complete | Kustomize manifests, a reusable Helm chart, probes, resource requests and limits, rolling updates, HPAs, persistent volumes, hardened application security contexts, ingress network policies, and a validated local kind deployment path. |
| 4. CI/CD and supply-chain hardening | Complete | CI and dependency gates, Helm and Kubernetes validation, IaC and image scanning, GHCR release images, attestations, environment-gated Helm deployment, dependency automation, workflow hardening, and an administrator operations runbook. |

## Phase 4 Completed Scope

### Pull Request and Main-Branch Validation

- Service and shared-library tests run as separate, bounded jobs.
- Committed OpenAPI contracts are checked for drift.
- Every service image is built, and each image is scanned with Trivy for high
  and critical vulnerabilities with fixed versions available.
- Dockerfiles are scanned with Checkov.
- Kustomize and default/production Helm variants are rendered, checked with
  kubeconform, and evaluated against targeted Checkov Kubernetes policies.
- Python service requirements are audited with a pinned `pip-audit` toolchain.

### Release Artifacts and Deployment

- Pushes to `main` publish all four service images to GHCR with an immutable
  commit-SHA tag and a default-branch `latest` tag.
- Release builds publish SBOM and provenance attestations.
- A manually dispatched workflow deploys one verified SHA across every service
  through the Helm chart.
- Deployment inputs and required secrets are validated before cluster access.
- The workflow checks that every service image exists, uses environment-scoped
  secrets, hides Kubernetes Secret output during the dry-run, stores temporary
  secret files outside the workspace, and cleans those files on success or
  failure.
- Helm waits for the release and the workflow verifies every application
  rollout before reporting success.

### Workflow and Dependency Hardening

- Workflow tokens default to read-only access; only the image publishing job
  receives `packages: write`.
- CI, dependency audit, and deployment jobs have explicit timeouts.
- Validation workflows cancel superseded runs for the same ref; deployments
  remain serialized per environment without cancelling an active release.
- Dependabot monitors GitHub Actions, service and infrastructure images, Docker
  Compose, Python services, shared code, and security tooling.
- Routine dependency groups are limited to minor and patch updates. Runtime,
  datastore, base-image, and workflow major upgrades are planned migrations.
- GitHub branch rules, required checks, deployment reviewers, GHCR access, and
  security-feature settings are specified in the operations runbook.

## Phase 4 Closeout Validation

The closeout review on 2026-07-14 produced the following local evidence from the
merged `main` baseline:

| Check | Result |
| --- | --- |
| `.venv/Scripts/python.exe -m pytest` | Passed: 34 tests. |
| `.venv/Scripts/python.exe scripts/export_openapi.py --check` | Passed: committed contracts match the applications. |
| `kubectl kustomize infra/k8s/base` | Passed: the Kubernetes base renders successfully. |
| `docker compose config --quiet` | Passed: the Compose model is valid. |
| `git diff --check` | Passed: no whitespace errors. |

Helm is not installed in the closeout workstation environment. Helm lint,
default and production rendering, kubeconform, Checkov, service image builds,
and Trivy therefore remain CI-backed checks rather than locally repeated
closeout checks. The closeout pull request must pass the full check set
designated in `docs/github-operations-runbook.md` before merge.

## Known Production Gaps

These items are deliberately visible so the current baseline is not
misrepresented as production-ready.

| Priority | Gap in the current baseline | Production exit criteria |
| --- | --- | --- |
| Before production | PostgreSQL and Redis are single-instance in-cluster StatefulSets. There is no automated backup, restore, replication, multi-zone placement, or disaster-recovery test. | Select managed services or production operators; define RPO/RTO; enable encrypted backups and high availability; complete and record a restore/failover exercise. |
| Before production | The chart exposes only internal services and does not provide ingress, DNS, or TLS lifecycle management. | Add the approved ingress or gateway, certificate automation, DNS, external access policy, rate limiting, and end-to-end TLS validation. |
| Before production | Application startup runs Alembic migrations, which can race across replicas and couples schema changes to rollout. | Add a single controlled migration job with backward-compatible migration policy, preflight checks, failure handling, and rollback guidance. |
| Before production | Kubernetes Secrets receive values from GitHub environment secrets, but there is no external secret manager, workload identity, or automated rotation. Shared API keys remain the primary identity model. | Integrate a managed secret store and workload identity; define rotation and revocation; replace shared keys with an identity provider and scoped service/user authorization. |
| Before production | The current chart has no `imagePullSecrets`; deployment therefore relies on public GHCR packages. Attestations are published but not verified before admission. | Choose a registry access model, add authenticated image pulls when private artifacts are required, pin images by digest, and enforce signature/provenance policy at deployment or admission. |
| High | Cluster, network, identity, DNS, and storage infrastructure are not provisioned as code. Deployment assumes an existing cluster and a long-lived kubeconfig secret. | Provision isolated environments with reviewed infrastructure as code, short-lived federated credentials, remote state controls, policy checks, and drift detection. |
| High | Metrics endpoints exist, but no in-repository metrics collection, dashboards, centralized logs, tracing, alert rules, SLOs, or synthetic checks are deployed. | Operate an observability stack; define service and end-to-end SLIs/SLOs; alert on user-impacting symptoms; validate dashboards and paging routes. |
| High | NetworkPolicy restricts ingress but intentionally leaves egress open. Stateful containers use upstream security defaults, and there is no Pod Security Admission or dedicated Kubernetes RBAC model. | Add namespace pod-security policy, least-privilege service accounts/RBAC, explicit egress policy with required destinations, and validated database/Redis runtime hardening. |
| High | The current CI does not continuously deploy to kind, run end-to-end smoke tests against Kubernetes, perform DAST, load tests, or resilience tests. | Add an ephemeral-cluster integration gate and scheduled security, capacity, and failure-mode testing with owned thresholds. |
| High | Release deployment is a manual rolling Helm upgrade. There is no canary/blue-green policy, automatic rollback signal, PodDisruptionBudget, topology spread, or capacity validation. | Define progressive delivery and rollback criteria; add disruption and placement controls; validate scaling, failure recovery, and zero-downtime behavior. |
| High | GitHub rules, environment reviewers, package access, CodeQL, secret scanning, and push protection are host settings rather than repository-enforced state. | Apply and periodically audit `docs/github-operations-runbook.md`; retain evidence and track any plan-dependent unavailable control. |
| Medium | Workflow actions use version tags rather than immutable commit SHAs, and Ruff/detect-secrets are local pre-commit hooks rather than required CI jobs. | Pin third-party actions to reviewed commit SHAs with update automation, and decide which lint and secret checks must become required server-side gates. |
| Medium | Operational policies for data retention, privacy, incident recovery, capacity, cost, and support ownership are not defined. | Assign service ownership and escalation; approve retention and privacy controls; publish operational and disaster-recovery runbooks; establish capacity and cost reviews. |

## Recommended Next Milestone

Prioritize production-readiness work in this order:

1. Apply and verify the GitHub-hosted controls in the operations runbook.
2. Establish the production data, backup, recovery, secret, and identity model.
3. Add controlled migrations plus ingress, TLS, and registry policy.
4. Deploy observability and define SLOs and operational ownership.
5. Add ephemeral-cluster, security, capacity, and resilience validation.
6. Introduce progressive delivery and complete a documented recovery exercise.

Related documents:

- `docs/github-operations-runbook.md`
- `docs/release-deployment.md`
- `docs/supply-chain-security.md`
- `infra/helm/incident-platform/README.md`
- `infra/k8s/README.md`
