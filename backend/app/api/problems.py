from __future__ import annotations

import json

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import SOURCE_MAX_BYTES
from ..db import get_db
from ..deps import get_current_user
from ..judge.languages import language_status
from ..judge.engine import judge_source
from ..judge.queue import enqueue, run_judge
from ..judge.traps import arsenal
from ..models import Draft, Submission, User
from ..schemas import (
    DraftIn,
    DraftOut,
    ProblemDetailOut,
    ProblemMetaOut,
    PublicTestOut,
    RankingOut,
    RunOut,
    ScoreOverview,
    ScoreRow,
    SubmissionOut,
    SubmitIn,
    TrapSlotOut,
)
from ..services.problems import bank
from ..services.progress import ac_best_map, score_overview, weekly_slugs
from ..services.publish import can_view, is_published
from ..services.ranking import ranking_for, scores_for_user

router = APIRouter(prefix="/api", tags=["problems"])


def _user_progress(db: Session, user_id: int) -> tuple[set[str], set[str]]:
    rows = db.execute(
        select(Submission.problem_slug, Submission.verdict).where(Submission.user_id == user_id)
    ).all()
    attempted = {slug for slug, _ in rows}
    solved = {slug for slug, verdict in rows if verdict == "AC"}
    return solved, attempted


def _submission_out(sub: Submission, include_source: bool = False) -> SubmissionOut:
    details = None
    if sub.details_json:
        try:
            details = json.loads(sub.details_json)
        except json.JSONDecodeError:
            details = {"message": sub.details_json}
    return SubmissionOut(
        id=sub.id,
        problem_slug=sub.problem_slug,
        language=sub.language,
        status=sub.status,
        verdict=sub.verdict,
        details=details,
        compile_log=sub.compile_log,
        time_ms=sub.time_ms,
        created_at=sub.created_at.isoformat() if sub.created_at else "",
        judged_at=sub.judged_at.isoformat() if sub.judged_at else None,
        source=sub.source if include_source else None,
    )


def _iso(dt) -> str | None:
    if dt is None:
        return None
    return dt.isoformat()


def _meta_out(
    problem,
    *,
    solved: bool,
    attempted: bool,
    ac_langs: list[str],
    weekly: bool,
    published: bool,
) -> dict:
    return dict(
        slug=problem.slug,
        title=problem.title,
        difficulty=problem.difficulty,
        time_limit_ms=problem.time_limit_ms,
        memory_limit_mb=problem.memory_limit_mb,
        tags=problem.tags,
        solved=solved,
        attempted=attempted,
        ac_languages=ac_langs,
        weekly=weekly,
        added_at=_iso(problem.added_at),
        languages=list(problem.languages),
        published=published,
    )


def _require_visible(db: Session, user: User, slug: str) -> None:
    if not can_view(db, user, slug):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "题目不存在")


@router.get("/languages")
def languages() -> list[dict]:
    return language_status()


@router.get("/problems", response_model=list[ProblemMetaOut])
def list_problems(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[ProblemMetaOut]:
    solved, attempted = _user_progress(db, user.id)
    best = ac_best_map(db, user.id)
    week = weekly_slugs()
    out = []
    for problem in bank.list():
        if not can_view(db, user, problem.slug):
            continue
        pub = is_published(db, problem.slug)
        out.append(
            ProblemMetaOut(
                **_meta_out(
                    problem,
                    solved=problem.slug in solved,
                    attempted=problem.slug in attempted,
                    ac_langs=sorted(best.get(problem.slug, {})),
                    weekly=problem.slug in week,
                    published=pub,
                )
            )
        )
    return out


@router.get("/problems/{slug}", response_model=ProblemDetailOut)
def get_problem(slug: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> ProblemDetailOut:
    _require_visible(db, user, slug)
    problem = bank.get(slug)
    solved, attempted = _user_progress(db, user.id)
    best = ac_best_map(db, user.id).get(slug, {})
    week = weekly_slugs()
    public = [
        PublicTestOut(args=t.args, expected=t.expected) for t in problem.public_tests()
    ]
    return ProblemDetailOut(
        **_meta_out(
            problem,
            solved=problem.slug in solved,
            attempted=problem.slug in attempted,
            ac_langs=sorted(best),
            weekly=problem.slug in week,
            published=is_published(db, slug),
        ),
        statement_md=problem.statement_md,
        signature=problem.signature,
        starter=problem.starter,
        public_tests=public,
        best_by_language={k: int(v) for k, v in best.items()},
        traps=[TrapSlotOut(**slot) for slot in arsenal(problem)],
    )


def _require_problem_language(problem, language: str) -> None:
    if language not in problem.languages:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "本题不支持该语言")


def _starter_source(slug: str, language: str) -> str:
    return bank.get(slug).starter.get(language, "")


@router.get("/problems/{slug}/draft", response_model=DraftOut)
def get_draft(
    slug: str,
    language: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DraftOut:
    _require_visible(db, user, slug)
    try:
        problem = bank.get(slug)
    except KeyError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "题目不存在") from None
    _require_problem_language(problem, language)
    row = db.scalars(
        select(Draft).where(
            Draft.user_id == user.id,
            Draft.problem_slug == slug,
            Draft.language == language,
        )
    ).first()
    if row:
        return DraftOut(
            language=language,
            source=row.source,
            from_starter=False,
            updated_at=row.updated_at.isoformat() if row.updated_at else None,
        )
    return DraftOut(language=language, source=_starter_source(slug, language), from_starter=True, updated_at=None)


@router.put("/problems/{slug}/draft", response_model=DraftOut)
def put_draft(
    slug: str,
    body: DraftIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DraftOut:
    _require_visible(db, user, slug)
    try:
        problem = bank.get(slug)
    except KeyError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "题目不存在") from None
    _require_problem_language(problem, body.language)
    if len(body.source.encode("utf-8")) > SOURCE_MAX_BYTES:
        raise HTTPException(413, "代码过长")
    row = db.scalars(
        select(Draft).where(
            Draft.user_id == user.id,
            Draft.problem_slug == slug,
            Draft.language == body.language,
        )
    ).first()
    if row:
        row.source = body.source
        row.updated_at = datetime.utcnow()
    else:
        row = Draft(
            user_id=user.id,
            problem_slug=slug,
            language=body.language,
            source=body.source,
        )
        db.add(row)
    db.commit()
    db.refresh(row)
    return DraftOut(
        language=row.language,
        source=row.source,
        from_starter=False,
        updated_at=row.updated_at.isoformat() if row.updated_at else None,
    )


@router.post("/problems/{slug}/submit", response_model=SubmissionOut)
async def submit(
    slug: str,
    body: SubmitIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SubmissionOut:
    _require_visible(db, user, slug)
    try:
        problem = bank.get(slug)
    except KeyError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "题目不存在") from None
    _require_problem_language(problem, body.language)
    if len(body.source.encode("utf-8")) > SOURCE_MAX_BYTES:
        raise HTTPException(413, "代码过长")
    sub = Submission(
        user_id=user.id,
        problem_slug=slug,
        language=body.language,
        source=body.source,
        status="queued",
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)
    await enqueue(sub.id)
    return _submission_out(sub)


@router.post("/problems/{slug}/run", response_model=RunOut)
async def run_public(
    slug: str,
    body: SubmitIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> RunOut:
    _require_visible(db, user, slug)
    try:
        problem = bank.get(slug)
    except KeyError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "题目不存在") from None
    _require_problem_language(problem, body.language)
    if len(body.source.encode("utf-8")) > SOURCE_MAX_BYTES:
        raise HTTPException(413, "代码过长")
    public = problem.public_tests()
    if not public:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "本题没有公开测例")
    result = await run_judge(judge_source, slug, body.language, body.source, True)
    return RunOut(
        kind="test",
        verdict=str(result.get("verdict") or "NA"),
        details=result.get("details"),
        compile_log=result.get("compile_log"),
        time_ms=result.get("time_ms"),
        public_count=len(public),
    )


@router.get("/problems/{slug}/ranking", response_model=RankingOut)
def problem_ranking(
    slug: str,
    language: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> RankingOut:
    _require_visible(db, user, slug)
    try:
        problem = bank.get(slug)
    except KeyError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "题目不存在") from None
    _require_problem_language(problem, language)
    return ranking_for(db, slug, language, user.id)


@router.get("/scores", response_model=list[ScoreRow])
def my_scores(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[ScoreRow]:
    return scores_for_user(db, user.id)


@router.get("/scores/overview", response_model=ScoreOverview)
def my_score_overview(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> ScoreOverview:
    return score_overview(db, user.id)


@router.get("/submissions", response_model=list[SubmissionOut])
def my_submissions(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    slug: str | None = None,
    limit: int = 50,
) -> list[SubmissionOut]:
    stmt = select(Submission).where(Submission.user_id == user.id)
    if slug:
        stmt = stmt.where(Submission.problem_slug == slug)
    stmt = stmt.order_by(Submission.id.desc()).limit(min(limit, 200))
    rows = db.scalars(stmt).all()
    return [_submission_out(row) for row in rows]


@router.get("/submissions/{sub_id}", response_model=SubmissionOut)
def get_submission(
    sub_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SubmissionOut:
    sub = db.get(Submission, sub_id)
    if not sub or sub.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "提交不存在")
    return _submission_out(sub, include_source=True)
