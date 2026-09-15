from __future__ import annotations

from collections import defaultdict
from typing import Any

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from ..models import Submission, User
from ..schemas import LanguageStat, ProblemStat, UserStat

_AC = case((Submission.verdict == "AC", 1), else_=0)


def problem_stats(db: Session, catalog: list[Any]) -> list[ProblemStat]:
    rows = db.execute(
        select(Submission.problem_slug, func.count(), func.coalesce(func.sum(_AC), 0)).group_by(
            Submission.problem_slug
        )
    ).all()
    counts = {str(slug): (int(total), int(ac)) for slug, total, ac in rows}
    out: list[ProblemStat] = []
    seen: set[str] = set()
    for problem in catalog:
        total, ac = counts.get(problem.slug, (0, 0))
        out.append(ProblemStat(slug=problem.slug, title=problem.title, submissions=total, accepted=ac))
        seen.add(problem.slug)
    for slug in sorted(counts):
        if slug in seen:
            continue
        total, ac = counts[slug]
        out.append(ProblemStat(slug=slug, title=slug, submissions=total, accepted=ac))
    return out


def user_stats(db: Session) -> list[UserStat]:
    totals = db.execute(
        select(
            User.id,
            User.username,
            func.count(Submission.id),
            func.coalesce(func.sum(_AC), 0),
        )
        .outerjoin(Submission, User.id == Submission.user_id)
        .group_by(User.id, User.username)
    ).all()
    langs = db.execute(
        select(
            Submission.user_id,
            Submission.language,
            func.count(),
            func.coalesce(func.sum(_AC), 0),
        ).group_by(Submission.user_id, Submission.language)
    ).all()
    by_lang: dict[int, list[LanguageStat]] = defaultdict(list)
    for uid, language, total, ac in langs:
        by_lang[int(uid)].append(
            LanguageStat(language=str(language), submissions=int(total), accepted=int(ac))
        )
    for items in by_lang.values():
        items.sort(key=lambda row: (-row.submissions, row.language))
    out = [
        UserStat(
            user_id=int(uid),
            username=str(name),
            submissions=int(total),
            accepted=int(ac),
            by_language=by_lang.get(int(uid), []),
        )
        for uid, name, total, ac in totals
    ]
    out.sort(key=lambda row: (-row.submissions, row.user_id))
    return out
