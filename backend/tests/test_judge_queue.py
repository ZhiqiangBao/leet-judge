from __future__ import annotations

import asyncio
import threading
import time

from app.config import judge_slots
from app.judge import queue as jq


def test_judge_slots_default_and_clamp(monkeypatch):
    monkeypatch.delenv("LOCAL_LEET_JUDGE_SLOTS", raising=False)
    assert judge_slots() == 2
    monkeypatch.setenv("LOCAL_LEET_JUDGE_SLOTS", "0")
    assert judge_slots() == 1
    monkeypatch.setenv("LOCAL_LEET_JUDGE_SLOTS", "99")
    assert judge_slots() == 8
    monkeypatch.setenv("LOCAL_LEET_JUDGE_SLOTS", "nope")
    assert judge_slots() == 2


def test_run_judge_caps_concurrent_jobs(monkeypatch):
    monkeypatch.setenv("LOCAL_LEET_JUDGE_SLOTS", "2")
    jq.reset_runtime()
    current = 0
    peak = 0
    lock = threading.Lock()

    def work() -> None:
        nonlocal current, peak
        with lock:
            current += 1
            peak = max(peak, current)
        time.sleep(0.05)
        with lock:
            current -= 1

    async def go() -> None:
        await asyncio.gather(*[jq.run_judge(work) for _ in range(6)])

    asyncio.run(go())
    assert peak == 2
    jq.reset_runtime()
