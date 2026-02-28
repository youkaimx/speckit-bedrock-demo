terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 6.0"
    }
  }
  cloud {

    organization = "youkaimx"

    workspaces {
      name = "speckit-bedrock-demo"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

locals {
  name_prefix = "${var.project_name}-${var.environment}"
}

# S3 bucket for documents (SSE-S3 encryption at rest)
# v5.x fixes aws_region.name deprecation (uses id) for AWS provider 6
module "s3_documents" {
  source  = "terraform-aws-modules/s3-bucket/aws"
  version = "~> 5.0"

  bucket = "${local.name_prefix}-documents"

  # Encryption at rest (SSE-S3)
  server_side_encryption_configuration = {
    rule = {
      apply_server_side_encryption_by_default = {
        sse_algorithm = "AES256"
      }
      bucket_key_enabled = true
    }
  }

  # Block public access
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true

  tags = {
    Name        = "${local.name_prefix}-documents"
    Environment = var.environment
  }
}

# DynamoDB table for document metadata (owner_id + filename)
module "dynamodb_metadata" {
  source  = "terraform-aws-modules/dynamodb-table/aws"
  version = "~> 4.0"

  name         = "${local.name_prefix}-document-metadata"
  hash_key     = "owner_id"
  range_key    = "filename"
  billing_mode = "PAY_PER_REQUEST"

  attributes = [
    { name = "owner_id", type = "S" },
    { name = "filename", type = "S" }
  ]

  tags = {
    Name        = "${local.name_prefix}-document-metadata"
    Environment = var.environment
  }
}
