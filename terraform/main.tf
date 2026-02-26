terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 6.0"
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
module "s3_documents" {
  source  = "terraform-aws-modules/s3-bucket/aws"
  version = "~> 4.0"

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

# Cognito user pool and app client
module "cognito" {
  source  = "terraform-aws-modules/cognito/aws"
  version = "~> 4.0"

  name         = local.name_prefix
  user_pool_id = "${local.name_prefix}-pool"

  username_attributes      = ["email"]
  auto_verified_attributes = ["email"]

  password_policy = {
    minimum_length    = 12
    require_lowercase = true
    require_uppercase = true
    require_numbers   = true
    require_symbols   = true
  }

  # App client for API (OAuth/OIDC)
  app_clients = {
    api_client = {
      name                 = "api-client"
      generate_secret       = false
      access_token_validity = 1
      id_token_validity     = 1
      refresh_token_validity = 30
      token_validity_units = {
        access_token  = "hours"
        id_token      = "hours"
        refresh_token = "days"
      }
      explicit_auth_flows = [
        "ALLOW_USER_PASSWORD_AUTH",
        "ALLOW_REFRESH_TOKEN_AUTH",
        "ALLOW_USER_SRP_AUTH"
      ]
      supported_identity_providers = ["COGNITO"]
      callback_urls                = ["https://localhost/callback"]
      logout_urls                  = ["https://localhost"]
    }
  }

  tags = {
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
    { name = "owner_id"; type = "S" },
    { name = "filename"; type = "S" }
  ]

  tags = {
    Name        = "${local.name_prefix}-document-metadata"
    Environment = var.environment
  }
}

# ECS cluster (placeholder for Fargate service)
module "ecs" {
  source  = "terraform-aws-modules/ecs/aws"
  version = "~> 5.0"

  cluster_name = local.name_prefix

  fargate_capacity_providers = {
    FARGATE = {
      default_capacity_provider_strategy = {
        weight = 100
      }
    }
  }

  tags = {
    Environment = var.environment
  }
}

# ECS task execution role and task role placeholders
# Application will use these for S3, DynamoDB, Bedrock, Cognito
resource "aws_iam_role" "ecs_task_execution" {
  name = "${local.name_prefix}-ecs-task-execution"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role" "ecs_task" {
  name = "${local.name_prefix}-ecs-task"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })
}

# S3 Vectors: Terraform AWS provider may not yet support S3 Vectors index creation.
# Use var.s3_vectors_bucket_name from a bucket created via Console/CLI, or add
# aws_s3_vectors_index when the provider supports it.
# See: https://github.com/hashicorp/terraform-provider-aws/issues/43409
