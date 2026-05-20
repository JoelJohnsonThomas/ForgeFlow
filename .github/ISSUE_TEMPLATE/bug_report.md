---
name: Bug report
about: Report a defect in ForgeFlow
title: "[BUG] "
labels: bug
assignees: ''
---

## What happened

A clear, concise description of the bug.

## Expected behavior

What you expected to happen instead.

## Reproduction

Minimal steps to reproduce. Include lead data, env vars, and the exact command:

```bash
# Example
docker compose up -d
curl -X POST localhost:8000/workflows/run \
  -H "Content-Type: application/json" \
  -d '{"workflow_type": "sales_ops", "lead_data": {"company_name": "Acme Corp"}}'
```

## Stack trace / logs

If applicable, paste the full stack trace inside a fenced code block.

```
<paste here>
```

## Environment

- ForgeFlow version / commit: `git rev-parse HEAD`
- Python version: `python --version`
- OS:
- Docker version (if applicable):
- LLM provider (openai / ollama / anthropic):

## Additional context

Anything else that might help — screenshots, links to related issues, recent config changes.
