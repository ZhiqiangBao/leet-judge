from __future__ import annotations

import subprocess
from pathlib import Path

from app.services.git_sync import pull_problems
from app.services.problems import ProblemError


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(cwd), *args], check=True, capture_output=True)


def test_pull_ff_reports_problem_slugs(tmp_path: Path):
    remote = tmp_path / "remote.git"
    subprocess.run(["git", "init", "--bare", "-b", "main", str(remote)], check=True, capture_output=True)
    work = tmp_path / "work"
    work.mkdir()
    _git(work, "init", "-b", "main")
    _git(work, "config", "user.email", "t@example.com")
    _git(work, "config", "user.name", "t")
    _git(work, "remote", "add", "origin", str(remote))
    (work / "problems" / "new-one").mkdir(parents=True)
    (work / "problems" / "new-one" / "note.txt").write_text("x", encoding="utf-8")
    _git(work, "add", ".")
    _git(work, "-c", "commit.gpgsign=false", "commit", "-m", "init")
    _git(work, "push", "-u", "origin", "main")
    judge = tmp_path / "judge"
    subprocess.run(["git", "clone", str(remote), str(judge)], check=True, capture_output=True)
    (work / "problems" / "new-two").mkdir()
    (work / "problems" / "new-two" / "note.txt").write_text("y", encoding="utf-8")
    _git(work, "add", ".")
    _git(work, "-c", "commit.gpgsign=false", "commit", "-m", "add")
    _git(work, "push")
    result = pull_problems(judge)
    assert result["ok"] is True
    assert result["unchanged"] is False
    assert "new-two" in result["slugs"]


def test_pull_requires_git(tmp_path: Path):
    try:
        pull_problems(tmp_path)
        assert False
    except ProblemError as exc:
        assert "git" in str(exc).lower() or "仓库" in str(exc)
