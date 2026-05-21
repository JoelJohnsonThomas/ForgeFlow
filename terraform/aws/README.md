# ForgeFlow on AWS — Terraform Module

Provisions the infrastructure ForgeFlow needs to run on AWS:

| AWS resource | Purpose |
|--------------|---------|
| VPC + public/private subnets across 3 AZs | Network foundation |
| EKS cluster (managed node group) | Kubernetes runtime for the workloads |
| RDS PostgreSQL 16 with `pgvector` parameter group | Database (replaces in-cluster StatefulSet) |
| Secrets Manager secret | Holds OPENAI_API_KEY, API_SECRET_KEY, DB password, etc. |
| ECR repositories (api, mcp, dashboard) | Image registry |
| ALB ingress controller IAM policy | LoadBalancer for the API + dashboard |
| IAM IRSA role for the API ServiceAccount | Reads secrets from Secrets Manager via the External Secrets Operator |

GCP and Azure equivalents are out of scope for this module — they're
queued in [ROADMAP.md](../../ROADMAP.md) Phase 5 as separate work.

## Prerequisites

- Terraform >= 1.6
- AWS credentials with permissions to create VPC + EKS + RDS + IAM + ECR
  + Secrets Manager (see `iam-bootstrap.json` for the minimal policy)
- `kubectl` for post-apply Helm install
- `helm` for the chart install step

## Usage

```hcl
module "forgeflow" {
  source  = "./terraform/aws"
  version = "0.1.0"

  region       = "us-east-1"
  cluster_name = "forgeflow-prod"
  environment  = "prod"

  # VPC
  vpc_cidr             = "10.40.0.0/16"
  enable_nat_gateway   = true

  # EKS
  eks_version          = "1.31"
  node_instance_types  = ["m6i.large"]
  node_desired_size    = 3
  node_min_size        = 2
  node_max_size        = 10

  # RDS
  rds_instance_class   = "db.r6g.large"
  rds_allocated_storage_gb = 100
  rds_multi_az         = true
  rds_backup_retention_days = 14

  # Secrets — values seeded into Secrets Manager
  openai_api_key       = var.openai_api_key       # from TF_VAR_openai_api_key
  api_secret_key       = var.api_secret_key
  langchain_api_key    = var.langchain_api_key

  tags = {
    "Owner"   = "platform-team"
    "CostCtr" = "ai-prod"
  }
}

output "eks_kubeconfig_command" {
  value = module.forgeflow.kubeconfig_command
}
output "rds_endpoint" {
  value = module.forgeflow.rds_endpoint
}
output "ecr_api_repo" {
  value = module.forgeflow.ecr_api_repo
}
```

## Apply

```bash
terraform init
terraform plan  -var "openai_api_key=$OPENAI_API_KEY" \
                -var "api_secret_key=$(openssl rand -hex 32)"
terraform apply -var "openai_api_key=$OPENAI_API_KEY" \
                -var "api_secret_key=$(openssl rand -hex 32)"
```

After apply:

```bash
# 1. Update kubeconfig
aws eks update-kubeconfig --region us-east-1 --name forgeflow-prod

# 2. Build + push images to the ECR repos that Terraform created
$(aws ecr get-login-password --region us-east-1 | \
    docker login --username AWS --password-stdin <account>.dkr.ecr.us-east-1.amazonaws.com)
docker build --target api       -t $(terraform output -raw ecr_api_repo):0.1.0       . && docker push $(terraform output -raw ecr_api_repo):0.1.0
docker build --target mcp       -t $(terraform output -raw ecr_mcp_repo):0.1.0       . && docker push $(terraform output -raw ecr_mcp_repo):0.1.0
docker build --target dashboard -t $(terraform output -raw ecr_dashboard_repo):0.1.0 . && docker push $(terraform output -raw ecr_dashboard_repo):0.1.0

# 3. Install the chart pointing at managed RDS + Secrets Manager
helm install ff ../../helm/forgeflow \
  -n forgeflow --create-namespace \
  --set image.tag=0.1.0 \
  --set image.registry=$(terraform output -raw ecr_account_url) \
  --set postgres.enabled=false \
  --set config.postgresUrl="$(terraform output -raw postgres_asyncpg_url)" \
  --set config.postgresSyncUrl="$(terraform output -raw postgres_psycopg_url)" \
  --set secrets.existingSecret=forgeflow-secrets
```

The `forgeflow-secrets` Kubernetes secret is created by the External
Secrets Operator that this module installs — it syncs from the AWS
Secrets Manager secret that Terraform seeded.

## Destroy

```bash
helm uninstall ff -n forgeflow
terraform destroy
```

RDS final snapshots are taken automatically (configurable via
`rds_skip_final_snapshot`). The EBS volumes backing PVCs in EKS are
NOT cleaned up by `terraform destroy` — drop the PVCs in the namespace
first if you want a clean teardown.
