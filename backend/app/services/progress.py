"""User AC progress, weekly slugs, and score overview."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import Submission
from ..schemas import BingoRow, ScoreOverview
from .problems import bank
from .ranking import scores_for_user


def _aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def ac_best_map(db: Session, user_id: int) -> dict[str, dict[str, int]]:
    """slug -> language -> best time_ms."""
    rows = db.execute(
        select(Submission.problem_slug, Submission.language, func.min(Submission.time_ms))
        .where(
            Submission.user_id == user_id,
            Submission.verdict == "AC",
            Submission.time_ms.is_not(None),
        )
        .group_by(Submission.problem_slug, Submission.language)
    ).all()
    out: dict[str, dict[str, int]] = defaultdict(dict)
    for slug, language, best_ms in rows:
        out[slug][language] = int(best_ms)
    return dict(out)


def weekly_slugs(now: datetime | None = None) -> set[str]:
    problems = bank.list()
    if not problems:
        return set()
    now = _aware(now or datetime.now(timezone.utc))
    week: list[str] = []
    for problem in problems:
        added = _aware(problem.added_at)
        if now - added < timedelta(days=7):
            week.append(problem.slug)
    if week:
        return set(week)
    newest = sorted(problems, key=lambda p: _aware(p.added_at), reverse=True)[:3]
    return {p.slug for p in newest}


def score_overview(db: Session, user_id: int) -> ScoreOverview:
    best = ac_best_map(db, user_id)
    bingo: list[BingoRow] = []
    complete = 0
    problems = bank.list()
    for problem in problems:
        ac_langs = sorted(best.get(problem.slug, {}))
        langs = list(problem.languages)
        if langs and set(langs) <= set(ac_langs):
            complete += 1
        bingo.append(
            BingoRow(
                slug=problem.slug,
                title=problem.title,
                tags=list(problem.tags),
                languages=langs,
                ac_languages=ac_langs,
            )
        )
    return ScoreOverview(
        complete=complete,
        total_problems=len(problems),
        rows=scores_for_user(db, user_id),
        bingo=bingo,
    )
