from __future__ import annotations

import json
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

from ..config import DATA_DIR
from ..services.problems import bank, jsonl_top_bool, parse_test_line
from .hints import attach_hint
from .languages import get_adapter
from .sandbox import run_limited

MAX_LOG = 8000


class _HintCases:
    """Parse a single jsonl line only when attach_hint asks for that index."""

    def __init__(self, problem, count: int) -> None:
        self._problem = problem
        self._count = count

    def __len__(self) -> int:
        return self._count

    def __getitem__(self, index: int):
        return self._problem.test_at(index)


def _feed_hidden(problem) -> tuple:
    flags: list[bool] = []
    public_by_index: dict[int, Any] = {}

    def lines():
        for i, line in enumerate(problem.iter_test_lines()):
            hidden = jsonl_top_bool(line)
            flags.append(hidden)
            if not hidden:
                public_by_index[i] = parse_test_line(line)
            yield line

    return lines(), flags, public_by_index


def _last_json(stdout: str) -> dict[str, Any] | None:
    for line in reversed(stdout.splitlines()):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            return obj
    return None


def _public_details(
    raw: dict[str, Any],
    hidden_flags: list[bool] | tuple[bool, ...],
    public_by_index: dict[int, Any],
    *,
    reveal_public: bool = False,
) -> dict[str, Any]:
    details = {
        "verdict": raw.get("verdict"),
        "passed": raw.get("passed"),
        "total": len(hidden_flags),
        "message": raw.get("message"),
        "failed_index": raw.get("failed_index"),
        "cases": [],
    }
    failed_index = raw.get("failed_index")
    passed_count = int(raw.get("passed") or 0)
    cases = []
    for i, hidden in enumerate(hidden_flags):
        passed = raw.get("verdict") == "AC" or i < passed_count
        if failed_index is not None and i == failed_index:
            passed = False
        case: dict[str, Any] = {"index": i, "passed": passed, "hidden": bool(hidden)}
        show = (not hidden) and (reveal_public or not passed or failed_index == i)
        if show and not hidden:
            test = public_by_index[i]
            case["args"] = test.args
            case["expected"] = test.expected
            if failed_index is not None and i == failed_index:
                if "got" in raw:
                    case["got"] = raw["got"]
                if raw.get("message"):
                    case["message"] = raw["message"]
        cases.append(case)
    details["cases"] = cases
    return details


def _with_hint(
    details: dict[str, Any],
    tests: list,
    verdict: str,
    n_max: int | None,
    *,
    public_only: bool,
    params=None,
) -> dict[str, Any]:
    return attach_hint(details, tests, verdict, n_max, public_only=public_only, params=params)


def judge_source(
    problem_slug: str,
    language: str,
    source: str,
    public_only: bool = False,
) -> dict[str, Any]:
    adapter = get_adapter(language)
    if adapter is None:
        return {"verdict": "NA", "details": {"message": f"未知语言: {language}"}, "compile_log": None, "time_ms": 0}
    if not adapter.implemented:
        return {
            "verdict": "NA",
            "details": {"message": f"{adapter.display_name} 接口已保留，尚未实现评测"},
            "compile_log": None,
            "time_ms": 0,
        }
    if not adapter.detect():
        return {
            "verdict": "NA",
            "details": {"message": f"{adapter.display_name} 运行时未安装"},
            "compile_log": None,
            "time_ms": 0,
        }

    problem = bank.get(problem_slug)
    signature = problem.signature.model_dump()
    tmp_root = DATA_DIR / "tmp"
    tmp_root.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="job-", dir=tmp_root) as td:
        workdir = Path(td)
        wrapped = adapter.wrap(source, signature)
        (workdir / adapter.source_filename).write_text(wrapped, encoding="utf-8")
        compiled = adapter.compile(str(workdir))
        if not compiled.ok:
            return {
                "verdict": "CE",
                "details": {"message": "编译失败"},
                "compile_log": (compiled.log or "")[-MAX_LOG:],
                "time_ms": 0,
            }
        if public_only:
            public = problem.public_tests()
            if not public:
                return {
                    "verdict": "NA",
                    "details": {"message": "本题没有公开测例"},
                    "compile_log": compiled.log,
                    "time_ms": 0,
                }
            hidden_flags: tuple[bool, ...] | list[bool] = tuple(False for _ in public)
            public_by_index = {i: t for i, t in enumerate(public)}
            hint_tests: list | _HintCases = public
            stdin = problem.tests_stdin(public_only=True)
            run = run_limited(
                adapter.run_argv(str(workdir)),
                cwd=workdir,
                stdin=stdin,
                time_ms=problem.time_limit_ms,
                memory_mb=problem.memory_limit_mb,
            )
        else:
            feed, flag_buf, public_by_index = _feed_hidden(problem)
            run = run_limited(
                adapter.run_argv(str(workdir)),
                cwd=workdir,
                stdin_lines=feed,
                time_ms=problem.time_limit_ms,
                memory_mb=problem.memory_limit_mb,
            )
            hidden_flags = flag_buf
            hint_tests = _HintCases(problem, len(flag_buf))
        if run.tle:
            return {
                "verdict": "TLE",
                "details": _with_hint(
                    {"message": "超出时间限制", "total": len(hint_tests)},
                    hint_tests,
                    "TLE",
                    problem.n_max,
                    public_only=public_only,
                    params=problem.signature.params,
                ),
                "compile_log": compiled.log,
                "time_ms": problem.time_limit_ms,
            }
        if run.mle:
            return {
                "verdict": "MLE",
                "details": _with_hint(
                    {"message": "超出内存限制", "total": len(hint_tests)},
                    hint_tests,
                    "MLE",
                    problem.n_max,
                    public_only=public_only,
                    params=problem.signature.params,
                ),
                "compile_log": compiled.log,
                "time_ms": run.time_ms,
            }
        payload = _last_json(run.stdout)
        if run.returncode != 0 and not payload:
            return {
                "verdict": "RE",
                "details": _with_hint(
                    {
                        "message": (run.stderr or run.stdout or "runtime error")[-MAX_LOG:],
                        "total": len(hint_tests),
                    },
                    hint_tests,
                    "RE",
                    problem.n_max,
                    public_only=public_only,
                    params=problem.signature.params,
                ),
                "compile_log": compiled.log,
                "time_ms": run.time_ms,
            }
        if not payload:
            return {
                "verdict": "RE",
                "details": _with_hint(
                    {"message": "评测输出无法解析", "stderr": run.stderr[-2000:]},
                    hint_tests,
                    "RE",
                    problem.n_max,
                    public_only=public_only,
                    params=problem.signature.params,
                ),
                "compile_log": compiled.log,
                "time_ms": run.time_ms,
            }
        verdict = str(payload.get("verdict") or "RE")
        if verdict not in {"AC", "WA", "RE"}:
            verdict = "RE"
        details = _public_details(
            payload, hidden_flags, public_by_index, reveal_public=public_only
        )
        return {
            "verdict": verdict,
            "details": _with_hint(
                details, hint_tests, verdict, problem.n_max, public_only=public_only,
                params=problem.signature.params,
            ),
            "compile_log": compiled.log,
            "time_ms": run.time_ms,
        }


def apply_result(submission, result: dict[str, Any]) -> None:
    submission.status = "done"
    submission.verdict = result["verdict"]
    submission.details_json = json.dumps(result.get("details") or {}, ensure_ascii=False)
    submission.compile_log = result.get("compile_log")
    submission.time_ms = result.get("time_ms")
    submission.judged_at = datetime.utcnow()
