# ForgeFlow Kubernetes Manifests

Plain-YAML deployment for any conformant Kubernetes cluster (EKS, GKE, AKS,
Rancher, OpenShift, k3s). For templated/parameterized deployment see the
Helm chart in [`../helm/forgeflow`](../helm/forgeflow).

## Topology

| Workload | Kind | Replicas | Why |
|----------|------|----------|-----|
| `forgeflow-postgres` | StatefulSet | 1 | pgvector-extended PG16; persistent volume |
| `forgeflow-mcp` | Deployment | 1 (auto-scales 1→5) | Tool server; HPA on CPU |
| `forgeflow-api` | Deployment | 2 (auto-scales 2→10) | Stateless FastAPI; HPA on CPU |
| `forgeflow-dashboard` | Deployment | 1 | Streamlit; not auto-scaled |
| `forgeflow-migrate` | Job | run-once | Alembic schema upgrade |

## Quickstart

```bash
# 1. Build + push the images (replace registry with your own)
docker build --target api       -t my-registry/forgeflow-api:0.1.0       .
docker build --target mcp       -t my-registry/forgeflow-mcp:0.1.0       .
docker build --target dashboard -t my-registry/forgeflow-dashboard:0.1.0 .
docker push my-registry/forgeflow-api:0.1.0
docker push my-registry/forgeflow-mcp:0.1.0
docker push my-registry/forgeflow-dashboard:0.1.0

# 2. Create the namespace + secret (edit the secret first!)
kubectl apply -f 00-namespace.yaml
cp 11-secret.example.yaml 11-secret.yaml
# Edit 11-secret.yaml with real values, then:
kubectl apply -f 11-secret.yaml

# 3. Apply everything else
kubectl apply -f 10-configmap.yaml
kubectl apply -f 20-postgres-statefulset.yaml -f 21-postgres-service.yaml

# 4. Wait for postgres ready, then run the migration job once
kubectl -n forgeflow wait --for=condition=Ready pod/forgeflow-postgres-0 --timeout=300s
kubectl apply -f 70-migrate-job.yaml
kubectl -n forgeflow wait --for=condition=Complete job/forgeflow-migrate --timeout=300s

# 5. Apply the rest
kubectl apply -f 30-mcp-deployment.yaml -f 31-mcp-service.yaml
kubectl apply -f 40-api-deployment.yaml -f 41-api-service.yaml -f 42-api-hpa.yaml
kubectl apply -f 50-dashboard-deployment.yaml -f 51-dashboard-service.yaml
kubectl apply -f 60-ingress.yaml -f 80-network-policy.yaml
```

## Production checklist

- Replace `11-secret.example.yaml` with real values via `kubectl create secret`,
  sealed-secrets, or external-secrets-operator. Never commit real secrets.
- Set `image` to a pinned tag in production (`:0.1.0`, not `:latest`).
- Tune `resources.requests` + `resources.limits` to your workload.
- Provide a real `StorageClass` on the postgres PVC (current default uses the
  cluster default storage class).
- For a clustered Postgres, replace the single-pod StatefulSet with an
  operator like CloudNativePG or use a managed RDS / Cloud SQL / Postgres
  Flexible Server. See `../terraform/aws` for the EKS+RDS pattern.
- Replace the example NGINX Ingress with your cloud's LoadBalancer + cert-manager.

## File order convention

Numeric prefixes (`00-`, `10-`, etc.) control `kubectl apply -f .` ordering
without `kustomize`. If you wire Kustomize or ArgoCD, the order field is
authoritative and these prefixes can be relaxed.
