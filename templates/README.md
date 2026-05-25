# ForgeFlow Workflow Template Marketplace

Templates are self-describing workflow packages with a `manifest.yaml`
at the root. The registry walks `templates/builtin/` and
`templates/community/` at startup and exposes results through the API
(`GET /marketplace/templates`) and the dashboard (page 6).

## Manifest schema

```yaml
name: my_workflow             # required, lowercase + underscores
version: "1.0.0"              # required, semver
description: |                # required
  One- or two-sentence summary that shows up in the marketplace list.
domain: sales_ops             # required: sales_ops | support_ops | finance_recon | custom
author: Your Name             # optional
homepage: https://...         # optional
license: Apache-2.0           # optional, defaults to Apache-2.0
tags: [sales, crm]            # optional, free-form
stages: [qualify, research]   # optional, drives the dashboard timeline rendering
input_schema:                 # optional, advisory for callers; not enforced today
  company_name: { type: string, required: true }
requires_connectors: [search, email]   # optional; install fails-soft if missing
requires_extras: [ollama]              # optional; pip extras the template uses
```

## Built-in templates

| Name | Domain | Description |
|------|--------|-------------|
| `sales_ops` | sales_ops | Lead qualification + research + scoring + proposal + CRM |
| `support_ops` | support_ops | Ticket triage + investigation + response + escalation |
| `finance_recon` | finance_recon | Two-ledger reconciliation with variance flagging |

## Contributing a community template

1. Fork the repo (or vendor templates into your own).
2. Create `templates/community/<your-template>/manifest.yaml` with the
   schema above.
3. Implement the workflow as a Python package under
   `forgeflow/workflows/<your-template>/` mirroring the layout of
   `sales_ops/` (models.py, prompts.py, stages.py, pipeline.py).
4. Open a PR. The CI lint job validates that every manifest passes the
   `TemplateManifest.from_dict` schema check.

## API

```bash
# List everything
curl http://localhost:8000/marketplace/templates

# Filter by domain
curl 'http://localhost:8000/marketplace/templates?domain=sales_ops'

# Detail
curl http://localhost:8000/marketplace/templates/sales_ops
```

## CLI

```bash
# List
python scripts/marketplace.py list

# Show one
python scripts/marketplace.py show sales_ops

# Validate a manifest before opening a PR
python scripts/marketplace.py validate ./templates/community/my_workflow/manifest.yaml
```
