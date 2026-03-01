"""RAG service: retrieve chunks from S3 Vectors, build context, invoke Bedrock for grounded answer."""

import json

from src.api.config import get_settings
from src.services import embedding_service, retrieval_service
from src.storage.vectors import get_bedrock_client

# When no relevant content: return this message and empty source_document_ids (T035; do not fabricate).
NO_KNOWLEDGE_MESSAGE = (
    "No relevant content in your documents. Upload and process documents to ask questions."
)
# Default Claude model for RAG; override with BEDROCK_RAG_MODEL_ID.
DEFAULT_RAG_MODEL = "anthropic.claude-3-haiku-20240307-v1:0"
RAG_TOP_K = 10
RAG_MAX_TOKENS = 1024


def rag_query(owner_id: str, question: str) -> tuple[str, list[str]]:
    """
    Answer question using the user's processed documents. Returns (answer, source_document_ids).
    source_document_ids are filenames of documents that contributed chunks (for attribution).
    If vector store is empty or no relevant chunks: return clear no-knowledge message and [] (T035).
    """
    question = (question or "").strip()
    if not question:
        return NO_KNOWLEDGE_MESSAGE, []

    try:
        query_embedding = embedding_service.embed_text(question)
    except Exception:
        return NO_KNOWLEDGE_MESSAGE, []

    chunks = retrieval_service.retrieve(owner_id, query_embedding, top_k=RAG_TOP_K)
    if not chunks:
        return NO_KNOWLEDGE_MESSAGE, []

    context_parts = []
    seen_filenames: set[str] = set()
    for text, document_filename in chunks:
        if text:
            context_parts.append(text)
        if document_filename:
            seen_filenames.add(document_filename)
    context = "\n\n---\n\n".join(context_parts) if context_parts else ""
    if not context:
        return NO_KNOWLEDGE_MESSAGE, []

    settings = get_settings()
    model_id = settings.bedrock_rag_model_id or DEFAULT_RAG_MODEL
    client = get_bedrock_client()
    system = (
        "Answer the user's question using only the following context from their documents. "
        "If the context does not contain relevant information, say so clearly. Do not fabricate or guess."
    )
    user_content = f"Context:\n{context}\n\nQuestion: {question}"
    body = json.dumps(
        {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": RAG_MAX_TOKENS,
            "system": system,
            "messages": [{"role": "user", "content": user_content}],
        }
    )
    response = client.invoke_model(
        modelId=model_id,
        contentType="application/json",
        accept="application/json",
        body=body,
    )
    response_body = json.loads(response["body"].read())
    content_blocks = response_body.get("content", [])
    answer = NO_KNOWLEDGE_MESSAGE
    for block in content_blocks:
        if block.get("type") == "text" and block.get("text"):
            answer = block["text"].strip()
            break
    source_document_ids = sorted(seen_filenames)
    return answer, source_document_ids
