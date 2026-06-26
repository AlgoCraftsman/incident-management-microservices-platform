# Incident Management Microservices Platform

Production-shaped incident management platform for practicing SRE, DevOps, and cloud-native engineering patterns.

The first build slice implements the incident lifecycle foundation:

- `incidents-service`: owns incident state, timeline history, lifecycle transitions, and incident events.
- `alerts-service`: ingests Alertmanager-style webhooks, deduplicates raw alerts, and promotes eligible alerts into incidents.
- `platform-common`: shared operational primitives for correlation IDs, API-key auth, event envelopes, Redis Streams publishing, and logging.

## Architecture Principles

- Services own their data stores. Cross-service IDs are external references, not database foreign keys.
- Events use durable Redis Streams rather than fire-and-forget pub/sub.
- APIs are protected by service API keys by default, with explicit public health endpoints.
- Every request gets a correlation ID propagated through logs, responses, and events.
- Mutating APIs support idempotency where duplicate client retries are expected.
- Runtime configuration is environment driven and safe to run locally with Docker Compose.

## Local Run

```bash
cp .env.example .env
docker compose up --build
```

Service URLs:

- Incidents API: `http://localhost:8001`
- Alerts API: `http://localhost:8002`
- Redis: `localhost:6379`
- PostgreSQL incidents DB: `localhost:5433`
- PostgreSQL alerts DB: `localhost:5434`

Default local API key:

```text
dev-platform-key
```

Example critical alert:

```bash
curl -X POST http://localhost:8002/alerts/webhook \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-platform-key" \
  -H "Idempotency-Key: demo-critical-alert-1" \
  -d @docs/examples/critical-alertmanager-payload.json
```

Run the Phase 1 smoke test after the stack is healthy:

```bash
python scripts/phase1_smoke_test.py
```

The smoke test posts a critical Prometheus-style alert, verifies alert deduplication, confirms incident promotion, resolves the incident, and checks timeline history.

## Database Migrations

Each service owns its database schema and ships its own Alembic migrations:

- `services/incidents-service/alembic`
- `services/alerts-service/alembic`

The local containers run migrations on startup. For production, use the same migrations from a deployment job before rolling application replicas.

## Project Layout

```text
.
|-- docs/
|   |-- adr/
|   |-- examples/
|   `-- event-contracts.md
|-- libs/
|   `-- platform_common/
|-- scripts/
|   `-- phase1_smoke_test.py
|-- services/
|   |-- alerts-service/
|   `-- incidents-service/
|-- .github/workflows/
`-- docker-compose.yml
```

## Verification Targets

The Phase 1 target is:

1. `docker compose up --build` starts both APIs, their databases, and Redis.
2. A critical Prometheus alert posted to `alerts-service` creates exactly one alert and one P1 incident.
3. Reposting the same alert fingerprint updates the existing alert instead of creating a duplicate.
4. Incident state transitions append immutable timeline records.
5. Events are written to Redis Streams using versioned envelopes with correlation IDs.

Useful local checks:

```bash
pytest
docker compose up --build
python scripts/phase1_smoke_test.py
```
