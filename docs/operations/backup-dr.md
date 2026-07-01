# Backup & Disaster Recovery

## What holds state

**PostgreSQL is the single source of truth.** Everything durable lives there:

- LangGraph checkpoints (workflow run state — any worker resumes any `thread_id`)
- `workflow_runs`, `approval_requests`, `agent_traces`
- `memory_vectors` / `agent_knowledge` (pgvector)
- `auth_users`, `auth_refresh_tokens`, `workspaces`, `audit_log`

Everything else is **stateless and reproducible**:

| Component | Recovery |
|---|---|
| API / MCP / console | Redeploy from container images |
| Secrets | Restore from your secrets manager (never from a backup of `.env`) |
| Schema | `alembic upgrade head` (idempotent) |

So a complete backup strategy is essentially: **back up the database, and store
your secrets and image tags somewhere durable.**

## Backups

### Docker Compose (single host)
The DB lives in the named volume `forgeflow_pgdata`. Take logical dumps on a
schedule:
```bash
# Logical backup (portable across PG versions)
docker compose exec -T postgres pg_dump -U forgeflow -d forgeflow -Fc \
  > forgeflow-$(date +%F).dump
```
Store the dump off-host (S3/GCS/Azure Blob) with lifecycle retention. For a
crash-consistent physical copy, stop the DB and snapshot the volume.

### Managed Postgres (RDS / Cloud SQL / Azure Flexible Server) — recommended for prod
- Enable **automated backups** and **point-in-time recovery (PITR)** via WAL
  archiving.
- Enable cross-region snapshot copy for regional-outage protection.
- The Terraform AWS module provisions RDS PG16; enable `backup_retention_period`
  and `copy_tags_to_snapshot`.

## Restore

```bash
# 1. Bring up a fresh Postgres (empty)
docker compose up -d postgres

# 2. Restore the logical dump
docker compose exec -T postgres pg_restore -U forgeflow -d forgeflow --clean --if-exists \
  < forgeflow-YYYY-MM-DD.dump

# 3. Apply any migrations newer than the dump (idempotent)
docker compose --profile migration run --rm migrate

# 4. Start the app
docker compose up -d
```
For managed DBs, restore the snapshot / PITR to a new instance, point
`POSTGRES_URL`/`POSTGRES_SYNC_URL` at it, then run step 3.

## Targets (set your own SLOs)

| Metric | Compose (dumps) | Managed + PITR |
|---|---|---|
| **RPO** (max data loss) | your dump interval (e.g. 24h) | seconds–minutes (WAL) |
| **RTO** (time to restore) | minutes (dump size dependent) | minutes (snapshot restore) |

## Disaster recovery runbook

1. **Provision** a new Postgres (managed snapshot restore or a fresh instance +
   logical restore).
2. **Point** the app at it via `POSTGRES_URL` / `POSTGRES_SYNC_URL` (from your
   secrets manager).
3. **Migrate**: `alembic upgrade head` (safe to re-run).
4. **Redeploy** API / MCP / console from pinned image tags (K8s/Helm/Compose).
5. **Rotate secrets** if the incident may have exposed them (`API_SECRET_KEY`
   rotation invalidates all existing JWTs — expected).
6. **Verify**: `GET /health` → `database: connected, graph: compiled`; run a
   `dry_run` workflow; confirm a pending approval resumes.

## Test your restores

A backup you haven't restored is a hypothesis. Periodically restore the latest
dump into a scratch database and run the smoke check in step 6. Automate it in
CI where possible.

## Notes

- **Secrets are not in the DB backup.** Keep `API_SECRET_KEY` and provider keys
  in a secrets manager; losing `API_SECRET_KEY` logs everyone out (JWTs can't be
  verified) but does not corrupt data.
- **In-flight runs survive** a crash because state is checkpointed per node — a
  restored DB resumes runs from their last checkpoint.
