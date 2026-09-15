from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

Difficulty = Literal["easy", "medium", "hard"]
CompareMode = Literal["exact", "any_order"]


class RegisterIn(BaseModel):
    username: str = Field(min_length=3, max_length=32, pattern=r"^[A-Za-z0-9_]+$")
    password: str = Field(min_length=4, max_length=72)


class LoginIn(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    id: int
    username: str
    is_admin: bool


class ParamSpec(BaseModel):
    name: str
    type: str


class Signature(BaseModel):
    class_name: str = "Solution"
    method: str
    params: list[ParamSpec]
    return_type: str
    compare: CompareMode = "exact"


class TestCase(BaseModel):
    args: list[Any]
    expected: Any
    hidden: bool = False


class PublicTestOut(BaseModel):
    args: list[Any]
    expected: Any


class TrapSlotOut(BaseModel):
    id: str
    title: str
    blurb: str
    loaded: bool
    family: str
    verified: bool = False


class ProblemMetaOut(BaseModel):
    slug: str
    title: str
    difficulty: Difficulty
    time_limit_ms: int
    memory_limit_mb: int
    tags: list[str]
    solved: bool = False
    attempted: bool = False
    ac_languages: list[str] = Field(default_factory=list)
    weekly: bool = False
    added_at: str | None = None
    languages: list[str] = Field(default_factory=list)


class ProblemDetailOut(ProblemMetaOut):
    statement_md: str
    signature: Signature
    starter: dict[str, str]
    public_tests: list[PublicTestOut] = Field(default_factory=list)
    best_by_language: dict[str, int] = Field(default_factory=dict)
    traps: list[TrapSlotOut] = Field(default_factory=list)


class SubmitIn(BaseModel):
    language: str
    source: str = Field(min_length=1, max_length=262144)


class DraftIn(BaseModel):
    language: str
    source: str = Field(max_length=262144)


class DraftOut(BaseModel):
    language: str
    source: str
    from_starter: bool
    updated_at: str | None = None


class SubmissionOut(BaseModel):
    id: int
    problem_slug: str
    language: str
    status: str
    verdict: str | None
    details: dict[str, Any] | None = None
    compile_log: str | None = None
    time_ms: int | None = None
    created_at: str
    judged_at: str | None = None
    source: str | None = None


class LanguageOut(BaseModel):
    id: str
    display_name: str
    implemented: bool
    available: bool
    runtime_detected: bool
    reason: str | None = None


class ProblemCreateIn(BaseModel):
    slug: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", max_length=64)
    title: str = Field(min_length=1, max_length=120)
    difficulty: Difficulty = "easy"
    time_limit_ms: int = Field(default=2000, ge=100, le=30000)
    memory_limit_mb: int = Field(default=256, ge=32, le=2048)
    tags: list[str] = Field(default_factory=list)
    statement_md: str
    signature: Signature
    starter: dict[str, str] = Field(default_factory=dict)
    tests: list[TestCase] = Field(default_factory=list)


class ProblemUpdateIn(BaseModel):
    title: str | None = None
    difficulty: Difficulty | None = None
    time_limit_ms: int | None = Field(default=None, ge=100, le=30000)
    memory_limit_mb: int | None = Field(default=None, ge=32, le=2048)
    tags: list[str] | None = None
    statement_md: str | None = None
    signature: Signature | None = None
    starter: dict[str, str] | None = None


class TestsReplaceIn(BaseModel):
    tests: list[TestCase]


class TestsAppendIn(BaseModel):
    tests: list[TestCase] = Field(min_length=1)


class RunOut(BaseModel):
    kind: str = "test"
    verdict: str
    details: dict[str, Any] | None = None
    compile_log: str | None = None
    time_ms: int | None = None
    public_count: int = 0


class RankEntry(BaseModel):
    rank: int
    username: str
    time_ms: int
    is_me: bool = False


class RankingOut(BaseModel):
    slug: str
    language: str
    total: int
    mine: RankEntry | None = None
    entries: list[RankEntry]


class ScoreRow(BaseModel):
    slug: str
    title: str
    language: str
    time_ms: int
    rank: int
    total: int


class BingoRow(BaseModel):
    slug: str
    title: str
    tags: list[str]
    languages: list[str]
    ac_languages: list[str]


class ScoreOverview(BaseModel):
    complete: int
    total_problems: int
    rows: list[ScoreRow]
    bingo: list[BingoRow]


class DuelCreateIn(BaseModel):
    slug: str


class DuelPlayerOut(BaseModel):
    user_id: int
    username: str
    ac: bool = False
    time_ms: int | None = None
    language: str | None = None
    judged_at: str | None = None


class DuelOut(BaseModel):
    code: str
    slug: str
    title: str
    status: str
    host: DuelPlayerOut
    guest: DuelPlayerOut | None = None
    winner_id: int | None = None
    expires_at: str
    started_at: str | None = None
    is_host: bool = False
    is_guest: bool = False


class AdminSubmissionOut(SubmissionOut):
    user_id: int
    username: str


class ProblemStat(BaseModel):
    slug: str
    title: str
    submissions: int
    accepted: int


class LanguageStat(BaseModel):
    language: str
    submissions: int
    accepted: int


class UserStat(BaseModel):
    user_id: int
    username: str
    submissions: int
    accepted: int
    by_language: list[LanguageStat]


class AdminStatsOut(BaseModel):
    users: int
    submissions: int
    accepted: int
    problems: int
    by_problem: list[ProblemStat]
