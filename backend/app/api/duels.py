from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import get_current_user
from ..models import User
from ..schemas import DuelCreateIn, DuelOut
from ..services import duels as duel_svc
from ..services.problems import bank

router = APIRouter(prefix="/api/duels", tags=["duels"])


@router.post("/", response_model=DuelOut)
def create_duel(
    body: DuelCreateIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DuelOut:
    try:
        bank.get(body.slug)
    except KeyError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "题目不存在") from None
    duel = duel_svc.create(db, user.id, body.slug)
    return duel_svc.to_out(db, duel, user.id)


@router.post("/{code}/join", response_model=DuelOut)
def join_duel(
    code: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DuelOut:
    try:
        duel = duel_svc.join(db, code, user.id)
    except KeyError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "房间不存在") from None
    except ValueError as exc:
        msg = {
            "expired": "房间已过期",
            "finished": "对战已结束",
            "full": "房间已满",
        }.get(str(exc), "无法加入")
        raise HTTPException(status.HTTP_400_BAD_REQUEST, msg) from None
    return duel_svc.to_out(db, duel, user.id)


@router.get("/{code}", response_model=DuelOut)
def get_duel(
    code: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DuelOut:
    try:
        duel = duel_svc.get(db, code)
    except KeyError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "房间不存在") from None
    return duel_svc.to_out(db, duel, user.id)
