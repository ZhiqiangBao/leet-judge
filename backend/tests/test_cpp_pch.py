from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from app.judge.cpp_pch import cache_key, ensure_pch, pch_enabled
from app.judge.languages.cpp17 import Cpp17Adapter, wrap_cpp


def _gxx() -> str | None:
    if Path("/usr/bin/g++").exists():
        return "/usr/bin/g++"
    return shutil.which("g++")


def test_pch_disabled(monkeypatch):
    monkeypatch.setenv("LOCAL_LEET_CPP_PCH", "0")
    assert pch_enabled() is False
    assert ensure_pch("g++") is None


def test_cache_key_tracks_header(tmp_path):
    a = tmp_path / "a.hpp"
    b = tmp_path / "b.hpp"
    a.write_text("#include <vector>\n", encoding="utf-8")
    b.write_text("#include <vector>\n#include <map>\n", encoding="utf-8")
    compiler = _gxx() or "g++"
    assert cache_key(compiler, a) != cache_key(compiler, b)
    assert cache_key(compiler, a) == cache_key(compiler, a)


@pytest.mark.skipif(_gxx() is None, reason="g++ not installed")
def test_pch_speeds_reuse(tmp_path, monkeypatch):
    monkeypatch.setattr("app.judge.cpp_pch.DATA_DIR", tmp_path)
    compiler = _gxx()
    first = ensure_pch(compiler)
    assert first is not None
    assert (first / "leet_std.hpp.gch").is_file()
    again = ensure_pch(compiler)
    assert again == first

    work = tmp_path / "job"
    work.mkdir()
    sig = {
        "class_name": "Solution",
        "method": "add",
        "params": [{"name": "a", "type": "int"}, {"name": "b", "type": "int"}],
        "return_type": "int",
        "compare": "exact",
    }
    (work / "solution.cpp").write_text(
        wrap_cpp("class Solution { public: int add(int a, int b) { return a + b; } };", sig),
        encoding="utf-8",
    )
    compiled = Cpp17Adapter().compile(str(work))
    assert compiled.ok, compiled.log
    assert not (work / "leet_std.hpp").exists()


_SIG = {
    "class_name": "Solution",
    "method": "add",
    "params": [{"name": "a", "type": "int"}, {"name": "b", "type": "int"}],
    "return_type": "int",
    "compare": "exact",
}


def test_wrap_cpp_resets_line_to_user_source():
    marker = "class Solution { public: int add(int a, int b) { return a + b; } };"
    src = wrap_cpp(marker, _SIG)
    _, rest = src.split("#line 1\n", 1)
    assert rest.startswith(marker)


@pytest.mark.skipif(_gxx() is None, reason="g++ not installed")
def test_cpp_syntax_error_line_matches_editor(tmp_path):
    user = (
        "class Solution {\n"
        "public:\n"
        "    int add(int a, int b) { return a + ; }\n"
        "};\n"
    )
    work = tmp_path / "job"
    work.mkdir()
    (work / "solution.cpp").write_text(wrap_cpp(user, _SIG), encoding="utf-8")
    compiled = Cpp17Adapter().compile(str(work))
    assert not compiled.ok
    log = compiled.log.replace("\\", "/")
    assert "solution.cpp:3:" in log
    assert "solution.cpp:8:" not in log
    assert "solution.cpp:9:" not in log
