from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.deps import create_user
from app.judge.hints import attach_hint, case_n
from app.models import Duel, Submission, User  # noqa: F401
from app.services import duels as duel_svc
from app.services.progress import score_overview, weekly_slugs


def test_hint_hidden_has_no_args():
    tests = [
        SimpleNamespace(args=[[1, 2], 3], expected=[0, 1], hidden=False),
        SimpleNamespace(args=[[0] * 100000], expected=1, hidden=True),
    ]
    details = {"failed_index": 1, "verdict": "WA"}
    out = attach_hint(
        details,
        tests,
        "WA",
        100000,
        public_only=False,
        params=[("nums", "List[int]")],
    )
    hint = out["hint"]
    assert "args" not in hint
    assert "expected" not in hint
    assert hint["hidden"] is True
    assert hint["at_max"] is True
    assert hint["n"] == 100000
    dumped = str(out)
    assert "[0, 0, 0, 0, 0" not in dumped
    assert out["kill"]["weapon"] == "scale"
    assert out["kill"]["hidden"] is True
    assert "args" not in out["kill"]


def test_hint_tle_text():
    tests = [SimpleNamespace(args=[[0] * 10], hidden=True)]
    out = attach_hint({"message": "tle"}, tests, "TLE", 100000, public_only=False)
    assert "args" not in out["hint"]
    assert "超时" in out["hint"]["text"]


def test_case_n_grid():
    assert case_n([[[1, 2], [3, 4]], 2], [("grid", "List[List[int]]"), ("k", "int")]) == 2
    assert case_n(["ab", "cd"], [("s", "str"), ("t", "str")]) == 2


def test_case_n_graph_uses_vertex_n_not_edge_len():
    edges = [[i % 50, (i + 1) % 50] for i in range(2500)]
    params = [("n", "int"), ("edges", "List[List[int]]"), ("k", "int")]
    assert case_n([50, edges, 1], params) == 50
    assert case_n([[0] * 100], [("nums", "List[int]")]) == 100


def test_case_n_int_then_list_is_not_vertex_scale():
    assert case_n([3, [0] * 100], [("k", "int"), ("nums", "List[int]")]) == 100


def test_weekly_recent_and_fallback(monkeypatch):
    now = datetime(2026, 9, 8, tzinfo=timezone.utc)

    class P:
        def __init__(self, slug: str, days: int) -> None:
            self.slug = slug
            self.added_at = now - timedelta(days=days)

    monkeypatch.setattr(
        "app.services.progress.bank.list",
        lambda: [P("new", 1), P("old", 40)],
    )
    assert weekly_slugs(now) == {"new"}

    monkeypatch.setattr(
        "app.services.progress.bank.list",
        lambda: [P("a", 10), P("b", 20), P("c", 30), P("d", 40)],
    )
    assert weekly_slugs(now) == {"a", "b", "c"}


def _session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_duel_join_and_faster_ac_wins(monkeypatch):
    db = _session()
    host = create_user(db, "host_user", "secret", is_admin=False)
    guest = create_user(db, "guest_user", "secret", is_admin=False)
    monkeypatch.setattr(
        "app.services.duels.bank.get",
        lambda slug: SimpleNamespace(slug=slug, title="两数之和"),
    )
    duel = duel_svc.create(db, host.id, "two-sum")
    assert duel.status == "waiting"
    joined = duel_svc.join(db, duel.code, guest.id)
    assert joined.status == "live"
    assert joined.started_at is not None
    t0 = joined.started_at
    db.add(
        Submission(
            user_id=host.id,
            problem_slug="two-sum",
            language="python3",
            source="x",
            status="done",
            verdict="AC",
            time_ms=80,
            judged_at=t0 + timedelta(seconds=5),
        )
    )
    db.add(
        Submission(
            user_id=guest.id,
            problem_slug="two-sum",
            language="c",
            source="y",
            status="done",
            verdict="AC",
            time_ms=20,
            judged_at=t0 + timedelta(seconds=6),
        )
    )
    db.commit()
    out = duel_svc.to_out(db, joined, host.id)
    assert out.status == "finished"
    assert out.winner_id == guest.id
    assert out.host.ac is True
    assert out.guest and out.guest.ac is True
    assert out.guest.time_ms == 20


def test_bingo_overview_fields():
    db = _session()
    user = create_user(db, "bingo_user", "secret", is_admin=False)
    ov = score_overview(db, user.id)
    assert ov.total_problems > 0
    assert ov.complete == 0
    row = next(r for r in ov.bingo if r.slug == "two-sum")
    assert row.ac_languages == []
    assert row.languages
    assert "python3" in row.languages


def test_arsenal_no_args_and_kill_weapon():
    from app.judge.traps import arsenal

    problem = SimpleNamespace(
        tags=["array", "hash"],
        n_max=10000,
        elem_min=-1_000_000_000,
        elem_max=1_000_000_000,
        signature=SimpleNamespace(
            params=[
                SimpleNamespace(name="nums", type="List[int]"),
                SimpleNamespace(name="target", type="int"),
            ]
        ),
        tests=[
            SimpleNamespace(hidden=False, args=[[2, 7], 9]),
            SimpleNamespace(hidden=True, args=[[1, 2], 3]),
            SimpleNamespace(hidden=True, args=[[0] * 10000, 1]),
            SimpleNamespace(hidden=True, args=[[-1_000_000_000, 1_000_000_000], 0]),
        ],
    )
    slots = arsenal(problem)
    dumped = str(slots)
    assert "[0, 0, 0" not in dumped
    by_id = {s["id"]: s for s in slots}
    assert by_id["boundary"]["loaded"] is True
    assert by_id["scale"]["loaded"] is True
    assert by_id["values"]["loaded"] is True

    tle = attach_hint({"message": "tle"}, problem.tests, "TLE", 10000, public_only=False)
    assert tle["kill"]["weapon"] == "complexity"
    ac = attach_hint({}, problem.tests, "AC", 10000, public_only=False)
    assert ac["kill"]["cleared"] is True
    assert ac["kill"]["weapon"] is None
