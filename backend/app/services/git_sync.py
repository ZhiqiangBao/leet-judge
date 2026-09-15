"""Pull the judge clone. Does not parse tests.jsonl."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from ..config import ROOT
from .problems import ProblemError

_CODE_PREFIXES = ("backend/", "frontend/", "scripts/", "rules/")


def _git(root: Path, *args: str, timeout: int = 120) -> str:
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0", "GCM_INTERACTIVE": "never"}
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            env=env,
        )
    except subprocess.TimeoutExpired as exc:
        raise ProblemError("git 超时") from exc
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip() or "git 失败"
        raise ProblemError(err)
    return (proc.stdout or "").strip()


def pull_problems(root: Path | None = None) -> dict:
    repo = Path(root) if root is not None else ROOT
    if not (repo / ".git").exists():
        raise ProblemError("评测机目录不是 git 仓库，无法从远程拉取")
    before = _git(repo, "rev-parse", "HEAD")
    _git(repo, "pull", "--ff-only")
    after = _git(repo, "rev-parse", "HEAD")
    names: list[str] = []
    if before != after:
        names = [line.replace("\\", "/") for line in _git(repo, "diff", "--name-only", before, after).splitlines() if line]
    slugs: list[str] = []
    for name in names:
        parts = name.split("/")
        if len(parts) >= 2 and parts[0] == "problems" and parts[1] and parts[1] != "catalog.md":
            if parts[1] not in slugs:
                slugs.append(parts[1])
    needs_restart = any(name.startswith(_CODE_PREFIXES) for name in names)
    return {
        "ok": True,
        "unchanged": before == after,
        "before": before,
        "after": after,
        "slugs": slugs,
        "needs_restart": needs_restart,
    }
