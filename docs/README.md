# ForgeFlow Documentation

Start at the [project README](../README.md) for the overview and quickstart. This
index links the deeper guides by what you're trying to do.

## Getting started
- [Quickstart](../README.md#-quickstart) — clone, configure, run the stack, first workflow
- [Troubleshooting](troubleshooting.md) — 401s, port conflicts, slow startup, and other first-run issues
- [Configuration reference](configuration.md) — every environment variable, with defaults

## Using ForgeFlow
- [Examples](examples.md) — runnable patterns: API, programmatic, streaming, custom connectors/templates
- [API reference](api-reference.md) — endpoints, auth requirements, roles, error semantics
- [Connector setup](connectors.md) — HubSpot, Salesforce, Jira, ServiceNow, GitHub, SAP, QuickBooks, MS Graph
- [Sales-ops production runbook](sales-ops-production.md) — a real HubSpot pipeline on Fly.io

## Architecture & internals
- [Architecture](architecture.md) — components, request lifecycle, workflow execution, auth flow (Mermaid diagrams)
- [Database](database.md) — schema, ER diagram, tables, migrations, indexes
- [Testing](testing.md) — running + writing tests, the DB-integration pattern, coverage

## Security & auth
- [Authentication & authorization](auth.md) — tokens, refresh rotation, MFA, OIDC, RBAC
- [Security policy](../SECURITY.md) — supported versions, vulnerability reporting, hardening checklist
- [Security audit / threat model](../SECURITY_AUDIT.md) — findings and their status

## Operating in production
- [Backup & disaster recovery](operations/backup-dr.md) — backup, restore, RPO/RTO, DR runbook
- [Deployment targets](../README.md#-deployment) — Compose, Kubernetes, Helm, Terraform (AWS), Fly.io
- [Air-gapped deployment](deployment/AIRGAPPED.md) — offline bundle builder

## Contributing
- [CONTRIBUTING.md](../CONTRIBUTING.md) — dev setup, standards, PR process
- [Code of Conduct](../CODE_OF_CONDUCT.md) · [Community](../COMMUNITY.md) · [Changelog](../CHANGELOG.md) · [Roadmap](../ROADMAP.md)

## Reference index

| Doc | What it covers |
|---|---|
| [architecture.md](architecture.md) | System design + Mermaid diagrams |
| [database.md](database.md) | Schema, ER diagram, migrations |
| [configuration.md](configuration.md) | All env vars |
| [api-reference.md](api-reference.md) | REST endpoints |
| [connectors.md](connectors.md) | Enterprise connector credentials |
| [auth.md](auth.md) | Auth model |
| [examples.md](examples.md) | Runnable code patterns |
| [testing.md](testing.md) | Test suite + writing tests |
| [troubleshooting.md](troubleshooting.md) | Common failures |
| [operations/backup-dr.md](operations/backup-dr.md) | Backup & DR |
| [deployment/AIRGAPPED.md](deployment/AIRGAPPED.md) | Offline install |
| [sales-ops-production.md](sales-ops-production.md) | Production runbook |
