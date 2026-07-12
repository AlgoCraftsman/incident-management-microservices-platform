# Release Deployment

CI publishes each service image to GitHub Container Registry on pushes to `main`.
Images are tagged with the immutable commit SHA and `latest`. Promote a
release by deploying the same commit SHA across all services with the Helm
chart.

## GitHub Actions Deployment

Use the `Deploy Helm Release` workflow for environment-gated deployments. Run it
from the Actions tab after the target commit has completed CI on `main`.

Required GitHub environment secrets:

| Secret | Purpose |
| --- | --- |
| `KUBE_CONFIG_B64` | Base64-encoded kubeconfig for the target cluster context. |
| `PLATFORM_API_KEYS` | Comma-separated API keys accepted by public service APIs. |
| `INTERNAL_API_KEY` | Shared service-to-service API key. |
| `INCIDENTS_DB_PASSWORD` | PostgreSQL password for `incidents-service`. |
| `ALERTS_DB_PASSWORD` | PostgreSQL password for `alerts-service`. |
| `ONCALL_DB_PASSWORD` | PostgreSQL password for `oncall-service`. |
| `STATUS_PAGE_DB_PASSWORD` | PostgreSQL password for `status-page-service`. |

Workflow inputs:

| Input | Default | Notes |
| --- | --- | --- |
| `environment` | `production` | Must match a GitHub environment with the required secrets. |
| `image_sha` | Workflow commit SHA | Use the merged `main` commit SHA that published the GHCR images. |
| `namespace` | `incident-platform` | Kubernetes namespace for the release. |
| `release_name` | `incident-platform` | Helm release name. |
| `timeout` | `10m` | Helm wait timeout. |

The workflow fails before deployment if required secrets are missing, the image
tag is not a 40-character lowercase commit SHA, or any service image is missing
from GHCR.

Before deploying, the workflow runs a client-side Helm dry-run with
`--hide-secret`. The sanitized dry-run output is written under the runner
temporary directory instead of the repository workspace so rendered Kubernetes
Secret values are not retained as workspace files.

Helm secret override files are created under the runner temporary directory,
used for dry-run and deployment commands, and removed in a final cleanup step
that runs even when deployment fails.

## Manual Deployment

For an operator workstation with cluster access and Helm installed:

```bash
export RELEASE_SHA=<git-sha>
export NAMESPACE=incident-platform

helm upgrade --install incident-platform infra/helm/incident-platform \
  --namespace "$NAMESPACE" \
  --create-namespace \
  --wait \
  --timeout 10m \
  -f infra/helm/incident-platform/values-prod.yaml \
  --set-string global.imageTag="$RELEASE_SHA" \
  --set-file secrets.platformApiKeys=./secrets/platform_api_keys \
  --set-file secrets.internalApiKey=./secrets/internal_api_key \
  --set-file databases.incidents.password=./secrets/incidents_db_password \
  --set-file databases.alerts.password=./secrets/alerts_db_password \
  --set-file databases.oncall.password=./secrets/oncall_db_password \
  --set-file databases.statusPage.password=./secrets/status_page_db_password
```

Keep the secret files out of version control. Use `--set-file` rather than
`--set-string` for API keys because `PLATFORM_API_KEYS` can contain
comma-separated values.

## Verification

After deployment:

```bash
kubectl -n incident-platform rollout status deployment/incidents-service
kubectl -n incident-platform rollout status deployment/alerts-service
kubectl -n incident-platform rollout status deployment/oncall-service
kubectl -n incident-platform rollout status deployment/status-page-service
kubectl -n incident-platform get deployments,statefulsets,pods
```

Confirm the expected image tag is running:

```bash
kubectl -n incident-platform get deployment incidents-service \
  -o jsonpath='{.spec.template.spec.containers[0].image}'
```

## Rollback

Roll back to the previous Helm revision:

```bash
helm -n incident-platform history incident-platform
helm -n incident-platform rollback incident-platform <revision> --wait --timeout 10m
```

Prefer rolling forward to a known-good commit SHA when possible so image provenance stays explicit.
