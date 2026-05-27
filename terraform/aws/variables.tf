variable "region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "cluster_name" {
  description = "Base name for all resources (EKS, RDS, ECR, IAM)"
  type        = string
  default     = "forgeflow"
  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{2,30}$", var.cluster_name))
    error_message = "cluster_name must be 3-31 chars, lowercase alphanumeric or hyphen."
  }
}

variable "environment" {
  description = "Environment tag (dev | staging | prod)"
  type        = string
  default     = "dev"
}

# --- VPC ------------------------------------------------------------------

variable "vpc_cidr" {
  description = "CIDR block for the new VPC"
  type        = string
  default     = "10.40.0.0/16"
}

variable "enable_nat_gateway" {
  description = "Create a NAT gateway so private subnets can reach the internet"
  type        = bool
  default     = true
}

# --- EKS ------------------------------------------------------------------

variable "eks_version" {
  description = "Kubernetes minor version (e.g. 1.31)"
  type        = string
  default     = "1.31"
}

variable "node_instance_types" {
  description = "EC2 instance types for the managed node group"
  type        = list(string)
  default     = ["m6i.large"]
}

variable "node_desired_size" {
  type    = number
  default = 3
}

variable "node_min_size" {
  type    = number
  default = 2
}

variable "node_max_size" {
  type    = number
  default = 10
}

# --- EKS public-endpoint access control ---
# SECURITY_AUDIT.md §8: leaving endpoint_public_access wide-open is the
# default that ships kubectl access to the whole internet. Lock it down to
# the CIDRs that genuinely need control-plane reach (office VPN, CI runners).
variable "eks_public_access_cidrs" {
  description = "CIDRs allowed to call the EKS public endpoint. Empty list = private-only."
  type        = list(string)
  default     = []
}

# --- RDS ------------------------------------------------------------------

variable "rds_instance_class" {
  type    = string
  default = "db.t4g.medium"
}

variable "rds_allocated_storage_gb" {
  type    = number
  default = 50
}

variable "rds_max_allocated_storage_gb" {
  description = "Storage autoscaling ceiling. 0 disables autoscaling."
  type        = number
  default     = 200
}

variable "rds_multi_az" {
  type    = bool
  default = false
}

variable "rds_backup_retention_days" {
  type    = number
  default = 7
}

variable "rds_skip_final_snapshot" {
  description = "Skip the final snapshot on destroy. Safe for dev; never true for prod."
  type        = bool
  default     = false
}

# --- Secrets seeded into Secrets Manager ----------------------------------

variable "openai_api_key" {
  description = "Seeded into the forgeflow-secrets AWS Secret"
  type        = string
  sensitive   = true
}

variable "api_secret_key" {
  description = "JWT signing secret (generate with: openssl rand -hex 32)"
  type        = string
  sensitive   = true
}

variable "langchain_api_key" {
  type      = string
  sensitive = true
  default   = ""
}

variable "slack_bot_token" {
  type      = string
  sensitive = true
  default   = ""
}

# --- Tags -----------------------------------------------------------------

variable "tags" {
  description = "Tags applied to every taggable resource"
  type        = map(string)
  default     = {}
}
