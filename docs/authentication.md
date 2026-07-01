# Authentication

All service APIs except `/health` require `X-API-Key`.

Local development keeps using the simple free default:

```env
PLATFORM_API_KEYS=dev-platform-key
INTERNAL_API_KEY=dev-platform-key
```

Comma-separated keys are treated as legacy platform-wide keys and receive the `platform:*` scope. This keeps existing smoke tests and local Compose runs simple.

For a more production-shaped setup, `PLATFORM_API_KEYS` can also contain structured JSON:

```json
[
  {
    "name": "local-admin",
    "key": "dev-platform-key",
    "scopes": ["platform:*"]
  },
  {
    "name": "incidents-client",
    "key": "incident-client-key",
    "scopes": ["incidents-service:access"]
  },
  {
    "name": "service-to-service",
    "key": "service-internal-key",
    "scopes": ["incidents-service:access"]
  },
  {
    "name": "status-client",
    "key": "status-client-key",
    "scopes": ["status-page-service:*"]
  }
]
```

Supported scope patterns:

- `platform:*`: access to every service.
- `<service-name>:access`: access to one service.
- `<service-name>:*`: wildcard access to one service namespace.

Service-to-service calls still use `INTERNAL_API_KEY` for now. A later identity-provider phase can replace this with JWTs or workload identity without changing the protected route shape.

When using structured keys, include the `INTERNAL_API_KEY` value in `PLATFORM_API_KEYS` with the scopes needed by target services. Today, `alerts-service` and `oncall-service` call `incidents-service`, so the internal key needs `incidents-service:access` or `platform:*`.
