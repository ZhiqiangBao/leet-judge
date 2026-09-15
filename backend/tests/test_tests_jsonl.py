from __future__ import annotations

from app.services.problems import dump_tests, jsonl_top_bool, parse_test_line
from app.services.problems import Problem


def test_hidden_flag_skips_nested_payload():
    line = '{"args":[' + ",".join(["1"] * 5000) + '],"expected":0,"hidden":true}'
    assert jsonl_top_bool(line) is True
    assert jsonl_top_bool('{"args":[1],"expected":1}') is False
    assert jsonl_top_bool('{ "args": [1], "expected": 1, "hidden": false }') is False


def test_stdin_keeps_raw_numbers_not_pydantic_dump(tmp_path):
    slug = tmp_path / "raw-float"
    slug.mkdir()
    (slug / "meta.yaml").write_text(
        "title: t\ndifficulty: easy\ntime_limit_ms: 1000\nmemory_limit_mb: 256\ntags: []\n",
        encoding="utf-8",
    )
    (slug / "statement.md").write_text("s", encoding="utf-8")
    (slug / "signature.yaml").write_text(
        "method: f\nparams:\n  - name: x\n    type: float\nreturn_type: float\n",
        encoding="utf-8",
    )
    raw = '{ "args": [1.0], "expected": 1.0, "hidden": true }\n'
    (slug / "tests.jsonl").write_text(raw, encoding="utf-8")
    problem = Problem(slug)
    stdin = problem.tests_stdin(public_only=False)
    dumped = dump_tests([parse_test_line(raw.strip())])
    assert "1.0" in stdin
    assert stdin.strip() != dumped.strip()
    assert problem.test_count == 1
    assert problem.hidden_flags == (True,)
    assert problem.public_tests() == []
    assert problem.test_at(0).expected == 1.0
    assert not hasattr(problem, "_test_lines")


def test_public_only_stdin_drops_hidden(tmp_path):
    slug = tmp_path / "mix"
    slug.mkdir()
    (slug / "meta.yaml").write_text(
        "title: t\ndifficulty: easy\ntime_limit_ms: 1000\nmemory_limit_mb: 256\ntags: []\n",
        encoding="utf-8",
    )
    (slug / "statement.md").write_text("s", encoding="utf-8")
    (slug / "signature.yaml").write_text(
        "method: f\nparams:\n  - name: x\n    type: int\nreturn_type: int\n",
        encoding="utf-8",
    )
    (slug / "tests.jsonl").write_text(
        '{"args":[1],"expected":1,"hidden":false}\n'
        '{"args":[2],"expected":2,"hidden":true}\n',
        encoding="utf-8",
    )
    problem = Problem(slug)
    assert problem.tests_stdin(public_only=True).strip() == '{"args":[1],"expected":1,"hidden":false}'
    pubs = problem.public_tests()
    assert len(pubs) == 1
    assert pubs[0].args == [1]


def test_load_does_not_require_tests_jsonl(tmp_path):
    slug = tmp_path / "no-tests"
    slug.mkdir()
    (slug / "meta.yaml").write_text(
        "title: t\ndifficulty: easy\ntime_limit_ms: 1000\nmemory_limit_mb: 256\ntags: []\n",
        encoding="utf-8",
    )
    (slug / "statement.md").write_text("s", encoding="utf-8")
    (slug / "signature.yaml").write_text(
        "method: f\nparams:\n  - name: x\n    type: int\nreturn_type: int\n",
        encoding="utf-8",
    )
    problem = Problem(slug)
    assert problem.test_count == 0
    assert not hasattr(problem, "_test_lines")


def test_run_limited_streams_stdin_lines(tmp_path):
    import sys

    from app.judge.sandbox import run_limited

    def feed():
        yield '{"args":[1],"expected":1,"hidden":false}'
        yield '{"args":[2],"expected":2,"hidden":true}'

    run = run_limited(
        [
            sys.executable,
            "-c",
            "import sys; print(sum(1 for line in sys.stdin if line.strip()))",
        ],
        cwd=tmp_path,
        stdin_lines=feed(),
        time_ms=5000,
        memory_mb=64,
    )
    assert run.returncode == 0
    assert run.stdout.strip() == "2"


def _tiny_problem(tmp_path, tests: str):
    slug = tmp_path / "p"
    slug.mkdir()
    (slug / "meta.yaml").write_text(
        "title: t\ndifficulty: easy\ntime_limit_ms: 1000\nmemory_limit_mb: 256\ntags: []\n",
        encoding="utf-8",
    )
    (slug / "statement.md").write_text("s", encoding="utf-8")
    (slug / "signature.yaml").write_text(
        "method: f\nparams:\n  - name: x\n    type: int\nreturn_type: int\n",
        encoding="utf-8",
    )
    (slug / "tests.jsonl").write_text(tests, encoding="utf-8")
    return Problem(slug)


def test_public_tests_stop_at_first_hidden(tmp_path):
    problem = _tiny_problem(
        tmp_path,
        '{"args":[1],"expected":1,"hidden":false}\n'
        '{"hidden":true,"args": not-valid-json\n',
    )
    pubs = problem.public_tests()
    assert len(pubs) == 1
    assert pubs[0].args == [1]
    stdin = problem.tests_stdin(public_only=True)
    assert "not-valid-json" not in stdin
    assert stdin.strip() == '{"args":[1],"expected":1,"hidden":false}'


def test_harnesses_judge_one_line_at_a_time():
    from app.judge.languages.c11 import wrap_c
    from app.judge.languages.cpp17 import wrap_cpp
    from app.judge.languages.go import wrap_go
    from app.judge.languages.rust import wrap_rust
    from app.judge.languages.zig import zig_harness_source
    from app.judge.runtimes.node_harness import wrap_javascript
    from app.judge.runtimes.python_harness import wrap_python

    sig = {
        "method": "f",
        "class_name": "Solution",
        "params": [{"name": "x", "type": "int"}],
        "return_type": "int",
        "compare": "exact",
    }
    py = wrap_python("class Solution:\n    def f(self, x):\n        return x\n", sig)
    assert "tests.append" not in py
    assert "for line in sys.stdin" in py
    js = wrap_javascript("class Solution { f(x) { return x; } }", sig)
    assert "readFileSync" not in js
    assert "_readLine" in js
    cpp = wrap_cpp("class Solution { public: int f(int x) { return x; } };", sig)
    assert "vector<string> lines" not in cpp
    c = wrap_c("int f(int x) { return x; }", sig)
    assert "strdup(line)" not in c
    go = wrap_go(
        "package main\ntype Solution struct{}\nfunc (s *Solution) F(x int) int { return x }\n",
        sig,
    )
    assert "var lines []leetLine" not in go
    rs = wrap_rust("impl Solution { pub fn f(x: i32) -> i32 { x } }", sig)
    assert "read_to_string" not in rs
    for flavor in ("14", "15", "16"):
        z = zig_harness_source(flavor)
        assert "leetReadAll" not in z
        assert "tests.append" not in z
        assert "leetOneLine" in z


def test_python_harness_wa_does_not_need_later_lines(tmp_path):
    import json
    import sys

    from app.judge.runtimes.python_harness import wrap_python
    from app.judge.sandbox import run_limited

    src = wrap_python(
        "class Solution:\n    def f(self, x):\n        return x\n",
        {"method": "f", "class_name": "Solution", "compare": "exact"},
    )
    path = tmp_path / "solution.py"
    path.write_text(src, encoding="utf-8")
    run = run_limited(
        [sys.executable, "-I", str(path)],
        cwd=tmp_path,
        stdin_lines=[
            '{"args":[1],"expected":1}',
            '{"args":[2],"expected":0}',
            '{"args":[3],"expected":3}',
        ],
        time_ms=5000,
        memory_mb=64,
    )
    assert run.returncode == 0
    payload = json.loads(run.stdout.strip().splitlines()[-1])
    assert payload["verdict"] == "WA"
    assert payload["failed_index"] == 1
