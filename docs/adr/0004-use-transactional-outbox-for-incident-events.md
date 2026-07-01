# ADR 0004: Use Transactional Outbox for Incident Events

## Status

Accepted

## Context

Incident events drive on-call notifications and status-page updates. If an incident mutation commits successfully but Redis is temporarily unavailable, publishing directly from the request handler can lose the event that downstream services need.

## Decision

`incidents-service` writes incident lifecycle events to an `outbox_events` table in the same transaction as the incident state change. A background publisher drains pending outbox rows to Redis Streams and marks each event as published with its stream ID.

## Consequences

- Incident state changes and event intent are committed atomically.
- Redis outages no longer make incident write requests fail solely because event publishing is unavailable.
- Failed publishes remain visible in the database and can be retried by the publisher loop.
- Downstream consumers continue to receive the same versioned event envelope.
