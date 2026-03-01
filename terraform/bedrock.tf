# Bedrock: model access and IAM for embeddings and RAG.
# Foundation models are enabled per account/region; this file defines IAM so the app (e.g. ECS task) can invoke them.

data "aws_caller_identity" "current" {}

# IAM policy: allow InvokeModel and InvokeModelWithResponseStream for Bedrock foundation models.
# Attach to ECS task role (or other execution role) when deploying the API.
resource "aws_iam_policy" "bedrock_invoke" {
  name        = "${local.name_prefix}-bedrock-invoke"
  description = "Allow invoking Bedrock foundation models (embeddings and RAG)"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "BedrockInvoke"
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream"
        ]
        Resource = [
          "arn:aws:bedrock:${var.aws_region}::foundation-model/amazon.titan-embed-text-v2:0",
          "arn:aws:bedrock:${var.aws_region}::foundation-model/anthropic.claude-3-haiku-20240307-v1:0",
          "arn:aws:bedrock:${var.aws_region}::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0"
        ]
      }
    ]
  })
}

# IAM policy: allow S3 Vectors read/write for the embeddings bucket and index.
# Attach to the same role as bedrock_invoke when the app runs in ECS.
# Index ARN format: arn:aws:s3vectors:region:account:bucket/name/index/index-name
locals {
  s3vectors_bucket_arn = "arn:aws:s3vectors:${var.aws_region}:${data.aws_caller_identity.current.account_id}:bucket/${aws_s3vectors_vector_bucket.embeddings.vector_bucket_name}"
  s3vectors_index_arn  = "${local.s3vectors_bucket_arn}/index/${aws_s3vectors_index.embeddings.index_name}"
}

resource "aws_iam_policy" "s3vectors_embeddings" {
  name        = "${local.name_prefix}-s3vectors-embeddings"
  description = "Allow put/list/query/delete vectors in the embeddings bucket"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "S3VectorsEmbeddings"
        Effect = "Allow"
        Action = [
          "s3vectors:PutVectors",
          "s3vectors:DeleteVectors",
          "s3vectors:ListVectors",
          "s3vectors:QueryVectors",
          "s3vectors:GetVectors"
        ]
        Resource = [
          local.s3vectors_bucket_arn,
          local.s3vectors_index_arn
        ]
      }
    ]
  })
}
