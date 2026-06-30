# API Contracts

The platform publishes checked-in OpenAPI contracts for every HTTP service:

- `docs/openapi/incidents-service.openapi.json`
- `docs/openapi/alerts-service.openapi.json`
- `docs/openapi/oncall-service.openapi.json`
- `docs/openapi/status-page-service.openapi.json`

These contracts are generated from each FastAPI application and describe the externally visible REST surface: paths, request bodies, response models, validation rules, tags, and schema components.

## Updating Contracts

Regenerate contracts after changing service routes or schemas:

```bash
python scripts/export_openapi.py
```

Verify checked-in contracts are current:

```bash
python scripts/export_openapi.py --check
```

CI runs the check so pull requests cannot accidentally change API behavior without updating the documented contract.

## Why OpenAPI Matters Here

OpenAPI is the machine-readable API contract between this platform's services and its clients. It lets reviewers inspect each service boundary quickly, gives future frontend or CLI clients a stable source for generated SDKs, and creates a clear diff when API behavior changes.
