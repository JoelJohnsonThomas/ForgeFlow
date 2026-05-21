# ForgeFlow Helm Chart

Templated Kubernetes deployment for ForgeFlow. Equivalent to the manifests
in [`../../k8s/`](../../k8s/) but parameterized, with helm hooks for
schema migration and per-environment value overrides.

## Install

```bash
# Add namespace + dry-run to verify the rendered manifests
kubectl create namespace forgeflow
helm install ff ./helm/forgeflow -n forgeflow --dry-run --debug

# Real install — edit values.yaml first or override on the CLI
helm install ff ./helm/forgeflow -n forgeflow \
  --set image.tag=0.1.0 \
  --set secrets.values.OPENAI_API_KEY=sk-...
```

## Upgrade

```bash
helm upgrade ff ./helm/forgeflow -n forgeflow -f my-values.yaml
```

The `migrate` job runs as a `pre-upgrade` hook, so alembic catches any
new revisions before the new pods roll out.

## Values

See [`values.yaml`](values.yaml) for the full set with comments. Key
sections:

- `image.*` — registry + tag (override per environment)
- `config.*` — non-secret runtime configuration (ConfigMap)
- `secrets.values` — inline secret values for dev. For production set
  `secrets.existingSecret: my-external-secret-name` instead.
- `postgres.enabled` — set to `false` when using managed RDS / Cloud SQL
- `api.autoscaling.*`, `mcp.autoscaling.*` — HPA tuning
- `ingress.*` — host names + TLS
- `networkPolicy.enabled` — set to `false` on clusters without a CNI
  that enforces NetworkPolicy

## Production checklist

- [ ] `image.tag` pinned to a specific version (not `latest`)
- [ ] `secrets.existingSecret` references an external secret store
- [ ] `postgres.enabled: false` + managed-DB connection string in
      `config.postgresUrl` / `config.postgresSyncUrl`
- [ ] `ingress.tls.enabled: true` and cert-manager wired up
- [ ] `networkPolicy.enabled: true` and the cluster's CNI enforces them
- [ ] `image.pullSecrets` configured if your registry isn't public
- [ ] `nodeSelector` / `tolerations` / `affinity` set to your node pool
- [ ] Resource requests + limits tuned to your workload (defaults are
      conservative for dev clusters)

## Uninstall

```bash
helm uninstall ff -n forgeflow

# Persistent volumes survive uninstall — delete the PVC if you want
# the database wiped:
kubectl -n forgeflow delete pvc -l app.kubernetes.io/component=postgres
```
