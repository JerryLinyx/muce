"""In-process job registry for selection task lifecycle and SSE progress."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from threading import Lock
from typing import Any


@dataclass
class JobState:
    job_id: str
    status: str = "pending"  # pending | running | done | failed
    stage: str | None = None
    progress: float = 0.0
    message: str = ""
    result: Any | None = None
    error: str | None = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


class JobRegistry:
    def __init__(self, *, ttl_seconds: int = 3600) -> None:
        self._jobs: dict[str, JobState] = {}
        self._lock = Lock()
        self._ttl = ttl_seconds

    def create_job(self) -> str:
        job_id = uuid.uuid4().hex
        with self._lock:
            self._jobs[job_id] = JobState(job_id=job_id)
        return job_id

    def get(self, job_id: str) -> JobState:
        with self._lock:
            if job_id not in self._jobs:
                raise KeyError(job_id)
            return self._jobs[job_id]

    def update(self, job_id: str, **fields) -> None:
        with self._lock:
            state = self._jobs.get(job_id)
            if state is None:
                return
            for key, value in fields.items():
                setattr(state, key, value)
            state.updated_at = time.time()

    def complete(self, job_id: str, *, result: Any) -> None:
        self.update(
            job_id,
            status="done",
            progress=1.0,
            stage="done",
            result=result,
            message="完成",
        )

    def fail(self, job_id: str, *, error: str) -> None:
        self.update(job_id, status="failed", error=error, message=error)

    def purge_expired(self) -> None:
        cutoff = time.time() - self._ttl
        with self._lock:
            expired = [
                jid
                for jid, state in self._jobs.items()
                if state.updated_at < cutoff and state.status in {"done", "failed"}
            ]
            for jid in expired:
                self._jobs.pop(jid, None)
