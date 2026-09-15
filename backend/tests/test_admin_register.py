from __future__ import annotations

from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.admin_register import _html, _is_loopback
from app.db import Base
from app.deps import create_user
from app.models import User  # noqa: F401


def _session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_create_user_admin_flag_independent_of_order():
    db = _session()
    first = create_user(db, "first_user", "secret", is_admin=False)
    admin = create_user(db, "root_admin", "secret", is_admin=True)
    assert first.is_admin is False
    assert admin.is_admin is True


def test_admin_register_page_renders_css():
    resp = _html("<p>ok</p>")
    text = bytes(resp.body).decode()
    assert resp.status_code == 200
    assert "注册管理员" in text
    assert "font-family" in text
    assert "<p>ok</p>" in text


def test_loopback_only():
    def req(host: str | None):
        client = SimpleNamespace(host=host) if host is not None else None
        return SimpleNamespace(client=client)

    assert _is_loopback(req("127.0.0.1"))
    assert _is_loopback(req("::1"))
    assert _is_loopback(req("::ffff:127.0.0.1"))
    assert not _is_loopback(req("192.168.1.8"))
    assert not _is_loopback(req(None))
