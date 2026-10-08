import time
from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException, status
from app.core.database import get_db
from app.core.security import require_role
from app.models.schemas import SearchRequest, SearchResponse, SearchResultItem
from app.services.rag_engine import hybrid_search

router = APIRouter(prefix="/search", tags=["search"])


@router.post("", response_model=SearchResponse)
async def perform_search(
    req: SearchRequest,
    user: Dict[str, Any] = Depends(require_role("viewer")),
):
    start_time = time.time()

    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT c.id, c.document_id, c.collection, c.chunk_index, c.text, c.heading, c.embedding_json,
                   d.name as document_name
            FROM chunks c
            JOIN documents d ON c.document_id = d.id
            WHERE c.collection = ?
            """,
            (req.collection,),
        ).fetchall()

    if not rows:
        return SearchResponse(
            query=req.query,
            collection=req.collection,
            total_results=0,
            results=[],
            search_time_ms=round((time.time() - start_time) * 1000, 2),
        )

    chunks = [
        {
            "id": r["id"],
            "document_id": r["document_id"],
            "document_name": r["document_name"],
            "text": r["text"],
            "heading": r["heading"],
            "embedding": r["embedding_json"],
        }
        for r in rows
    ]

    scored = hybrid_search(
        query=req.query,
        chunks=chunks,
        dense_weight=req.dense_weight,
        sparse_weight=req.sparse_weight,
        top_k=req.top_k,
        min_score=req.min_score,
    )

    items = [
        SearchResultItem(
            rank=s["rank"],
            chunk_id=s["chunk_id"],
            document_id=s["document_id"],
            document_name=s["document_name"],
            score=s["score"],
            dense_score=s["dense_score"],
            sparse_score=s["sparse_score"],
            text=s["text"],
            heading=s["heading"],
        )
        for s in scored
    ]

    return SearchResponse(
        query=req.query,
        collection=req.collection,
        total_results=len(items),
        results=items,
        search_time_ms=round((time.time() - start_time) * 1000, 2),
    )
