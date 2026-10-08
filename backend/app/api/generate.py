import json
import time
import uuid
from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException, status
from app.core.database import get_db, utc_now
from app.core.security import require_role
from app.models.schemas import (
    CitationItem,
    FaithfulnessMetrics,
    GenerateRequest,
    GenerateResponse,
)
from app.services.audit_service import log_audit_event
from app.services.citation_service import verify_grounded_citations
from app.services.llm_service import llm_service
from app.services.rag_engine import hybrid_search

router = APIRouter(prefix="/generate", tags=["generate"])


@router.post("", response_model=GenerateResponse)
async def generate_grounded_answer(
    req: GenerateRequest,
    user: Dict[str, Any] = Depends(require_role("viewer")),
):
    start_time = time.time()

    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT c.id, c.document_id, c.text, c.heading, c.embedding_json, d.name as document_name
            FROM chunks c
            JOIN documents d ON c.document_id = d.id
            WHERE c.collection = ?
            """,
            (req.collection,),
        ).fetchall()

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

    retrieved = hybrid_search(
        query=req.question,
        chunks=chunks,
        dense_weight=0.5,
        sparse_weight=0.5,
        top_k=req.top_k,
    )

    if not retrieved:
        return GenerateResponse(
            question=req.question,
            answer="No relevant documents found in this collection to answer the question.",
            citations=[],
            faithfulness=FaithfulnessMetrics(
                faithfulness_score=1.0,
                citation_precision=1.0,
                verified_claims_count=0,
                total_citations_count=0,
                advisory=True,
                summary="No context records retrieved.",
            ),
            provider="offline",
            model="deterministic-rule",
            execution_time_ms=round((time.time() - start_time) * 1000, 2),
        )

    # Format context for prompt
    context_str = "\n\n".join(
        f"[{i}] (Source: {r['document_name']})\n{r['text']}"
        for i, r in enumerate(retrieved, 1)
    )

    prompt = (
        f"Answer the following question using ONLY the provided context chunks. "
        f"Cite source chunks inline as [1], [2], etc. If the answer is not supported, state that explicitly.\n\n"
        f"CONTEXT:\n{context_str}\n\n"
        f"QUESTION: {req.question}"
    )

    system = "You are a factual, retrieval-augmented answer assistant. Never extrapolate beyond cited context."

    try:
        llm_out = await llm_service.generate_response(prompt, system, context_chunks=retrieved)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Grounded generation provider error: {str(e)}",
        )

    raw_answer = llm_out["answer"]
    citations_data, faith_metrics = verify_grounded_citations(raw_answer, retrieved)

    citation_items = [
        CitationItem(
            index=c["index"],
            chunk_id=c["chunk_id"],
            document_name=c["document_name"],
            snippet=c["snippet"],
            verified=c["verified"],
            overlap_score=c["overlap_score"],
        )
        for c in citations_data
    ]

    gen_id = f"gen-{uuid.uuid4().hex[:12]}"
    now = utc_now()
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO generations (id, query, answer, faithfulness_score, citation_precision, provider, model, citations_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                gen_id,
                req.question,
                raw_answer,
                faith_metrics["faithfulness_score"],
                faith_metrics["citation_precision"],
                llm_out["provider"],
                llm_out["model"],
                json.dumps([c.model_dump() for c in citation_items]),
                now,
            ),
        )

    log_audit_event(
        action="grounded_generate",
        user_id=user["user_id"],
        user_role=user["effective_role"],
        resource_id=gen_id,
        details=f"Grounded answer for query '{req.question[:50]}' (faithfulness: {faith_metrics['faithfulness_score']})",
    )

    return GenerateResponse(
        question=req.question,
        answer=raw_answer,
        citations=citation_items,
        faithfulness=FaithfulnessMetrics(**faith_metrics),
        provider=llm_out["provider"],
        model=llm_out["model"],
        execution_time_ms=round((time.time() - start_time) * 1000, 2),
    )
