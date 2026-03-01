"""Bedrock embedding invocation: Titan Text Embeddings for document chunks."""

import json

from src.api.config import get_settings
from src.storage.vectors import get_bedrock_client

# Default Titan Text Embeddings V2 model; config can override via BEDROCK_MODEL_ID.
DEFAULT_EMBEDDING_MODEL = "amazon.titan-embed-text-v2:0"
# Dimension must match the vector index; 1024 is Titan V2 default.
DEFAULT_DIMENSIONS = 1024


def embed_text(text: str) -> list[float]:
    """
    Invoke Bedrock to embed a single text string. Returns a list of floats (dimension from model).
    Uses Titan Text Embeddings V2 by default; request body: inputText; optional dimensions.
    """
    if not text or not text.strip():
        raise ValueError("Text to embed must be non-empty")
    settings = get_settings()
    model_id = settings.bedrock_model_id or DEFAULT_EMBEDDING_MODEL
    client = get_bedrock_client()
    body = json.dumps({"inputText": text.strip(), "dimensions": DEFAULT_DIMENSIONS})
    response = client.invoke_model(
        modelId=model_id,
        contentType="application/json",
        accept="application/json",
        body=body,
    )
    response_body = json.loads(response["body"].read())
    embedding = response_body.get("embedding")
    if not embedding:
        raise ValueError("Bedrock response missing 'embedding' field")
    return list(embedding)
