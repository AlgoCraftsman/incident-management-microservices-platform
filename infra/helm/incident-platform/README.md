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

Validate against a local kind cluster:

```bash
docker build -f services/incidents-service/Dockerfile -t ghcr.io/algocraftsman/incident-management-microservices-platform/incidents-service:latest .
docker build -f services/alerts-service/Dockerfile -t ghcr.io/algocraftsman/incident-management-microservices-platform/alerts-service:latest .
docker build -f services/oncall-service/Dockerfile -t ghcr.io/algocraftsman/incident-management-microservices-platform/oncall-service:latest .
docker build -f services/status-page-service/Dockerfile -t ghcr.io/algocraftsman/incident-management-microservices-platform/status-page-service:latest .

kind load docker-image \
  ghcr.io/algocraftsman/incident-management-microservices-platform/incidents-service:latest \
  ghcr.io/algocraftsman/incident-management-microservices-platform/alerts-service:latest \
  ghcr.io/algocraftsman/incident-management-microservices-platform/oncall-service:latest \
  ghcr.io/algocraftsman/incident-management-microservices-platform/status-page-service:latest \
  --name incident-platform

helm upgrade --install incident-platform infra/helm/incident-platform \
  --namespace incident-platform \
  --create-namespace \
  --wait \
  --timeout 5m
```

Use production-oriented overrides:

```bash
helm template incident-platform infra/helm/incident-platform \
  --namespace incident-platform \
  -f infra/helm/incident-platform/values-prod.yaml
```

The default `values.yaml` keeps the project free to run locally by using in-cluster PostgreSQL, Redis, and mock/local secrets. Replace `values-prod.yaml` placeholders with real secret management and immutable image tags before using the chart outside a local cluster.

PostgreSQL and Redis run with their upstream image defaults so they can initialize and own mounted data directories correctly. The application containers still run as non-root with privilege escalation disabled.

Network policies are enabled by default. They allow HTTP traffic between platform services, restrict each PostgreSQL instance to its owning service, and restrict Redis ingress to platform services.
