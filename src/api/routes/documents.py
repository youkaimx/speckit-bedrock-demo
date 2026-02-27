"""POST/GET/DELETE /api/v1/documents. document_id = filename (user-scoped)."""

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from src.api.auth import get_owner_id
from src.models.document import Document
from src.services import upload_service

router = APIRouter(prefix="/documents", tags=["documents"])


def _doc_to_response(doc: Document) -> dict:
    return {
        "document_id": doc.filename,
        "format": doc.format.value if hasattr(doc.format, "value") else doc.format,
        "size_bytes": doc.size_bytes,
        "uploaded_at": doc.uploaded_at.isoformat(),
        "processing_status": doc.processing_status.value
        if hasattr(doc.processing_status, "value")
        else doc.processing_status,
        "processing_error": doc.processing_error,
    }


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Document uploaded"},
        400: {"description": "Invalid format, missing file/mode, or file > 25 MB"},
        401: {"description": "Missing or invalid token"},
        429: {"description": "Rate limit exceeded"},
    },
)
async def upload_document(
    owner_id: Annotated[str, Depends(get_owner_id)],
    file: Annotated[UploadFile, File(description="PDF or Markdown file, max 25 MB")],
    mode: Annotated[str, Form(description="upload_and_analyze | upload_and_queue")],
    name: Annotated[str | None, Form()] = None,
):
    """Upload a PDF or Markdown file. document_id in response is the user-scoped filename."""
    if mode not in ("upload_and_analyze", "upload_and_queue"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "mode must be upload_and_analyze or upload_and_queue"},
        )
    filename = (name or file.filename or "").strip()
    if not filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "Missing filename (provide file or name)"},
        )
    content_type = file.content_type
    body = await file.read()
    size = len(body)
    fmt, err = upload_service.validate_upload(filename, content_type, size)
    if err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": err},
        )
    try:
        from io import BytesIO

        doc = upload_service.upload_document(
            owner_id=owner_id,
            filename=filename,
            body=BytesIO(body),
            content_type=content_type,
            size=size,
            mode=mode,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail={"error": str(e)}
        ) from e
    return _doc_to_response(doc)


@router.get(
    "",
    responses={
        200: {"description": "List of documents"},
        401: {"description": "Missing or invalid token"},
        429: {"description": "Rate limit exceeded"},
    },
)
async def list_documents(
    owner_id: Annotated[str, Depends(get_owner_id)],
    limit: int = 100,
    next_token: str | None = None,
):
    """List the authenticated user's documents. document_id = filename."""
    docs, next_tok = upload_service.list_documents(owner_id, limit=limit, next_token=next_token)
    items = [_doc_to_response(d) for d in docs]
    out = {"documents": items}
    if next_tok:
        out["next_token"] = next_tok
    return out


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {"description": "Document and embeddings removed"},
        401: {"description": "Missing or invalid token"},
        403: {"description": "Document belongs to another user"},
        404: {"description": "No document with that filename for this user"},
        429: {"description": "Rate limit exceeded"},
    },
)
async def delete_document(
    owner_id: Annotated[str, Depends(get_owner_id)],
    document_id: str,
):
    """Delete document and its embeddings. document_id is the user-scoped filename (URL-encoded)."""
    from urllib.parse import unquote

    filename = unquote(document_id)
    if not filename:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail={"error": "Document not found"}
        )
    found = upload_service.delete_document(owner_id, filename)
    if not found:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "No document with that filename for this user"},
        )
    return None
