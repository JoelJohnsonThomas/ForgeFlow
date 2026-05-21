output "vpc_id" {
  value       = aws_vpc.this.id
  description = "ID of the VPC ForgeFlow runs in"
}

output "private_subnet_ids" {
  value = aws_subnet.private[*].id
}

output "public_subnet_ids" {
  value = aws_subnet.public[*].id
}

output "cluster_name" {
  value = aws_eks_cluster.this.name
}

output "cluster_endpoint" {
  value     = aws_eks_cluster.this.endpoint
  sensitive = false
}

output "cluster_oidc_issuer" {
  value = aws_eks_cluster.this.identity[0].oidc[0].issuer
}

output "kubeconfig_command" {
  description = "Shell command to populate ~/.kube/config for kubectl"
  value       = "aws eks update-kubeconfig --region ${var.region} --name ${aws_eks_cluster.this.name}"
}

output "rds_endpoint" {
  value     = aws_db_instance.this.address
  sensitive = false
}

output "rds_port" {
  value = aws_db_instance.this.port
}

output "postgres_asyncpg_url" {
  description = "Connection string ForgeFlow's POSTGRES_URL should be set to"
  value       = "postgresql+asyncpg://forgeflow:${random_password.db.result}@${aws_db_instance.this.address}:${aws_db_instance.this.port}/forgeflow"
  sensitive   = true
}

output "postgres_psycopg_url" {
  description = "Connection string ForgeFlow's POSTGRES_SYNC_URL should be set to"
  value       = "postgresql+psycopg://forgeflow:${random_password.db.result}@${aws_db_instance.this.address}:${aws_db_instance.this.port}/forgeflow"
  sensitive   = true
}

output "secrets_manager_arn" {
  value = aws_secretsmanager_secret.forgeflow.arn
}

output "ecr_account_url" {
  description = "Base ECR registry URL (use as image.registry in Helm values)"
  value       = "${data.aws_caller_identity.current.account_id}.dkr.ecr.${var.region}.amazonaws.com"
}

output "ecr_api_repo" {
  value = aws_ecr_repository.api.repository_url
}

output "ecr_mcp_repo" {
  value = aws_ecr_repository.mcp.repository_url
}

output "ecr_dashboard_repo" {
  value = aws_ecr_repository.dashboard.repository_url
}

output "external_secrets_irsa_arn" {
  description = "IAM role ARN for the External Secrets Operator ServiceAccount"
  value       = aws_iam_role.external_secrets.arn
}
