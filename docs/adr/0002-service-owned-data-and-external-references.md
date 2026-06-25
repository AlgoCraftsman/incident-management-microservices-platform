# ADR 0002: Service-Owned Data and External References

## Status

Accepted

## Context

The platform uses separate databases per service. The initial plan included fields such as `incident_id` in the alerts service. A real database foreign key across service-owned databases would couple deployment, migrations, and availability.

## Decision

Each service owns its schema. IDs from other services are stored as external references and validated through API or event contracts, not database foreign keys.

## Consequences

- Services can evolve schemas independently.
- Cross-service consistency is eventual and handled through idempotent APIs and events.
- Tests must cover behavior at service boundaries instead of relying on shared database constraints.

