"""POST /api/v1/rag/query: natural-language question, answer grounded in user's processed documents."""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from src.api.auth import get_owner_id
from src.services import rag_service

router = APIRouter(prefix="/rag", tags=["rag"])


class RAGQueryRequest(BaseModel):
    """Request body for POST /rag/query per contracts/api-contract.md."""

    question: str = Field(..., min_length=1, description="Natural-language question")


@router.post(
    "/query",
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Answer and optional source_document_ids (filenames)"},
        400: {"description": "Missing question or invalid body"},
        401: {"description": "Missing or invalid token"},
        429: {"description": "Rate limit exceeded"},
    },
)
async def rag_query(
    owner_id: Annotated[str, Depends(get_owner_id)],
    body: RAGQueryRequest,
):
    """
    Submit a question; return an answer grounded in the user's processed documents.
    source_document_ids are filenames that contributed chunks. Empty store returns clear no-knowledge message.
    """
    answer, source_document_ids = rag_service.rag_query(owner_id, body.question)
    return {"answer": answer, "source_document_ids": source_document_ids}
