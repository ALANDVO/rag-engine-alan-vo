import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator, Optional
from app.core.config import settings

_memory_keepalive: Optional[sqlite3.Connection] = None


def get_db_path() -> str:
    url = settings.database_url
    if url.startswith("sqlite:///"):
        path = url.replace("sqlite:///", "")
        if path != ":memory:":
            p = Path(path)
            p.parent.mkdir(parents=True, exist_ok=True)
        return path
    return ":memory:"


def get_connection() -> sqlite3.Connection:
    global _memory_keepalive
    path = get_db_path()
    if path == ":memory:":
        uri = "file:shared_memory_db?mode=memory&cache=shared"
        if _memory_keepalive is None:
            _memory_keepalive = sqlite3.connect(uri, uri=True, timeout=30.0, check_same_thread=False)
            _memory_keepalive.execute("PRAGMA foreign_keys = ON")
        conn = sqlite3.connect(uri, uri=True, timeout=30.0, check_same_thread=False)
    else:
        conn = sqlite3.connect(path, timeout=30.0, check_same_thread=False)
        conn.execute("PRAGMA journal_mode = WAL")

    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def get_db() -> Generator[sqlite3.Connection, None, None]:
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def init_db() -> None:
    with get_db() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS collections (
            name TEXT PRIMARY KEY,
            description TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS documents (
            id TEXT PRIMARY KEY,
            collection TEXT NOT NULL DEFAULT 'default',
            name TEXT NOT NULL,
            content_type TEXT NOT NULL,
            char_count INTEGER NOT NULL,
            chunk_count INTEGER NOT NULL,
            content_hash TEXT NOT NULL,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            FOREIGN KEY (collection) REFERENCES collections(name) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS chunks (
            id TEXT PRIMARY KEY,
            document_id TEXT NOT NULL,
            collection TEXT NOT NULL DEFAULT 'default',
            chunk_index INTEGER NOT NULL,
            text TEXT NOT NULL,
            heading TEXT NOT NULL DEFAULT '',
            token_count INTEGER NOT NULL DEFAULT 0,
            embedding_json TEXT NOT NULL DEFAULT '[]',
            content_hash TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE,
            FOREIGN KEY (collection) REFERENCES collections(name) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS generations (
            id TEXT PRIMARY KEY,
            query TEXT NOT NULL,
            answer TEXT NOT NULL,
            faithfulness_score REAL NOT NULL,
            citation_precision REAL NOT NULL,
            provider TEXT NOT NULL,
            model TEXT NOT NULL,
            citations_json TEXT NOT NULL DEFAULT '[]',
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            action TEXT NOT NULL,
            user_id TEXT NOT NULL,
            user_role TEXT NOT NULL,
            resource_id TEXT NOT NULL DEFAULT '',
            details TEXT NOT NULL DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS evaluations (
            id TEXT PRIMARY KEY,
            dataset_name TEXT NOT NULL,
            sample_count INTEGER NOT NULL,
            mrr REAL NOT NULL,
            hit_rate_1 REAL NOT NULL,
            hit_rate_3 REAL NOT NULL,
            hit_rate_5 REAL NOT NULL,
            precision_k REAL NOT NULL,
            avg_faithfulness REAL NOT NULL,
            metrics_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_chunks_collection ON chunks(collection);
        CREATE INDEX IF NOT EXISTS idx_chunks_document ON chunks(document_id);
        CREATE INDEX IF NOT EXISTS idx_documents_collection ON documents(collection);
        CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON audit_logs(timestamp);
        """)

        # Ensure default collection exists
        now = utc_now()
        conn.execute(
            """
            INSERT OR IGNORE INTO collections (name, description, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            """,
            ("default", "Default RAG document collection", now, now)
        )
