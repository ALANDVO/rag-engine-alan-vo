import json
from typing import Any, Dict, List, Optional, Tuple
from app.core.database import get_db, utc_now
from app.models.schemas import AuditLogEntry, StatsResponse


def log_audit_event(
    action: str,
    user_id: str,
    user_role: str,
    resource_id: str = "",
    details: str = ""
) -> None:
    now = utc_now()
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO audit_logs (timestamp, action, user_id, user_role, resource_id, details)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (now, action, user_id, user_role, resource_id, details)
        )


def get_audit_logs(
    page: int = 1,
    size: int = 20,
    action: Optional[str] = None
) -> Tuple[List[AuditLogEntry], int]:
    offset = (page - 1) * size
    query = "SELECT id, timestamp, action, user_id, user_role, resource_id, details FROM audit_logs"
    count_query = "SELECT COUNT(*) FROM audit_logs"
    params: List[Any] = []

    if action:
        query += " WHERE action = ?"
        count_query += " WHERE action = ?"
        params.append(action)

    query += " ORDER BY id DESC LIMIT ? OFFSET ?"
    params_paged = params + [size, offset]

    with get_db() as conn:
        total = conn.execute(count_query, params).fetchone()[0]
        rows = conn.execute(query, params_paged).fetchall()

        entries = [
            AuditLogEntry(
                id=r["id"],
                timestamp=r["timestamp"],
                action=r["action"],
                user_id=r["user_id"],
                user_role=r["user_role"],
                resource_id=r["resource_id"],
                details=r["details"]
            )
            for r in rows
        ]

    return entries, total


def get_system_stats() -> StatsResponse:
    with get_db() as conn:
        total_docs = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
        total_chunks = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
        total_colls = conn.execute("SELECT COUNT(*) FROM collections").fetchone()[0]
        total_gens = conn.execute("SELECT COUNT(*) FROM generations").fetchone()[0]

        avg_faith_row = conn.execute("SELECT AVG(faithfulness_score) FROM generations").fetchone()
        avg_faith = avg_faith_row[0] if (avg_faith_row and avg_faith_row[0] is not None) else 1.0

    return StatsResponse(
        total_documents=total_docs,
        total_chunks=total_chunks,
        total_collections=total_colls,
        total_generations=total_gens,
        avg_faithfulness=round(avg_faith, 4)
    )
