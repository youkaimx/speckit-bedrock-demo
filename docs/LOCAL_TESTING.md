# Local Testing

Ways to run and test the Document RAG API locally.

---

## Option 1: Real AWS (Terraform + .env)

Terraform provisions S3 (documents), DynamoDB (metadata), **S3 Vectors** (embeddings bucket + index), and **IAM policies** for Bedrock and S3 Vectors. Cognito and ECS are added in later steps when needed.

1. **Provision infrastructure** (from repo root):

   ```bash
   cd terraform
   terraform init
   terraform apply
   ```

2. **Create `.env`** from Terraform outputs:

   ```bash
   export AWS_REGION=$(terraform -chdir=terraform output -raw aws_region)
   export S3_BUCKET_DOCUMENTS=$(terraform -chdir=terraform output -raw s3_bucket_documents)
   export DYNAMODB_TABLE_METADATA=$(terraform -chdir=terraform output -raw dynamodb_table_name)
   export S3_VECTORS_BUCKET_OR_INDEX=$(terraform -chdir=terraform output -raw s3_vectors_bucket_name)
   export S3_VECTORS_INDEX=$(terraform -chdir=terraform output -raw s3_vectors_index_name)
   # Optional: BEDROCK_MODEL_ID=amazon.titan-embed-text-v2:0  BEDROCK_RAG_MODEL_ID=anthropic.claude-3-haiku-20240307-v1:0
   ```

   Or copy `env.example` to `.env` and paste the output values. For RAG and processing you need Bedrock model access enabled in the AWS account (and the optional env vars above).

3. **Install and run**:

   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
   ```

   To set log verbosity: put `LOG_LEVEL=DEBUG` (or INFO, WARNING, ERROR) in `.env`, or run with the run entrypoint so CLI overrides config: `python -m src.api.run --reload --log-level DEBUG`.

4. **Use a dev token** (no Cognito needed for local calls):

   - Any request with `Authorization: Bearer dev-alice` is treated as user `dev-alice`.
   - Replace `dev-alice` with any identifier you like.

5. **Try the API**:

   - Open **http://localhost:8000/docs** (Swagger UI).
   - Or use curl:

   ```bash
   export TOKEN="dev-alice"

   # List documents (empty at first)
   curl -s http://localhost:8000/api/v1/documents -H "Authorization: Bearer $TOKEN"

   # Upload a PDF (replace path)
   curl -X POST http://localhost:8000/api/v1/documents \
     -H "Authorization: Bearer $TOKEN" \
     -F "file=@./path/to/file.pdf" \
     -F "mode=upload_and_queue"

   # List again
   curl -s http://localhost:8000/api/v1/documents -H "Authorization: Bearer $TOKEN"

   # Delete by document_id (filename)
   curl -X DELETE "http://localhost:8000/api/v1/documents/file.pdf" \
     -H "Authorization: Bearer $TOKEN"
   ```

---

## Option 2: LocalStack (S3 + DynamoDB only)

Use [LocalStack](https://localhost.localstack.cloud/) to emulate S3 and DynamoDB so you don’t need real AWS.

1. **Start LocalStack** (e.g. with Docker):

   ```bash
   docker run --rm -d -p 4566:4566 -p 4510-4559:4510-4559 localstack/localstack
   ```

2. **Create resources** (bucket + table). Example using AWS CLI pointed at LocalStack:

   ```bash
   export AWS_ACCESS_KEY_ID=test
   export AWS_SECRET_ACCESS_KEY=test
   export AWS_DEFAULT_REGION=us-east-1

   aws --endpoint-url=http://localhost:4566 s3 mb s3://local-documents
   aws --endpoint-url=http://localhost:4566 dynamodb create-table \
     --table-name document-metadata \
     --attribute-definitions AttributeName=owner_id,AttributeType=S AttributeName=filename,AttributeType=S \
     --key-schema AttributeName=owner_id,KeyType=HASH AttributeName=filename,KeyType=RANGE \
     --billing-mode PAY_PER_REQUEST
   ```

3. **`.env`** (or export before starting the app):

   ```bash
   AWS_REGION=us-east-1
   AWS_ENDPOINT_URL=http://localhost:4566
   S3_BUCKET_DOCUMENTS=local-documents
   DYNAMODB_TABLE_METADATA=document-metadata
   ```



   So for a quick LocalStack test, you’d add endpoint support in config and in the S3/DynamoDB client calls. The app reads `AWS_ENDPOINT_URL` from the environment; set it (e.g. in `.env`) so boto3 talks to LocalStack.

   **If you get 503 on upload:** Ensure the bucket and table exist. Create them with the commands in step 2 before calling the API.

   **Where DynamoDB is used:** The app creates the DynamoDB client in one place: `src/storage/metadata.py`, function `_get_table()`. It uses `boto3.resource("dynamodb", region_name=..., endpoint_url=...)` where `endpoint_url` is set from **`AWS_ENDPOINT_URL`** in your environment or `.env`. Settings are cached at startup—**restart the app** after changing `.env` so it picks up `AWS_ENDPOINT_URL`, `S3_BUCKET_DOCUMENTS`, and `DYNAMODB_TABLE_METADATA`.

4. **Run the app** as in Option 1 (venv, `uvicorn`), and use **`Bearer dev-alice`** and the same curl/`/docs` flow.

---

## Option 3: Smoke test only (no AWS)

You can start the server without real S3/DynamoDB to check that the app comes up and auth/validation behave:

1. **No `.env`** (or empty `S3_BUCKET_DOCUMENTS` and `DYNAMODB_TABLE_METADATA`).
2. **Run**:

   ```bash
   pip install -r requirements.txt
   uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
   ```

3. **In another terminal**:

   - **No token** → 401:
     ```bash
     curl -s http://localhost:8000/api/v1/documents
     ```
   - **With dev token** → 200 with empty list or 503 if storage isn’t configured:
     ```bash
     curl -s http://localhost:8000/api/v1/documents -H "Authorization: Bearer dev-alice"
     ```

   So you can at least verify routing and that `dev-` tokens are accepted. Upload/list/delete will fail until S3 and DynamoDB are configured (Option 1 or 2).

---

## Summary

| Goal                         | Approach                                      |
|-----------------------------|-----------------------------------------------|
| Full local test (upload/list/delete) | **Option 1** (Terraform + real AWS) or **Option 2** (LocalStack + endpoint wiring). |
| Quick auth/routing check    | **Option 3** (run server, use `Bearer dev-alice`, expect 401 without token). |

**Auth for local:** Use `Authorization: Bearer dev-<anything>`; no Cognito required.
**API docs:** http://localhost:8000/docs
