# ADR 0003: API Keys Now, RBAC Later

## Status

Accepted

## Context

The first build phase needs protected APIs without introducing a full identity provider. Leaving mutating endpoints unauthenticated would make the project less credible and would hide important API design concerns.

## Decision

Require `X-API-Key` for all non-public endpoints. Health endpoints remain public. Service-to-service calls use `INTERNAL_API_KEY`.

## Consequences

- The platform demonstrates secure-by-default API shape early.
- Local development stays simple.
- Future phases can add JWT auth, user roles, audit actors, and object-level authorization while keeping the dependency boundary intact.

