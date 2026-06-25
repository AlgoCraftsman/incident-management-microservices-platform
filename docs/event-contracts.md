# Event Contracts

All platform events use a versioned envelope.

```json
{
  "event_id": "uuid",
  "event_type": "incident.created",
  "event_version": 1,
  "occurred_at": "2026-06-24T20:00:00Z",
  "producer": "incidents-service",
  "correlation_id": "request-correlation-id",
  "idempotency_key": "optional-client-key",
  "payload": {}
}
```

## Current Events

| Event | Producer | Purpose |
| --- | --- | --- |
| `incident.created` | `incidents-service` | New incident opened. |
| `incident.updated` | `incidents-service` | Incident mutable fields changed. |
| `incident.acknowledged` | `incidents-service` | Incident entered acknowledged state. |
| `incident.resolved` | `incidents-service` | Incident entered resolved state. |
| `incident.closed` | `incidents-service` | Incident entered closed state. |
| `alert.received` | `alerts-service` | Raw alert accepted or deduplicated. |
| `alert.promoted_to_incident` | `alerts-service` | Alert routing created or linked an incident. |
| `alert.suppressed` | `alerts-service` | Alert was temporarily suppressed. |

## Compatibility Rules

- `event_type` and `event_version` are required.
- New optional payload fields are backward compatible.
- Removing or renaming payload fields requires a new `event_version`.
- Consumers must ignore unknown payload fields.
- Producers must include `correlation_id` for traceability across services.

