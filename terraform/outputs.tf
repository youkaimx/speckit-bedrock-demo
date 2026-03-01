output "aws_region" {
  description = "AWS region"
  value       = var.aws_region
}

output "s3_bucket_documents" {
  description = "S3 bucket name for documents"
  value       = module.s3_documents.s3_bucket_id
}

output "dynamodb_table_name" {
  description = "DynamoDB table name for document metadata"
  value       = module.dynamodb_metadata.dynamodb_table_id
}

output "s3_vectors_bucket_name" {
  description = "S3 Vectors bucket name for embeddings (set S3_VECTORS_BUCKET_OR_INDEX in app .env)"
  value       = aws_s3vectors_vector_bucket.embeddings.vector_bucket_name
}

output "s3_vectors_index_name" {
  description = "S3 Vectors index name (set S3_VECTORS_INDEX in app .env; default is 'default')"
  value       = aws_s3vectors_index.embeddings.index_name
}

output "bedrock_invoke_policy_arn" {
  description = "IAM policy ARN for Bedrock InvokeModel; attach to ECS task role (or app role) when deploying"
  value       = aws_iam_policy.bedrock_invoke.arn
}

output "s3vectors_embeddings_policy_arn" {
  description = "IAM policy ARN for S3 Vectors embeddings bucket/index; attach to ECS task role (or app role) when deploying"
  value       = aws_iam_policy.s3vectors_embeddings.arn
}
