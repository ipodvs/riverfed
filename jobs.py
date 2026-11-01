"""Async job queue for the Riverfed server.

Why: convert / ingest / studio used to run inside the HTTP request, holding
one fetch open for minutes. Browsers drop long fetches, so the UI showed a
stale "Ingesting…" banner with no way to tell a finished job from a hung one
— every "is it stuck?" incident traced back to this. Jobs decouple the work
from the request: POST returns a job id immediately, the UI polls
GET /jobs/<id> for state + live log tail.

Design (deliberately minimal — stdlib only, in-memory):
- LANES serialize work the same way the old locks did: everything wiki-mutating
  ("wiki" lane: ingest, review) runs one-at-a-time IN ORDER — a second click
  queues instead of being rejected. convert and studio get their own lanes.
- One daemon worker thread per lane, started lazily.
- A job's `runner` is a callable(job) -> result dict supplied by server.py
  (which owns all domain logic: command construction, parsing, auth). The
  runner streams progress via job.emit(line).
- In-memory only: a server restart forgets history (the subprocesses
  themselves are killed with the server anyway). Finished jobs are pruned
  beyond the most recent 100.
"""
from __future__ import annotations

import itertools
import queue
import threading
import time
import uuid
from collections import deque
from datetime import datetime

LOG_MAX_LINES = 400
KEEP_FINISHED = 100

_seq = itertools.count(1)


def _iso(ts: float | None) -> str | None:
    if ts is None:
        return None
    return datetime.fromtimestamp(ts).isoformat(timespec="seconds")


class Job:
    def __init__(self, kind: str, lane: str, label: str, runner):
        self.id = uuid.uuid4().hex[:12]
        self.seq = next(_seq)
        self.kind = kind
        self.lane = lane
        self.label = label
        self.runner = runner
        self.state = "queued"            # queued | running | done | error
        self.created_at = time.time()
        self.started_at: float | None = None
        self.finished_at: float | None = None
        self.log: deque[str] = deque(maxlen=LOG_MAX_LINES)
        self.result: dict | None = None
        self.error: str | None = None

    def emit(self, line: str) -> None:
        """Progress callback handed to runners (and safe from reader threads)."""
        self.log.append(line)


class JobManager:
    def __init__(self):
        self._lock = threading.Lock()
        self._jobs: dict[str, Job] = {}
        self._queues: dict[str, queue.Queue] = {}
        self._workers: dict[str, threading.Thread] = {}

    # ---- submission ----

    def submit(self, kind: str, lane: str, runner, label: str = "") -> str:
        job = Job(kind, lane, label, runner)
        with self._lock:
            self._jobs[job.id] = job
            q = self._queues.get(lane)
            if q is None:
                q = self._queues[lane] = queue.Queue()
            worker = self._workers.get(lane)
            if worker is None or not worker.is_alive():
                worker = threading.Thread(
                    target=self._work, args=(lane,), daemon=True,
                    name=f"job-worker-{lane}")
                self._workers[lane] = worker
                worker.start()
        q.put(job.id)
        return job.id

    # ---- worker loop ----

    def _work(self, lane: str) -> None:
        q = self._queues[lane]
        while True:
            job_id = q.get()
            job = self._jobs.get(job_id)
            if job is None:
                continue
            job.state = "running"
            job.started_at = time.time()
            try:
                result = job.runner(job) or {}
                job.result = result
                if result.get("success"):
                    job.state = "done"
                else:
                    job.state = "error"
                    job.error = str(result.get("error") or "failed")
            except Exception as exc:  # a runner bug must not kill the worker
                job.state = "error"
                job.error = f"{type(exc).__name__}: {exc}"
            finally:
                job.finished_at = time.time()
                self._prune()

    # ---- inspection ----

    def lane_active(self, lane: str) -> dict | None:
        """The queued/running job on a lane ({id, kind, label, state}), or
        None when idle. Lets /pending tell the UI an ingest/review is still
        in flight — the pending list empties as soon as the agent writes
        the source page, minutes before the job actually finishes, so
        "Wiki is up to date" alone would lie mid-run."""
        with self._lock:
            active = [j for j in self._jobs.values()
                      if j.lane == lane and j.state in ("queued", "running")]
        if not active:
            return None
        j = min(active, key=lambda x: x.seq)
        return {"id": j.id, "kind": j.kind, "label": j.label,
                "state": j.state}

    def snapshot(self, job_id: str, log_tail: int = 30) -> dict | None:
        job = self._jobs.get(job_id)
        if job is None:
            return None
        snap = {
            "id": job.id,
            "kind": job.kind,
            "label": job.label,
            "state": job.state,
            "created_at": _iso(job.created_at),
            "started_at": _iso(job.started_at),
            "finished_at": _iso(job.finished_at),
            "log_tail": list(job.log)[-log_tail:],
            "result": job.result,
            "error": job.error,
        }
        if job.state == "queued":
            with self._lock:
                ahead = sum(
                    1 for j in self._jobs.values()
                    if j.lane == job.lane and j.state == "queued" and j.seq < job.seq)
            snap["queue_position"] = ahead
        return snap

    def list(self, limit: int = 20) -> list[dict]:
        with self._lock:
            jobs = sorted(self._jobs.values(), key=lambda j: j.seq, reverse=True)
        out = []
        for j in jobs[:limit]:
            out.append({
                "id": j.id, "kind": j.kind, "label": j.label, "state": j.state,
                "created_at": _iso(j.created_at),
                "finished_at": _iso(j.finished_at),
            })
        return out

    def _prune(self) -> None:
        with self._lock:
            finished = [j for j in self._jobs.values()
                        if j.state in ("done", "error")]
            if len(finished) <= KEEP_FINISHED:
                return
            finished.sort(key=lambda j: j.seq)
            for j in finished[:-KEEP_FINISHED]:
                self._jobs.pop(j.id, None)
