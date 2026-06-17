"""A tiny file-based job queue — the "signal" between the board and your agent.

A button press writes a job file into a queue directory. A separate, always-on
process (e.g. a Claude Code agent) watches that directory, dispatches each
prompt to a subagent, and writes the job's status back. The board polls the same
files to drive its LED feedback (running / complete / error).

The contract is just a JSON file per job::

    {
      "id": "1718650000-ab12cd",
      "prompt": "Summarise today's commits",
      "button": [0, 1],
      "label": "standup",
      "status": "pending",        # pending -> running -> done | error
      "created": 1718650000.0,
      "finished": null,
      "result": null              # optional text the dispatcher writes back
    }

Files are written atomically (temp file + rename) so a reader never sees a
half-written job. Nothing here imports MIDI, so the queue is independently
testable and usable from any process.
"""

from __future__ import annotations

import json
import os
import secrets
import time
from dataclasses import asdict, dataclass
from pathlib import Path

PENDING = "pending"
RUNNING = "running"
DONE = "done"
ERROR = "error"
TERMINAL = (DONE, ERROR)

DEFAULT_DIR = Path(os.environ.get("STAUNCHPAD_QUEUE",
                                  Path.home() / ".staunchpad" / "queue"))


@dataclass
class Job:
    id: str
    prompt: str
    button: tuple[int, int] | None = None
    label: str | None = None
    status: str = PENDING
    created: float = 0.0
    finished: float | None = None
    result: str | None = None

    @property
    def is_terminal(self) -> bool:
        return self.status in TERMINAL


class JobQueue:
    """File-backed queue of prompt jobs shared between the board and a dispatcher."""

    def __init__(self, directory: str | Path = DEFAULT_DIR):
        self.dir = Path(directory)
        self.dir.mkdir(parents=True, exist_ok=True)

    # -- paths --------------------------------------------------------------
    def _path(self, job_id: str) -> Path:
        return self.dir / f"{job_id}.json"

    def _write(self, job: Job) -> None:
        data = asdict(job)
        if data["button"] is not None:
            data["button"] = list(data["button"])
        tmp = self._path(job.id).with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2))
        os.replace(tmp, self._path(job.id))   # atomic

    # -- producer side (the board) -----------------------------------------
    def submit(self, prompt: str, button=None, label: str | None = None) -> str:
        """Enqueue a prompt. Returns the new job id."""
        job_id = f"{int(time.time())}-{secrets.token_hex(3)}"
        self._write(Job(id=job_id, prompt=prompt,
                        button=tuple(button) if button else None,
                        label=label, status=PENDING, created=time.time()))
        return job_id

    # -- shared reads -------------------------------------------------------
    def read(self, job_id: str) -> Job | None:
        path = self._path(job_id)
        if not path.exists():
            return None
        try:
            d = json.loads(path.read_text())
        except (json.JSONDecodeError, FileNotFoundError):
            return None
        if d.get("button") is not None:
            d["button"] = tuple(d["button"])
        return Job(**d)

    def status(self, job_id: str) -> str | None:
        job = self.read(job_id)
        return job.status if job else None

    def jobs(self) -> list[Job]:
        out = []
        for p in sorted(self.dir.glob("*.json")):
            try:
                d = json.loads(p.read_text())
                if d.get("button") is not None:
                    d["button"] = tuple(d["button"])
                out.append(Job(**d))
            except Exception:
                continue
        return out

    def pending(self) -> list[Job]:
        return [j for j in self.jobs() if j.status == PENDING]

    # -- consumer side (the dispatcher) ------------------------------------
    def set_status(self, job_id: str, status: str, result: str | None = None) -> None:
        job = self.read(job_id)
        if not job:
            return
        job.status = status
        if result is not None:
            job.result = result
        if status in TERMINAL:
            job.finished = time.time()
        self._write(job)

    def claim(self, job: Job) -> bool:
        """Mark a pending job running. Returns False if already claimed."""
        current = self.read(job.id)
        if not current or current.status != PENDING:
            return False
        self.set_status(job.id, RUNNING)
        return True

    def archive(self, job_id: str) -> None:
        """Remove a finished job file."""
        self._path(job_id).unlink(missing_ok=True)
