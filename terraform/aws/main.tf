# ForgeFlow AWS infrastructure: VPC + EKS + RDS + Secrets Manager + ECR.
#
# Topology:
#   3-AZ VPC with public + private subnets. NAT gateway for private-subnet
#   egress so pods can reach external LLM providers. EKS managed node group
#   in private subnets. RDS in private subnets (db_subnet_group).
#   Secrets Manager holds the runtime secrets; we don't pass them into
#   kubernetes_secret directly — that's the job of External Secrets
#   Operator (installed by the apps team after `terraform apply`).

provider "aws" {
  region = var.region
  default_tags {
    tags = merge(
      {
        "Project"    = "forgeflow"
        "ManagedBy"  = "terraform"
        "Environment" = var.environment
      },
      var.tags,
    )
  }
}

data "aws_caller_identity" "current" {}
data "aws_availability_zones" "available" {
  state = "available"
}

locals {
  azs = slice(data.aws_availability_zones.available.names, 0, 3)
  name = var.cluster_name
}

# ---------------------------------------------------------------------------
# VPC + subnets
# ---------------------------------------------------------------------------
resource "aws_vpc" "this" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true
  tags = { Name = "${local.name}-vpc" }
}

resource "aws_internet_gateway" "this" {
  vpc_id = aws_vpc.this.id
  tags   = { Name = "${local.name}-igw" }
}

# Public subnets (one per AZ) for the NAT GW + ALB
resource "aws_subnet" "public" {
  count                   = length(local.azs)
  vpc_id                  = aws_vpc.this.id
  cidr_block              = cidrsubnet(var.vpc_cidr, 4, count.index)
  availability_zone       = local.azs[count.index]
  map_public_ip_on_launch = true
  tags = {
    Name                                          = "${local.name}-public-${local.azs[count.index]}"
    "kubernetes.io/role/elb"                      = "1"
    "kubernetes.io/cluster/${local.name}"         = "shared"
  }
}

# Private subnets for the EKS nodes + RDS
resource "aws_subnet" "private" {
  count             = length(local.azs)
  vpc_id            = aws_vpc.this.id
  cidr_block        = cidrsubnet(var.vpc_cidr, 4, count.index + 8)
  availability_zone = local.azs[count.index]
  tags = {
    Name                                          = "${local.name}-private-${local.azs[count.index]}"
    "kubernetes.io/role/internal-elb"             = "1"
    "kubernetes.io/cluster/${local.name}"         = "shared"
  }
}

resource "aws_eip" "nat" {
  count  = var.enable_nat_gateway ? 1 : 0
  domain = "vpc"
  tags   = { Name = "${local.name}-nat-eip" }
}

resource "aws_nat_gateway" "this" {
  count         = var.enable_nat_gateway ? 1 : 0
  allocation_id = aws_eip.nat[0].id
  subnet_id     = aws_subnet.public[0].id
  tags          = { Name = "${local.name}-nat" }
  depends_on    = [aws_internet_gateway.this]
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.this.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.this.id
  }
  tags = { Name = "${local.name}-public-rt" }
}

resource "aws_route_table" "private" {
  vpc_id = aws_vpc.this.id
  dynamic "route" {
    for_each = var.enable_nat_gateway ? [1] : []
    content {
      cidr_block     = "0.0.0.0/0"
      nat_gateway_id = aws_nat_gateway.this[0].id
    }
  }
  tags = { Name = "${local.name}-private-rt" }
}

resource "aws_route_table_association" "public" {
  count          = length(aws_subnet.public)
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table_association" "private" {
  count          = length(aws_subnet.private)
  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private.id
}

# ---------------------------------------------------------------------------
# EKS cluster
# ---------------------------------------------------------------------------
resource "aws_iam_role" "eks_cluster" {
  name = "${local.name}-eks-cluster"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = { Service = "eks.amazonaws.com" }
      Action = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "eks_cluster_policy" {
  role       = aws_iam_role.eks_cluster.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSClusterPolicy"
}

resource "aws_eks_cluster" "this" {
  name     = local.name
  version  = var.eks_version
  role_arn = aws_iam_role.eks_cluster.arn

  vpc_config {
    subnet_ids              = concat(aws_subnet.public[*].id, aws_subnet.private[*].id)
    # SECURITY_AUDIT.md §8: public endpoint is allowed only for the CIDRs
    # the operator explicitly lists; empty list ⇒ public access disabled.
    endpoint_public_access  = length(var.eks_public_access_cidrs) > 0
    endpoint_private_access = true
    public_access_cidrs     = length(var.eks_public_access_cidrs) > 0 ? var.eks_public_access_cidrs : null
  }

  # Enable EKS-managed control plane logs for audit
  enabled_cluster_log_types = ["api", "audit", "authenticator", "controllerManager", "scheduler"]

  depends_on = [aws_iam_role_policy_attachment.eks_cluster_policy]
}

# ---------------------------------------------------------------------------
# EKS managed node group
# ---------------------------------------------------------------------------
resource "aws_iam_role" "eks_node" {
  name = "${local.name}-eks-node"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
      Action = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "eks_worker_node" {
  role       = aws_iam_role.eks_node.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy"
}

resource "aws_iam_role_policy_attachment" "eks_cni" {
  role       = aws_iam_role.eks_node.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy"
}

resource "aws_iam_role_policy_attachment" "ecr_read" {
  role       = aws_iam_role.eks_node.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
}

# SECURITY_AUDIT.md C-6: IMDSv2 must be required so SSRF in a pod can't read
# the node's instance credentials. hop-limit=1 stops containerised processes
# from reaching IMDS at all (the extra hop crossing the bridge eats the TTL).
resource "aws_launch_template" "nodes" {
  name_prefix = "${local.name}-node-"

  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required"
    http_put_response_hop_limit = 1
    instance_metadata_tags      = "disabled"
  }

  monitoring { enabled = true }

  block_device_mappings {
    device_name = "/dev/xvda"
    ebs {
      volume_size           = 50
      volume_type           = "gp3"
      encrypted             = true
      delete_on_termination = true
    }
  }

  tag_specifications {
    resource_type = "instance"
    tags = { Name = "${local.name}-node" }
  }
}

resource "aws_eks_node_group" "default" {
  cluster_name    = aws_eks_cluster.this.name
  node_group_name = "${local.name}-default"
  node_role_arn   = aws_iam_role.eks_node.arn
  subnet_ids      = aws_subnet.private[*].id
  instance_types  = var.node_instance_types

  launch_template {
    id      = aws_launch_template.nodes.id
    version = aws_launch_template.nodes.latest_version
  }

  scaling_config {
    desired_size = var.node_desired_size
    max_size     = var.node_max_size
    min_size     = var.node_min_size
  }

  update_config { max_unavailable = 1 }

  depends_on = [
    aws_iam_role_policy_attachment.eks_worker_node,
    aws_iam_role_policy_attachment.eks_cni,
    aws_iam_role_policy_attachment.ecr_read,
  ]
}

# ---------------------------------------------------------------------------
# IAM OIDC provider — required for IRSA (IAM roles for service accounts)
# ---------------------------------------------------------------------------
data "tls_certificate" "eks" {
  url = aws_eks_cluster.this.identity[0].oidc[0].issuer
}

resource "aws_iam_openid_connect_provider" "eks" {
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = [data.tls_certificate.eks.certificates[0].sha1_fingerprint]
  url             = aws_eks_cluster.this.identity[0].oidc[0].issuer
}

# ---------------------------------------------------------------------------
# RDS PostgreSQL 16 with pgvector
# ---------------------------------------------------------------------------
resource "random_password" "db" {
  length  = 32
  special = false  # RDS rejects some special chars; alnum is safer
}

resource "aws_db_subnet_group" "this" {
  name       = "${local.name}-db"
  subnet_ids = aws_subnet.private[*].id
  tags       = { Name = "${local.name}-db-subnet" }
}

resource "aws_security_group" "rds" {
  name        = "${local.name}-rds"
  description = "Allow Postgres from EKS nodes only"
  vpc_id      = aws_vpc.this.id

  ingress {
    description     = "Postgres from EKS nodes"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    cidr_blocks     = [var.vpc_cidr]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${local.name}-rds-sg" }
}

# pgvector is bundled in RDS PG 15.5+; enable via the parameter group +
# CREATE EXTENSION run by our alembic migration 002_pgvector_memory.
resource "aws_db_parameter_group" "pg16" {
  name   = "${local.name}-pg16"
  family = "postgres16"

  parameter {
    name  = "shared_preload_libraries"
    value = "vector"
    apply_method = "pending-reboot"
  }
}

# SECURITY_AUDIT.md §8: encryption-at-rest with a customer-managed KMS key
# (not the default aws/rds key) so we can audit grants + revoke decrypt.
resource "aws_kms_key" "data" {
  description             = "${local.name} application data (RDS, Secrets Manager)"
  deletion_window_in_days = var.environment == "prod" ? 30 : 7
  enable_key_rotation     = true
  tags                    = { Name = "${local.name}-data" }
}

resource "aws_kms_alias" "data" {
  name          = "alias/${local.name}-data"
  target_key_id = aws_kms_key.data.key_id
}

resource "aws_db_instance" "this" {
  identifier              = "${local.name}-db"
  engine                  = "postgres"
  engine_version          = "16.3"
  instance_class          = var.rds_instance_class
  allocated_storage       = var.rds_allocated_storage_gb
  max_allocated_storage   = var.rds_max_allocated_storage_gb > 0 ? var.rds_max_allocated_storage_gb : null
  storage_type            = "gp3"
  storage_encrypted       = true
  kms_key_id              = aws_kms_key.data.arn

  db_name                 = "forgeflow"
  username                = "forgeflow"
  password                = random_password.db.result

  db_subnet_group_name    = aws_db_subnet_group.this.name
  vpc_security_group_ids  = [aws_security_group.rds.id]
  parameter_group_name    = aws_db_parameter_group.pg16.name

  multi_az                  = var.rds_multi_az
  backup_retention_period   = var.rds_backup_retention_days
  backup_window             = "03:00-04:00"
  maintenance_window        = "sun:04:00-sun:05:00"
  deletion_protection       = var.environment == "prod"
  skip_final_snapshot       = var.rds_skip_final_snapshot
  final_snapshot_identifier = var.rds_skip_final_snapshot ? null : "${local.name}-final-${formatdate("YYYYMMDDhhmmss", timestamp())}"

  performance_insights_enabled    = true
  performance_insights_kms_key_id = aws_kms_key.data.arn
  # Forward Postgres logs to CloudWatch so audit/forensics survive instance loss.
  enabled_cloudwatch_logs_exports = ["postgresql", "upgrade"]
  # Auto-apply minor version bumps in maintenance window — closes CVEs faster.
  auto_minor_version_upgrade      = true

  tags = { Name = "${local.name}-db" }
}

# ---------------------------------------------------------------------------
# Secrets Manager — runtime secrets pulled into K8s via External Secrets
# ---------------------------------------------------------------------------
resource "aws_secretsmanager_secret" "forgeflow" {
  name        = "${local.name}/runtime"
  description = "ForgeFlow runtime secrets (OpenAI key, JWT signing, DB password, ...)"
  recovery_window_in_days = var.environment == "prod" ? 30 : 0
  kms_key_id  = aws_kms_key.data.arn
}

resource "aws_secretsmanager_secret_version" "forgeflow" {
  secret_id = aws_secretsmanager_secret.forgeflow.id
  secret_string = jsonencode({
    OPENAI_API_KEY    = var.openai_api_key
    API_SECRET_KEY    = var.api_secret_key
    POSTGRES_PASSWORD = random_password.db.result
    LANGCHAIN_API_KEY = var.langchain_api_key
    SLACK_BOT_TOKEN   = var.slack_bot_token
  })
}

# ---------------------------------------------------------------------------
# ECR repos — one per Dockerfile build target
# ---------------------------------------------------------------------------
resource "aws_ecr_repository" "api" {
  name                 = "${local.name}/api"
  image_tag_mutability = "IMMUTABLE"
  image_scanning_configuration { scan_on_push = true }
}

resource "aws_ecr_repository" "mcp" {
  name                 = "${local.name}/mcp"
  image_tag_mutability = "IMMUTABLE"
  image_scanning_configuration { scan_on_push = true }
}

resource "aws_ecr_repository" "dashboard" {
  name                 = "${local.name}/dashboard"
  image_tag_mutability = "IMMUTABLE"
  image_scanning_configuration { scan_on_push = true }
}

# ---------------------------------------------------------------------------
# IRSA — IAM role assumable by the ForgeFlow ServiceAccount so it can read
# the Secrets Manager secret via External Secrets Operator.
# ---------------------------------------------------------------------------
resource "aws_iam_role" "external_secrets" {
  name = "${local.name}-external-secrets"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = { Federated = aws_iam_openid_connect_provider.eks.arn }
      Action = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "${replace(aws_iam_openid_connect_provider.eks.url, "https://", "")}:sub" = "system:serviceaccount:forgeflow:external-secrets"
          "${replace(aws_iam_openid_connect_provider.eks.url, "https://", "")}:aud" = "sts.amazonaws.com"
        }
      }
    }]
  })
}

resource "aws_iam_policy" "external_secrets_read" {
  name = "${local.name}-secret-read"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "secretsmanager:GetSecretValue",
        "secretsmanager:DescribeSecret",
      ]
      Resource = aws_secretsmanager_secret.forgeflow.arn
    }]
  })
}

resource "aws_iam_role_policy_attachment" "external_secrets" {
  role       = aws_iam_role.external_secrets.name
  policy_arn = aws_iam_policy.external_secrets_read.arn
}
