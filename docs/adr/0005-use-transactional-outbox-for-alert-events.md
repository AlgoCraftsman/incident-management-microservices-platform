# ADR 0005: Use Transactional Outbox for Alert Events

## Status

Accepted

## Context

`alerts-service` accepts Alertmanager webhooks, deduplicates alerts, may promote critical alerts into incidents, and publishes alert events. Publishing directly to Redis from the request path can make alert ingestion fail after the alert has already been stored if Redis is briefly unavailable.

## Decision

`alerts-service` writes `alert.received`, `alert.promoted_to_incident`, and `alert.suppressed` events to an `outbox_events` table in the same transaction as each alert state change. A background publisher drains pending rows to Redis Streams and records the published stream ID.

## Consequences

- Alert state changes and event intent are committed together.
- Alert ingestion is no longer coupled to immediate Redis availability for alert event publishing.
- Failed publishes remain queryable and retryable by the publisher loop.
- Alert and incident producers now use the same reliability pattern for Redis Stream events.
