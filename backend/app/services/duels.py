"""Same-instance duel rooms. Source is never included."""
from __future__ import annotations

import secrets
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Duel, Submission, User
from ..schemas import DuelOut, DuelPlayerOut
from .problems import bank

TTL = timedelta(hours=2)


def _now() -> datetime:
    return datetime.utcnow()


def _new_code(db: Session) -> str:
    for _ in range(16):
        code = secrets.token_hex(3)
        exists = db.scalars(select(Duel).where(Duel.code == code)).first()
        if not exists:
            return code
    raise RuntimeError("could not allocate duel code")


def _player(user: User, ac: Submission | None) -> DuelPlayerOut:
    return DuelPlayerOut(
        user_id=user.id,
        username=user.username,
        ac=ac is not None,
        time_ms=int(ac.time_ms) if ac is not None and ac.time_ms is not None else None,
        language=ac.language if ac is not None else None,
        judged_at=ac.judged_at.isoformat() if ac is not None and ac.judged_at else None,
    )


def _first_ac(db: Session, user_id: int, slug: str, started_at: datetime | None) -> Submission | None:
    if started_at is None:
        return None
    return db.scalars(
        select(Submission)
        .where(
            Submission.user_id == user_id,
            Submission.problem_slug == slug,
            Submission.verdict == "AC",
            Submission.judged_at.is_not(None),
            Submission.judged_at >= started_at,
        )
        .order_by(Submission.judged_at, Submission.id)
    ).first()


def settle(db: Session, duel: Duel) -> Duel:
    now = _now()
    if duel.expires_at <= now and duel.status in {"waiting", "live"}:
        duel.status = "expired"
        return duel
    if duel.status != "live" or duel.started_at is None or duel.guest_id is None:
        return duel
    host_ac = _first_ac(db, duel.host_id, duel.slug, duel.started_at)
    guest_ac = _first_ac(db, duel.guest_id, duel.slug, duel.started_at)
    if host_ac is None and guest_ac is None:
        return duel
    if host_ac is not None and guest_ac is None:
        duel.winner_id = duel.host_id
        duel.status = "finished"
        return duel
    if guest_ac is not None and host_ac is None:
        duel.winner_id = duel.guest_id
        duel.status = "finished"
        return duel
    assert host_ac is not None and guest_ac is not None
    ht = int(host_ac.time_ms or 10**9)
    gt = int(guest_ac.time_ms or 10**9)
    if ht < gt:
        duel.winner_id = duel.host_id
    elif gt < ht:
        duel.winner_id = duel.guest_id
    else:
        h_at = host_ac.judged_at or now
        g_at = guest_ac.judged_at or now
        duel.winner_id = duel.host_id if h_at <= g_at else duel.guest_id
    duel.status = "finished"
    return duel


def to_out(db: Session, duel: Duel, me_id: int) -> DuelOut:
    settle(db, duel)
    db.commit()
    db.refresh(duel)
    try:
        title = bank.get(duel.slug).title
    except KeyError:
        title = duel.slug
    host = db.get(User, duel.host_id)
    guest = db.get(User, duel.guest_id) if duel.guest_id else None
    if host is None:
        raise KeyError("host")
    host_ac = _first_ac(db, duel.host_id, duel.slug, duel.started_at)
    guest_ac = _first_ac(db, duel.guest_id, duel.slug, duel.started_at) if duel.guest_id else None
    return DuelOut(
        code=duel.code,
        slug=duel.slug,
        title=title,
        status=duel.status,
        host=_player(host, host_ac),
        guest=_player(guest, guest_ac) if guest else None,
        winner_id=duel.winner_id,
        expires_at=duel.expires_at.isoformat(),
        started_at=duel.started_at.isoformat() if duel.started_at else None,
        is_host=me_id == duel.host_id,
        is_guest=duel.guest_id is not None and me_id == duel.guest_id,
    )


def create(db: Session, host_id: int, slug: str) -> Duel:
    bank.get(slug)
    now = _now()
    duel = Duel(
        code=_new_code(db),
        slug=slug,
        host_id=host_id,
        status="waiting",
        expires_at=now + TTL,
    )
    db.add(duel)
    db.commit()
    db.refresh(duel)
    return duel


def join(db: Session, code: str, user_id: int) -> Duel:
    duel = db.scalars(select(Duel).where(Duel.code == code.strip().lower())).first()
    if not duel:
        raise KeyError("missing")
    settle(db, duel)
    if duel.status == "expired":
        raise ValueError("expired")
    if duel.status == "finished":
        raise ValueError("finished")
    if duel.host_id == user_id:
        return duel
    if duel.guest_id is not None and duel.guest_id != user_id:
        raise ValueError("full")
    if duel.guest_id is None:
        duel.guest_id = user_id
        duel.started_at = _now()
        duel.status = "live"
        db.commit()
        db.refresh(duel)
    return duel


def get(db: Session, code: str) -> Duel:
    duel = db.scalars(select(Duel).where(Duel.code == code.strip().lower())).first()
    if not duel:
        raise KeyError("missing")
    return duel
