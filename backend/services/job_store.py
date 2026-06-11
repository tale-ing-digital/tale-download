"""
File-based job store for async ZIP generation jobs.

Why file-based and not in-memory:
  Uvicorn runs with --workers 4 (4 separate OS processes). An in-memory dict is
  NOT shared across processes. A client might POST /jobs/zip (worker A creates the
  task) and then GET /jobs/{id}/status (hitting worker B, which has no knowledge of
  the job). File-based storage on a shared temp directory solves this transparently.

Job lifecycle:
  queued → processing → done | error

Files per job:
  /tmp/tale_download_jobs/{job_id}.json   — status / progress metadata
  /tmp/tale_download_jobs/{job_id}.zip    — result (only when status == "done")

Jobs expire (and files are deleted) TTL_MINUTES after completion.
"""

import io
import json
import os
import tempfile
import time
from typing import Optional

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

TTL_MINUTES: int = 20

_JOB_DIR: str = os.path.join(tempfile.gettempdir(), "tale_download_jobs")
os.makedirs(_JOB_DIR, exist_ok=True)


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

def _state_path(job_id: str) -> str:
    return os.path.join(_JOB_DIR, f"{job_id}.json")


def _zip_path(job_id: str) -> str:
    return os.path.join(_JOB_DIR, f"{job_id}.zip")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def put_job(job_id: str, project_code: str) -> None:
    """Create a new job in 'queued' state."""
    state = {
        "job_id": job_id,
        "project_code": project_code,
        "status": "queued",
        "done": 0,
        "total": 0,
        "error": None,
        "created_at": time.time(),
        "finished_at": None,
    }
    with open(_state_path(job_id), "w", encoding="utf-8") as f:
        json.dump(state, f)


def get_job(job_id: str) -> Optional[dict]:
    """Return job state dict, or None if the job does not exist."""
    path = _state_path(job_id)
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def update_job(job_id: str, **kwargs) -> None:
    """Atomically update fields in the job state."""
    job = get_job(job_id)
    if job is None:
        return
    job.update(kwargs)
    tmp = _state_path(job_id) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(job, f)
    os.replace(tmp, _state_path(job_id))  # atomic on POSIX


def set_job_done(job_id: str, zip_buffer: io.BytesIO) -> None:
    """Persist the ZIP to disk and mark the job as done."""
    zip_buffer.seek(0)
    with open(_zip_path(job_id), "wb") as f:
        f.write(zip_buffer.read())
    update_job(job_id, status="done", finished_at=time.time())


def set_job_error(job_id: str, error: str) -> None:
    """Mark the job as failed with an error message."""
    update_job(job_id, status="error", error=error, finished_at=time.time())


def get_zip_path(job_id: str) -> Optional[str]:
    """Return the path to the completed ZIP, or None if it does not exist."""
    path = _zip_path(job_id)
    return path if os.path.exists(path) else None


def cleanup_old_jobs() -> int:
    """
    Delete state files and ZIP files for jobs completed more than TTL_MINUTES ago.
    Returns the number of jobs removed.
    """
    now = time.time()
    cutoff = TTL_MINUTES * 60
    removed = 0
    try:
        for fname in os.listdir(_JOB_DIR):
            if not fname.endswith(".json"):
                continue
            job_id = fname[:-5]
            try:
                job = get_job(job_id)
                finished_at = job.get("finished_at") if job else None
                if finished_at and (now - finished_at) > cutoff:
                    try:
                        os.remove(_state_path(job_id))
                    except OSError:
                        pass
                    zip_p = _zip_path(job_id)
                    if os.path.exists(zip_p):
                        try:
                            os.remove(zip_p)
                        except OSError:
                            pass
                    removed += 1
            except Exception:
                pass
    except Exception:
        pass
    return removed
