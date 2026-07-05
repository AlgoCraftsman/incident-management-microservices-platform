# Incident Platform Helm Chart

This chart packages the incident management platform for local Kubernetes and future release automation.

Render the chart:

```bash
helm template incident-platform infra/helm/incident-platform --namespace incident-platform --create-namespace
```

Install into a local cluster:

```bash
helm upgrade --install incident-platform infra/helm/incident-platform \
  --namespace incident-platform \
  --create-namespace
```

Use production-oriented overrides:

```bash
helm template incident-platform infra/helm/incident-platform \
  --namespace incident-platform \
  -f infra/helm/incident-platform/values-prod.yaml
```

The default `values.yaml` keeps the project free to run locally by using in-cluster PostgreSQL, Redis, and mock/local secrets. Replace `values-prod.yaml` placeholders with real secret management and immutable image tags before using the chart outside a local cluster.

