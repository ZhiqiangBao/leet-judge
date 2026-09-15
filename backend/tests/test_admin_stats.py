from __future__ import annotations

from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.deps import create_user
from app.models import Submission, User  # noqa: F401
from app.services.admin_stats import problem_stats, user_stats


def _session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_problem_and_user_stats_aggregate():
    db = _session()
    alice = create_user(db, "alice", "secret", is_admin=False)
    bob = create_user(db, "bob", "secret", is_admin=False)
    db.add_all(
        [
            Submission(
                user_id=alice.id,
                problem_slug="two-sum",
                language="python3",
                source="a",
                status="done",
                verdict="AC",
            ),
            Submission(
                user_id=alice.id,
                problem_slug="two-sum",
                language="c",
                source="b",
                status="done",
                verdict="WA",
            ),
            Submission(
                user_id=bob.id,
                problem_slug="plus-one",
                language="python3",
                source="c",
                status="done",
                verdict="AC",
            ),
        ]
    )
    db.commit()
    catalog = [
        SimpleNamespace(slug="two-sum", title="两数之和"),
        SimpleNamespace(slug="plus-one", title="加一"),
        SimpleNamespace(slug="empty", title="空题"),
    ]
    problems = {row.slug: row for row in problem_stats(db, catalog)}
    assert problems["two-sum"].submissions == 2
    assert problems["two-sum"].accepted == 1
    assert problems["empty"].submissions == 0
    users = {row.username: row for row in user_stats(db)}
    assert users["alice"].submissions == 2
    assert users["alice"].accepted == 1
    py = next(item for item in users["alice"].by_language if item.language == "python3")
    assert py.submissions == 1
    assert py.accepted == 1
    assert users["bob"].submissions == 1
