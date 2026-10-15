import uuid
from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException, Query, status
from app.core.database import get_db, utc_now
from app.core.security import require_role
from app.models.schemas import (
    CollectionCreate,
    CollectionListResponse,
    CollectionResponse,
)
from app.services.audit_service import log_audit_event

router = APIRouter(prefix="/collections", tags=["collections"])


@router.post("", response_model=CollectionResponse, status_code=status.HTTP_201_CREATED)
async def create_collection(
    coll: CollectionCreate,
    user: Dict[str, Any] = Depends(require_role("operator")),
):
    if not coll.name.strip():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Collection name cannot be empty")

    now = utc_now()
    with get_db() as conn:
        existing = conn.execute("SELECT name FROM collections WHERE name = ?", (coll.name,)).fetchone()
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Collection '{coll.name}' already exists")

        conn.execute(
            """
            INSERT INTO collections (name, description, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            """,
            (coll.name, coll.description, now, now),
        )

    log_audit_event(
        action="create_collection",
        user_id=user["user_id"],
        user_role=user["effective_role"],
        resource_id=coll.name,
        details=f"Created collection '{coll.name}'",
    )

    return CollectionResponse(
        name=coll.name,
        description=coll.description,
        document_count=0,
        created_at=now,
        updated_at=now,
    )


@router.get("", response_model=CollectionListResponse)
async def list_collections(
    user: Dict[str, Any] = Depends(require_role("viewer")),
):
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT c.name, c.description, c.created_at, c.updated_at,
                   COUNT(d.id) as document_count
            FROM collections c
            LEFT JOIN documents d ON d.collection = c.name
            GROUP BY c.name, c.description, c.created_at, c.updated_at
            ORDER BY c.name
            """
        ).fetchall()

    items = [
        CollectionResponse(
            name=r["name"],
            description=r["description"],
            document_count=r["document_count"],
            created_at=r["created_at"],
            updated_at=r["updated_at"],
        )
        for r in rows
    ]

    return CollectionListResponse(items=items, total=len(items))


@router.delete("/{collection_name}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_collection(
    collection_name: str,
    user: Dict[str, Any] = Depends(require_role("admin")),
):
    if collection_name == "default":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete the default collection")

    with get_db() as conn:
        existing = conn.execute("SELECT name FROM collections WHERE name = ?", (collection_name,)).fetchone()
        if not existing:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Collection '{collection_name}' not found")

        # Check if collection has documents
        doc_count = conn.execute("SELECT COUNT(*) FROM documents WHERE collection = ?", (collection_name,)).fetchone()[0]
        if doc_count > 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Collection '{collection_name}' contains {doc_count} document(s). Delete or move documents first.",
            )

        conn.execute("DELETE FROM collections WHERE name = ?", (collection_name,))

    log_audit_event(
        action="delete_collection",
        user_id=user["user_id"],
        user_role=user["effective_role"],
        resource_id=collection_name,
        details=f"Deleted collection '{collection_name}'",
    )

    return None