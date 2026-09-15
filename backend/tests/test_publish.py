from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.models import User
from app.services import publish as pub


def _session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_unpublished_hidden_from_regular(monkeypatch):
    db = _session()
    admin = User(id=1, username="admin", password_hash="x", is_admin=True)
    user = User(id=2, username="cand", password_hash="x", is_admin=False)

    class P:
        slug = "demo"
        title = "Demo"
        difficulty = "easy"

    monkeypatch.setattr(pub.bank, "get", lambda slug: P() if slug == "demo" else (_ for _ in ()).throw(KeyError(slug)))
    monkeypatch.setattr(pub.bank, "list", lambda: [P()])

    assert pub.can_view(db, admin, "demo") is True
    assert pub.can_view(db, user, "demo") is False
    pub.set_published(db, "demo", True)
    assert pub.can_view(db, user, "demo") is True
    pub.set_published(db, "demo", False)
    assert pub.can_view(db, user, "demo") is False
    rows = pub.catalog(db)
    assert rows == [{"slug": "demo", "title": "Demo", "difficulty": "easy", "published": False}]
