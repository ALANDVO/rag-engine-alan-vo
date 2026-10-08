import json
import uuid
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, status
from app.core.database import get_db, utc_now
from app.core.security import require_role
from app.models.schemas import (
    EvaluationMetricSummary,
    EvaluationResultResponse,
    EvaluationRunRequest,
)
from app.services.audit_service import log_audit_event
from app.services.evaluation_service import run_evaluation

router = APIRouter(prefix="/evaluation", tags=["evaluation"])


@router.post("/run", response_model=EvaluationResultResponse)
async def execute_evaluation_benchmark(
    req: EvaluationRunRequest,
    user: Dict[str, Any] = Depends(require_role("operator")),
):
    res = run_evaluation(top_k=req.top_k)
    metrics = res["metrics"]
    eval_id = f"eval-{uuid.uuid4().hex[:12]}"
    now = utc_now()

    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO evaluations (id, dataset_name, sample_count, mrr, hit_rate_1, hit_rate_3, hit_rate_5, precision_k, avg_faithfulness, metrics_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                eval_id,
                res["dataset_name"],
                metrics["total_samples"],
                metrics["mrr"],
                metrics["hit_rate_1"],
                metrics["hit_rate_3"],
                metrics["hit_rate_5"],
                metrics["precision_k"],
                metrics["avg_faithfulness"],
                json.dumps(res),
                now,
            ),
        )

    log_audit_event(
        action="run_evaluation",
        user_id=user["user_id"],
        user_role=user["effective_role"],
        resource_id=eval_id,
        details=f"Ran evaluation '{res['dataset_name']}' - MRR: {metrics['mrr']}, Hit@1: {metrics['hit_rate_1']}",
    )

    return EvaluationResultResponse(
        id=eval_id,
        dataset_name=res["dataset_name"],
        metrics=EvaluationMetricSummary(**metrics),
        sample_details=res["sample_details"],
        run_at=now,
    )


@router.get("/history", response_model=List[EvaluationResultResponse])
async def list_evaluation_history(
    user: Dict[str, Any] = Depends(require_role("viewer")),
):
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT id, dataset_name, metrics_json, created_at
            FROM evaluations ORDER BY created_at DESC LIMIT 20
            """
        ).fetchall()

    history = []
    for r in rows:
        data = json.loads(r["metrics_json"])
        history.append(
            EvaluationResultResponse(
                id=r["id"],
                dataset_name=r["dataset_name"],
                metrics=EvaluationMetricSummary(**data["metrics"]),
                sample_details=data.get("sample_details", []),
                run_at=r["created_at"],
            )
        )
    return history
