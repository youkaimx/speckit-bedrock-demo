output "aws_region" {
  description = "AWS region"
  value       = var.aws_region
}

output "s3_bucket_documents" {
  description = "S3 bucket name for documents"
  value       = module.s3_documents.s3_bucket_id
}

output "cognito_user_pool_id" {
  description = "Cognito user pool ID"
  value       = aws_cognito_user_pool.main.id
}

output "cognito_user_pool_client_id" {
  description = "Cognito app client ID"
  value       = aws_cognito_user_pool_client.api_client.id
}

output "dynamodb_table_name" {
  description = "DynamoDB table name for document metadata"
  value       = module.dynamodb_metadata.dynamodb_table_id
}

output "ecs_cluster_name" {
  description = "ECS cluster name"
  value       = module.ecs.cluster_name
}

output "ecs_task_execution_role_arn" {
  description = "ECS task execution role ARN"
  value       = aws_iam_role.ecs_task_execution.arn
}

output "ecs_task_role_arn" {
  description = "ECS task role ARN (for S3, DynamoDB, Bedrock)"
  value       = aws_iam_role.ecs_task.arn
}

output "s3_vectors_bucket_name" {
  description = "S3 Vectors bucket/index name (set variable if created separately)"
  value       = var.s3_vectors_bucket_name != "" ? var.s3_vectors_bucket_name : null
}
