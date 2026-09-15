"""Which imported problems regular users may see."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import ProblemPublish, User
from .problems import bank


def is_published(db: Session, slug: str) -> bool:
    row = db.get(ProblemPublish, slug)
    return bool(row and row.published)


def can_view(db: Session, user: User, slug: str) -> bool:
    try:
        bank.get(slug)
    except KeyError:
        return False
    if user.is_admin:
        return True
    return is_published(db, slug)


def set_published(db: Session, slug: str, published: bool) -> ProblemPublish:
    bank.get(slug)
    row = db.get(ProblemPublish, slug)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if row is None:
        row = ProblemPublish(slug=slug, published=published, published_at=now if published else None)
        db.add(row)
    else:
        row.published = published
        row.published_at = now if published else None
    db.commit()
    db.refresh(row)
    return row


def catalog(db: Session) -> list[dict]:
    flags = {row.slug: row for row in db.scalars(select(ProblemPublish)).all()}
    out = []
    for problem in bank.list():
        flag = flags.get(problem.slug)
        out.append(
            {
                "slug": problem.slug,
                "title": problem.title,
                "difficulty": problem.difficulty,
                "published": bool(flag and flag.published),
            }
        )
    return out
