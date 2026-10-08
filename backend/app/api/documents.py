import json
import uuid
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from app.core.database import get_db, utc_now
from app.core.security import require_role
from app.models.schemas import (
    ChunkListResponse,
    ChunkResponse,
    DocumentCreate,
    DocumentListResponse,
    DocumentResponse,
)
from app.services.audit_service import log_audit_event
from app.services.rag_engine import (
    chunk_text,
    compute_hash,
    generate_deterministic_embedding,
)

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/ingest", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def ingest_document(
    doc: DocumentCreate,
    user: Dict[str, Any] = Depends(require_role("operator")),
):
    if not doc.text.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Document text cannot be empty.",
        )

    doc_id = f"doc-{uuid.uuid4().hex[:12]}"
    content_hash = compute_hash(doc.text)
    chunks_data = chunk_text(doc.text, chunk_size=doc.chunk_size, overlap=doc.chunk_overlap)
    now = utc_now()

    with get_db() as conn:
        # Verify collection exists, or create it
        conn.execute(
            """
            INSERT OR IGNORE INTO collections (name, description, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            """,
            (doc.collection, f"Collection {doc.collection}", now, now),
        )

        conn.execute(
            """
            INSERT INTO documents (id, collection, name, content_type, char_count, chunk_count, content_hash, metadata_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                doc_id,
                doc.collection,
                doc.name,
                "text/markdown" if doc.name.endswith(".md") else "text/plain",
                len(doc.text),
                len(chunks_data),
                content_hash,
                json.dumps(doc.metadata),
                now,
            ),
        )

        for i, c in enumerate(chunks_data):
            chunk_id = f"{doc_id}_c{i}"
            emb = generate_deterministic_embedding(c["text"])
            conn.execute(
                """
                INSERT INTO chunks (id, document_id, collection, chunk_index, text, heading, token_count, embedding_json, content_hash, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    chunk_id,
                    doc_id,
                    doc.collection,
                    i,
                    c["text"],
                    c["heading"],
                    c["token_count"],
                    json.dumps(emb),
                    c["content_hash"],
                    now,
                ),
            )

    log_audit_event(
        action="ingest_document",
        user_id=user["user_id"],
        user_role=user["effective_role"],
        resource_id=doc_id,
        details=f"Ingested '{doc.name}' ({len(chunks_data)} chunks) in '{doc.collection}'",
    )

    return DocumentResponse(
        id=doc_id,
        collection=doc.collection,
        name=doc.name,
        content_type="text/markdown" if doc.name.endswith(".md") else "text/plain",
        char_count=len(doc.text),
        chunk_count=len(chunks_data),
        content_hash=content_hash,
        created_at=now,
    )


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    collection: Optional[str] = None,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    user: Dict[str, Any] = Depends(require_role("viewer")),
):
    offset = (page - 1) * size
    query = "SELECT id, collection, name, content_type, char_count, chunk_count, content_hash, created_at FROM documents"
    count_query = "SELECT COUNT(*) FROM documents"
    params = []

    if collection:
        query += " WHERE collection = ?"
        count_query += " WHERE collection = ?"
        params.append(collection)

    query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
    params_paged = params + [size, offset]

    with get_db() as conn:
        total = conn.execute(count_query, params).fetchone()[0]
        rows = conn.execute(query, params_paged).fetchall()
        items = [
            DocumentResponse(
                id=r["id"],
                collection=r["collection"],
                name=r["name"],
                content_type=r["content_type"],
                char_count=r["char_count"],
                chunk_count=r["chunk_count"],
                content_hash=r["content_hash"],
                created_at=r["created_at"],
            )
            for r in rows
        ]

    return DocumentListResponse(items=items, total=total, page=page, size=size)


@router.get("/{document_id}/chunks", response_model=ChunkListResponse)
async def list_chunks(
    document_id: str,
    user: Dict[str, Any] = Depends(require_role("viewer")),
):
    with get_db() as conn:
        doc = conn.execute("SELECT id FROM documents WHERE id = ?", (document_id,)).fetchone()
        if not doc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

        rows = conn.execute(
            """
            SELECT id, document_id, collection, chunk_index, text, heading, token_count, created_at
            FROM chunks WHERE document_id = ? ORDER BY chunk_index ASC
            """,
            (document_id,),
        ).fetchall()

        items = [
            ChunkResponse(
                id=r["id"],
                document_id=r["document_id"],
                collection=r["collection"],
                chunk_index=r["chunk_index"],
                text=r["text"],
                heading=r["heading"],
                token_count=r["token_count"],
                created_at=r["created_at"],
            )
            for r in rows
        ]

    return ChunkListResponse(items=items, total=len(items))


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: str,
    user: Dict[str, Any] = Depends(require_role("operator")),
):
    with get_db() as conn:
        row = conn.execute("SELECT name FROM documents WHERE id = ?", (document_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

        doc_name = row["name"]
        conn.execute("DELETE FROM chunks WHERE document_id = ?", (document_id,))
        conn.execute("DELETE FROM documents WHERE id = ?", (document_id,))

    log_audit_event(
        action="delete_document",
        user_id=user["user_id"],
        user_role=user["effective_role"],
        resource_id=document_id,
        details=f"Deleted document '{doc_name}'",
    )
    return None
