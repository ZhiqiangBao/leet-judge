from __future__ import annotations

import asyncio
import json
from collections.abc import Callable, Coroutine
from typing import Any, TypeVar

from sqlalchemy.orm import Session

from ..config import judge_slots
from ..db import SessionLocal
from ..models import Submission
from .engine import apply_result, judge_source

_queue: asyncio.Queue[int] | None = None
_slots: asyncio.Semaphore | None = None
_tasks: list[asyncio.Task] = []

T = TypeVar("T")


def queue() -> asyncio.Queue[int]:
    global _queue
    if _queue is None:
        _queue = asyncio.Queue()
    return _queue


def _ensure_slots() -> asyncio.Semaphore:
    global _slots
    if _slots is None:
        _slots = asyncio.Semaphore(judge_slots())
    return _slots


async def run_judge(fn: Callable[..., T], /, *args: Any, **kwargs: Any) -> T:
    """Run a blocking judge job under the process-wide slot cap."""
    async with _ensure_slots():
        return await asyncio.to_thread(fn, *args, **kwargs)


async def _worker() -> None:
    q = queue()
    while True:
        sub_id = await q.get()
        try:
            await run_judge(_judge_one, sub_id)
        except Exception as exc:
            _mark_internal_error(sub_id, str(exc))
        finally:
            q.task_done()


def _mark_internal_error(sub_id: int, message: str) -> None:
    db = SessionLocal()
    try:
        sub = db.get(Submission, sub_id)
        if not sub:
            return
        sub.status = "done"
        sub.verdict = "RE"
        sub.details_json = json.dumps({"message": f"internal judge error: {message}"}, ensure_ascii=False)
        db.commit()
    finally:
        db.close()


def _judge_one(sub_id: int) -> None:
    db: Session = SessionLocal()
    try:
        sub = db.get(Submission, sub_id)
        if not sub:
            return
        sub.status = "running"
        db.commit()
        result = judge_source(sub.problem_slug, sub.language, sub.source)
        apply_result(sub, result)
        db.commit()
    finally:
        db.close()


def start_worker() -> Coroutine:
    async def _run():
        await spawn_worker()
        if _tasks:
            await asyncio.gather(*_tasks)

    return _run()


async def spawn_worker() -> None:
    await stop_worker()
    n = judge_slots()
    global _slots
    _slots = asyncio.Semaphore(n)
    for _ in range(n):
        _tasks.append(asyncio.create_task(_worker()))


async def stop_worker() -> None:
    global _slots
    pending = list(_tasks)
    _tasks.clear()
    for task in pending:
        task.cancel()
    if pending:
        await asyncio.gather(*pending, return_exceptions=True)
    _slots = None


def reset_runtime() -> None:
    """Drop queue/slot state. Tests only; workers must already be stopped."""
    global _queue, _slots
    _queue = None
    _slots = None
    _tasks.clear()


async def enqueue(submission_id: int) -> None:
    await queue().put(submission_id)
