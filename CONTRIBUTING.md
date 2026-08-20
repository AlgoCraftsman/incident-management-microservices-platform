# Contributing

Thank you for helping improve the incident management platform. Contributions
should preserve its production-shaped architecture, service ownership
boundaries, and security controls.

## Before You Start

- Keep each change focused and explain the operational reason for it.
- Open an issue before broad architectural changes or compatibility-breaking
  migrations so the approach can be agreed before implementation.
- Use descriptive, project-specific branch names and conventional commit
  messages.
- Never commit real credentials, production data, or local `.env` files. Add
  safe placeholders to `.env.example` when new configuration is required.

## Development Setup

Use Python 3.11 and Docker with Docker Compose. Create and activate a virtual
environment, then install the shared library, service requirements, and test
tools:

```bash
python -m venv .venv
python -m pip install --upgrade pip
python -m pip install -e libs/platform_common
python -m pip install -r services/incidents-service/requirements.txt
python -m pip install -r services/alerts-service/requirements.txt
python -m pip install -r services/oncall-service/requirements.txt
python -m pip install -r services/status-page-service/requirements.txt
python -m pip install pytest pytest-cov
```

See `README.md` for local containers, smoke tests, Kubernetes rendering, and
Helm commands.

## Validation

Run the checks relevant to your change. Every pull request should include at
least:

```bash
python -m pytest
python scripts/export_openapi.py --check
git diff --check
```

Changes to containers, workflows, or deployment manifests should also run the
corresponding image builds and security, Helm, Kubernetes, or policy checks
documented in `README.md` and `docs/build-plan.md`.

## Pull Requests

- Describe the behavior and operational impact of the change.
- Include validation evidence and call out any check that could not be run.
- Update tests, contracts, examples, and documentation when behavior changes.
- Keep vulnerability suppressions, weakened security gates, and unrelated
  dependency migrations out of routine changes.

Report security-sensitive findings through the process in `SECURITY.md`, not a
public issue or pull request.
