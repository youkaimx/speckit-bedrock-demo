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
