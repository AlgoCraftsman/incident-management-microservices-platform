# Kubernetes Manifests

This directory contains the Phase 3 Kubernetes deployment baseline.

The `base` kustomization deploys the four platform services, Redis, and one PostgreSQL instance per service into the `incident-platform` namespace.

```bash
kubectl apply -k infra/k8s/base
kubectl -n incident-platform get pods
```

The checked-in secrets use local development values that match Docker Compose. Replace them with external secret management before using these manifests outside a local cluster.

Images default to GHCR repositories under `ghcr.io/algocraftsman/incident-management-microservices-platform`. Override image tags during release promotion with:

```bash
kubectl set image deployment/incidents-service incidents-service=ghcr.io/algocraftsman/incident-management-microservices-platform/incidents-service:<sha> -n incident-platform
```

