from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import Submission, User
from ..schemas import RankEntry, RankingOut, ScoreRow
from .problems import bank


def ranking_for(db: Session, slug: str, language: str, me_id: int | None = None) -> RankingOut:
    best = (
        select(Submission.user_id, func.min(Submission.time_ms).label("best_ms"))
        .where(
            Submission.problem_slug == slug,
            Submission.language == language,
            Submission.verdict == "AC",
            Submission.time_ms.is_not(None),
        )
        .group_by(Submission.user_id)
        .order_by(func.min(Submission.time_ms), Submission.user_id)
        .subquery()
    )
    stmt = (
        select(best.c.user_id, best.c.best_ms, User.username)
        .join(User, User.id == best.c.user_id)
        .order_by(best.c.best_ms, best.c.user_id)
    )
    rows = db.execute(stmt).all()
    entries: list[RankEntry] = []
    mine: RankEntry | None = None
    for i, row in enumerate(rows, start=1):
        entry = RankEntry(
            rank=i,
            username=row.username,
            time_ms=int(row.best_ms),
            is_me=me_id is not None and row.user_id == me_id,
        )
        entries.append(entry)
        if entry.is_me:
            mine = entry
    return RankingOut(slug=slug, language=language, total=len(entries), mine=mine, entries=entries)


def scores_for_user(db: Session, user_id: int) -> list[ScoreRow]:
    ac = db.execute(
        select(Submission.problem_slug, Submission.language, func.min(Submission.time_ms))
        .where(
            Submission.user_id == user_id,
            Submission.verdict == "AC",
            Submission.time_ms.is_not(None),
        )
        .group_by(Submission.problem_slug, Submission.language)
        .order_by(Submission.problem_slug, Submission.language)
    ).all()
    titles = {p.slug: p.title for p in bank.list()}
    out: list[ScoreRow] = []
    for slug, language, best_ms in ac:
        ranking = ranking_for(db, slug, language, user_id)
        rank = ranking.mine.rank if ranking.mine else 0
        out.append(
            ScoreRow(
                slug=slug,
                title=titles.get(slug, slug),
                language=language,
                time_ms=int(best_ms),
                rank=rank,
                total=ranking.total,
            )
        )
    return out
