import sqlite3
import json
import os
import logging
import time 
from datetime import datetime 
from typing import Optional, List, Dict 
from enum import Enum 

logger = logging.getLogger(__name__)

DB_PATH = os.getenv("QUEUE_DB_PATH", "retry_queue.db")

class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED = "failed"
    DEAD = "dead" # failed too many times - giving up

def init_db():
    """Create the queue database table if it does not exist."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS job_queue (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                filename            TEXT NOT NULL,
                status              TEXT NOT NULL DEFAULT 'pending',
                attempt_count       INTEGER DEFAULT 0,
                max_attempts        INTEGER DEFAULT 3,
                error_message       TEXT,
                result_json         TEXT,
                created_at          TEXT NOT NULL,
                updated_at          TEXT NOT NULL
            )
        """)
        conn.commit()
    logger.info(f"Queue database initialized at {DB_PATH}")
    
def add_job(filename: str, max_attempts: int = 3) -> int:
    """Add a new job to the queue. Returns the job ID."""
    now = datetime.utcnow().isoformat()
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute(
            """
            INSERT INTO job_queue (filename, status, attempt_count, max_attempts, created_at, updated_at)
            VALUES (?, 'pending', 0, ?, ?, ?)
            """,
            (filename, max_attempts, now, now)
        )
        conn.commit()
        job_id = cursor.lastrowid
    logger.info(f"Add job {job_id} for file: {filename}")
    return job_id
    
def update_job(job_id: int, status: JobStatus, error: str = None, result: dict = None):
    """Update a job's status after processing."""
    now = datetime.utcnow().isoformat()
    result_json = json.dumps(result) if result else None

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            UPDATE job_queue
            SET status = ?, error_message = ?, result_json = ?,
                attempt_count = attempt_count + 1, updated_at = ?
            WHERE id = ?
            """,
            (status.value, error, result_json, now, job_id)
        )
        conn.commit()
    logger.info(f"Updated job {job_id} → {status.value}")
    
def get_pending_job() -> List[Dict]:
    """Fetch all jobs that are pending or stuck in 'processing' for too long."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT * FROM job_queue
            WHERE status IN ('pending', 'failed')
            AND attempt_count < max_attempts
            ORDER BY created_at ASC                """
        ).fetchall()
    return [dict(row) for row in rows]
    
def get_job(job_id: int) -> Optional[Dict]:
    """Get a specific job by ID."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM job_queue WHERE id = ?", (job_id,)
        ).fetchone()
    return dict(row) if row else None
    
def get_all_jobs(limit: int = 50) -> List[Dict]:
    """Get recent jobs for the dashboard display."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM job_queue ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(row) for row in rows]

def get_job_result(job_id: int) -> Optional[dict]:
    """
    Fetch the stored result JSON for a completed job.
    Returns the parsed dict or None if not found / not completed.
    """
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT result_json, filename FROM job_queue WHERE id = ?",
            (job_id,)
        ).fetchone()
    if not row or not row["result_json"]:
        return None
    return {"result": json.loads(row["result_json"]), "filename": row["filename"]}

def mark_dead_jobs():
    """Mark jobs that have exceeded max attempts as 'dead' (permanently failed)."""
    now = datetime.utcnow().isoformat()
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            UPDATE job_queue
            SET status = 'dead', updated_at = ?
            WHERE status = 'failed' AND attempt_count >= max_attempts
            """,
            (now,)
        )
        conn.commit()

init_db()