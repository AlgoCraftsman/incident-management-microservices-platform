# Kubernetes Manifests

This directory contains the Phase 3 Kubernetes deployment baseline.

The `base` kustomization deploys the four platform services, Redis, and one PostgreSQL instance per service into the `incident-platform` namespace.

```bash
kubectl apply -k infra/k8s/base
kubectl -n incident-platform get pods
```

The checked-in secrets use local development values that match Docker Compose. Replace them with external secret management before using these manifests outside a local cluster.

The base also includes ingress `NetworkPolicy` resources that allow service HTTP traffic inside the namespace, restrict each PostgreSQL instance to its owning service, and restrict Redis ingress to platform services. Egress remains open so optional notification providers and future observability integrations can be added without cluster-specific policy exceptions.

Images default to GHCR repositories under `ghcr.io/algocraftsman/incident-management-microservices-platform`. Override image tags during release promotion with:

```bash
kubectl set image deployment/incidents-service incidents-service=ghcr.io/algocraftsman/incident-management-microservices-platform/incidents-service:<sha> -n incident-platform
```

