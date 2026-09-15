from __future__ import annotations

import json

from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import ROOT
from ..db import get_db
from ..deps import get_admin_user
from ..models import Submission, User
from ..schemas import (
    AdminStatsOut,
    AdminSubmissionOut,
    ProblemCreateIn,
    ProblemStat,
    ProblemUpdateIn,
    TestsAppendIn,
    TestsReplaceIn,
    UserStat,
)
from ..services.admin_stats import problem_stats, user_stats
from ..services.git_sync import pull_problems
from ..services.problems import (
    ProblemError,
    bank,
    extract_problem_zip,
    write_upload_tree,
)

_PATCH_NAMES = {
    "meta": "meta.yaml",
    "statement": "statement.md",
    "signature": "signature.yaml",
    "tests": "tests.jsonl",
}
_PATCH_MAX_BYTES = 80 * 1024 * 1024

router = APIRouter(prefix="/api/admin", tags=["admin"])


def _admin_submission_out(sub: Submission, username: str, include_source: bool = False) -> AdminSubmissionOut:
    details = None
    if sub.details_json:
        try:
            details = json.loads(sub.details_json)
        except json.JSONDecodeError:
            details = {"message": sub.details_json}
    return AdminSubmissionOut(
        id=sub.id,
        user_id=sub.user_id,
        username=username,
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


async def _stream_named_upload(upload: UploadFile, dest: Path) -> None:
    written = 0
    with dest.open("wb") as out:
        while True:
            chunk = await upload.read(1024 * 1024)
            if not chunk:
                break
            written += len(chunk)
            if written > _PATCH_MAX_BYTES:
                raise ProblemError(f"{dest.name} 太大")
            out.write(chunk)


@router.get("/guide")
def admin_guide(_admin: User = Depends(get_admin_user)) -> dict:
    path = ROOT / "docs" / "admin.md"
    if not path.is_file():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "手册文件不存在")
    return {"markdown": path.read_text(encoding="utf-8")}


@router.get("/stats", response_model=AdminStatsOut)
def stats(_admin: User = Depends(get_admin_user), db: Session = Depends(get_db)) -> AdminStatsOut:
    catalog = bank.list()
    by_problem = problem_stats(db, catalog)
    users = user_stats(db)
    return AdminStatsOut(
        users=len(users),
        submissions=sum(row.submissions for row in by_problem),
        accepted=sum(row.accepted for row in by_problem),
        problems=len(catalog),
        by_problem=by_problem,
    )


@router.get("/stats/problems", response_model=list[ProblemStat])
def stats_problems(_admin: User = Depends(get_admin_user), db: Session = Depends(get_db)) -> list[ProblemStat]:
    return problem_stats(db, bank.list())


@router.get("/stats/users", response_model=list[UserStat])
def stats_users(_admin: User = Depends(get_admin_user), db: Session = Depends(get_db)) -> list[UserStat]:
    return user_stats(db)


@router.get("/submissions", response_model=list[AdminSubmissionOut])
def list_submissions(
    db: Session = Depends(get_db),
    _admin: User = Depends(get_admin_user),
    slug: str | None = None,
    username: str | None = None,
    user_id: int | None = None,
    language: str | None = None,
    limit: int = 100,
) -> list[AdminSubmissionOut]:
    stmt = select(Submission, User.username).join(User, User.id == Submission.user_id)
    if slug:
        stmt = stmt.where(Submission.problem_slug == slug)
    if language:
        stmt = stmt.where(Submission.language == language)
    if username:
        stmt = stmt.where(User.username == username)
    if user_id is not None:
        stmt = stmt.where(Submission.user_id == user_id)
    stmt = stmt.order_by(Submission.id.desc()).limit(min(max(limit, 1), 300))
    rows = db.execute(stmt).all()
    return [_admin_submission_out(sub, name) for sub, name in rows]


@router.get("/submissions/{sub_id}", response_model=AdminSubmissionOut)
def get_submission(
    sub_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(get_admin_user),
) -> AdminSubmissionOut:
    row = db.execute(
        select(Submission, User.username).join(User, User.id == Submission.user_id).where(Submission.id == sub_id)
    ).first()
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "提交不存在")
    sub, name = row
    return _admin_submission_out(sub, name, include_source=True)


@router.post("/problems")
def create_problem(body: ProblemCreateIn, _admin: User = Depends(get_admin_user)) -> dict:
    try:
        problem = bank.write_problem(
            slug=body.slug,
            title=body.title,
            difficulty=body.difficulty,
            time_limit_ms=body.time_limit_ms,
            memory_limit_mb=body.memory_limit_mb,
            tags=body.tags,
            statement_md=body.statement_md,
            signature=body.signature,
            starter=body.starter,
            tests=body.tests,
            overwrite=False,
        )
    except ProblemError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    return {"ok": True, "slug": problem.slug, "tests": problem.test_count}


@router.put("/problems/{slug}")
def update_problem(slug: str, body: ProblemUpdateIn, _admin: User = Depends(get_admin_user)) -> dict:
    try:
        current = bank.get(slug)
    except KeyError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "题目不存在") from None
    try:
        problem = bank.write_problem(
            slug=slug,
            title=body.title or current.title,
            difficulty=body.difficulty or current.difficulty,
            time_limit_ms=body.time_limit_ms or current.time_limit_ms,
            memory_limit_mb=body.memory_limit_mb or current.memory_limit_mb,
            tags=body.tags if body.tags is not None else current.tags,
            statement_md=body.statement_md if body.statement_md is not None else current.statement_md,
            signature=body.signature or current.signature,
            starter=body.starter if body.starter is not None else current.starter,
            tests=None,
            overwrite=True,
        )
    except ProblemError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    return {"ok": True, "slug": problem.slug}


@router.put("/problems/{slug}/tests")
def replace_tests(slug: str, body: TestsReplaceIn, _admin: User = Depends(get_admin_user)) -> dict:
    try:
        bank.get(slug)
        problem = bank.write_tests(slug, body.tests, append=False)
    except KeyError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "题目不存在") from None
    except ProblemError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    return {"ok": True, "slug": slug, "tests": problem.test_count}


@router.post("/problems/{slug}/tests:append")
def append_tests(slug: str, body: TestsAppendIn, _admin: User = Depends(get_admin_user)) -> dict:
    try:
        bank.get(slug)
        problem = bank.write_tests(slug, body.tests, append=True)
    except KeyError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "题目不存在") from None
    except ProblemError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    return {"ok": True, "slug": slug, "tests": problem.test_count}


@router.post("/reload")
def reload(_admin: User = Depends(get_admin_user)) -> dict:
    try:
        bank.reload()
    except ProblemError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    return {"ok": True, "count": len(bank.list())}


@router.post("/sync-git")
def sync_git(_admin: User = Depends(get_admin_user)) -> dict:
    try:
        result = pull_problems()
        bank.reload()
    except ProblemError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    result["count"] = len(bank.list())
    return result


@router.post("/problems/import")
async def import_problems(
    overwrite: bool = Form(True),
    slug: str = Form(""),
    file: UploadFile | None = File(None),
    files: list[UploadFile] | None = File(None),
    _admin: User = Depends(get_admin_user),
) -> dict:
    uploads = [item for item in (files or []) if item is not None and (item.filename or "").strip()]
    if file is not None and (file.filename or "").strip():
        uploads = [file, *uploads]
    if not uploads:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "请选择题目目录或 zip")
    try:
        with TemporaryDirectory() as raw:
            tree = Path(raw) / "tree"
            tree.mkdir()
            first = (uploads[0].filename or "").replace("\\", "/").lower()
            if len(uploads) == 1 and first.endswith(".zip"):
                extract_problem_zip(await uploads[0].read(), tree)
            else:
                packed: list[tuple[str, bytes]] = []
                for item in uploads:
                    packed.append((item.filename or item.name, await item.read()))
                write_upload_tree(packed, tree)
            slugs = bank.import_tree(tree, overwrite=overwrite, fallback_slug=slug.strip())
    except ProblemError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    return {"ok": True, "slugs": slugs, "count": len(bank.list())}


@router.post("/problems/files")
async def merge_problem_files(
    slug: str = Form(...),
    meta: UploadFile | None = File(None),
    statement: UploadFile | None = File(None),
    signature: UploadFile | None = File(None),
    tests: UploadFile | None = File(None),
    _admin: User = Depends(get_admin_user),
) -> dict:
    uploads = {
        "meta": meta,
        "statement": statement,
        "signature": signature,
        "tests": tests,
    }
    try:
        with TemporaryDirectory() as raw:
            incoming = Path(raw) / "files"
            incoming.mkdir()
            wrote = False
            for field, upload in uploads.items():
                if upload is None or not (upload.filename or "").strip():
                    continue
                dest = incoming / _PATCH_NAMES[field]
                await _stream_named_upload(upload, dest)
                wrote = True
            if not wrote:
                raise ProblemError("请选择要写入的文件")
            problem = bank.merge_files(slug.strip(), incoming)
    except ProblemError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    return {"ok": True, "slug": problem.slug, "count": len(bank.list())}


@router.post("/problems/{slug}/starters")
def generate_starters(slug: str, _admin: User = Depends(get_admin_user)) -> dict:
    try:
        bank.get(slug)
        return bank.write_starters(slug)
    except KeyError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "题目不存在") from None
    except ProblemError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
