variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "document-rag-api"
}

variable "environment" {
  description = "Environment (e.g. dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "cognito_domain_prefix" {
  description = "Cognito hosted UI domain prefix (optional)"
  type        = string
  default     = ""
}

variable "s3_vectors_bucket_name" {
  description = "S3 Vectors bucket/index name (create via Console/CLI if Terraform provider does not yet support S3 Vectors)"
  type        = string
  default     = ""
}
