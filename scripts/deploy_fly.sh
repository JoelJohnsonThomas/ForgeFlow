#!/usr/bin/env bash
# Deploy ForgeFlow's 3 services to Fly.io in the right order.
#
# Prereqs:
#   - fly CLI installed + authenticated (`fly auth login`)
#   - The 3 apps already created (see fly/*.toml headers for one-time setup)
#   - Secrets already set per fly/*.toml comments
#   - Postgres provisioned + attached to forgeflow-api
#
# Run:
#   bash scripts/deploy_fly.sh

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "==> Deploying MCP tool server (forgeflow-mcp)"
fly deploy -a forgeflow-mcp -c fly/mcp.toml --remote-only

echo "==> Deploying API (forgeflow-api) — runs alembic migrations as release_command"
fly deploy -a forgeflow-api -c fly/api.toml --remote-only

echo "==> Deploying frontend console (forgeflow-console)"
fly deploy -a forgeflow-console -c fly/frontend.toml --remote-only

echo
echo "Done. Health-check the deployment:"
echo "  fly status -a forgeflow-api"
echo "  curl https://forgeflow-console.fly.dev/api/health"
echo
echo "Console URL:"
echo "  fly info -a forgeflow-console --json | jq -r '.Hostname' | awk '{print \"https://\" \$0}'"
