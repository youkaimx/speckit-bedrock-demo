# S3 Vectors: vector bucket and index for document embeddings (US2/US3).
# Matches app embedding dimension (1024, Titan Text Embeddings V2) and cosine similarity.
# Requires AWS provider with S3 Vectors support (e.g. hashicorp/aws >= 6.24).

resource "aws_s3vectors_vector_bucket" "embeddings" {
  vector_bucket_name = "${local.name_prefix}-vectors"

  # Encryption at rest (SSE-S3 equivalent for vector bucket)
  encryption_configuration {
    sse_type = "AES256"
  }

  tags = {
    Name        = "${local.name_prefix}-vectors"
    Environment = var.environment
  }
}

resource "aws_s3vectors_index" "embeddings" {
  index_name         = "default"
  vector_bucket_name = aws_s3vectors_vector_bucket.embeddings.vector_bucket_name
  dimension          = 1024
  distance_metric    = "cosine"
  data_type          = "float32"
}
