# ADR 0001: Use Redis Streams for Platform Events

## Status

Accepted

## Context

The original build plan used Redis pub/sub for incident and status-page integration. Pub/sub is simple, but subscribers miss messages when they are offline. Incident workflows need replayable events for reliability, local debugging, and future consumers such as notifications and status updates.

## Decision

Use Redis Streams as the first event transport. Services publish versioned event envelopes to a shared stream named by `EVENT_STREAM_NAME`.

## Consequences

- Consumers can resume from stream IDs and avoid losing events during restarts.
- Local development remains free and lightweight.
- Future work can introduce consumer groups, dead-letter streams, and replay tooling without changing event contracts.
- Kafka or NATS can still replace Redis Streams later if the platform needs stronger ordering, partitions, or larger-scale retention.

