from __future__ import annotations

import io
import shutil
import zipfile
from pathlib import Path

from app.services.problems import (
    ProblemBank,
    ProblemError,
    extract_problem_zip,
    write_upload_tree,
)


def _write_slug(root: Path, slug: str) -> Path:
    dest = root / slug
    dest.mkdir(parents=True)
    (dest / "starter").mkdir()
    (dest / "meta.yaml").write_text(
        f"slug: {slug}\ntitle: T\ndifficulty: easy\ntime_limit_ms: 2000\nmemory_limit_mb: 256\ntags: []\n",
        encoding="utf-8",
    )
    (dest / "statement.md").write_text("# T\n", encoding="utf-8")
    (dest / "signature.yaml").write_text(
        "class_name: Solution\nmethod: foo\nparams:\n  - name: x\n    type: int\nreturn_type: int\ncompare: exact\n",
        encoding="utf-8",
    )
    (dest / "tests.jsonl").write_text(
        '{"args":[1],"expected":1,"hidden":false}\n{"args":[2],"expected":2,"hidden":true}\n',
        encoding="utf-8",
    )
    (dest / "starter" / "python3.py").write_text("class Solution:\n    def foo(self, x: int) -> int:\n        return x\n", encoding="utf-8")
    return dest


def test_import_copies_jsonl_as_lines(tmp_path: Path):
    src_root = tmp_path / "src"
    bank_root = tmp_path / "bank"
    bank_root.mkdir()
    _write_slug(src_root, "demo-slug")
    bank = ProblemBank(bank_root)
    slugs = bank.import_tree(src_root / "demo-slug", overwrite=False)
    assert slugs == ["demo-slug"]
    problem = bank.get("demo-slug")
    assert problem.test_count == 2
    assert problem.hidden_flags == (False, True)
    raw = (bank_root / "demo-slug" / "tests.jsonl").read_text(encoding="utf-8")
    assert '"args":[2]' in raw
    assert problem.tests_stdin().splitlines()[1] == '{"args":[2],"expected":2,"hidden":true}'


def test_import_zip_problems_prefix(tmp_path: Path):
    src = tmp_path / "src"
    _write_slug(src / "problems", "zip-slug")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for file in (src / "problems" / "zip-slug").rglob("*"):
            if file.is_file():
                zf.write(file, file.relative_to(src).as_posix())
    dest = tmp_path / "unz"
    extract_problem_zip(buf.getvalue(), dest)
    bank = ProblemBank(tmp_path / "bank")
    assert bank.import_tree(dest) == ["zip-slug"]


def test_write_upload_tree_rejects_dotdot(tmp_path: Path):
    dest = tmp_path / "t"
    dest.mkdir()
    try:
        write_upload_tree([("../x", b"no")], dest)
        assert False
    except ProblemError:
        pass


def test_import_refuses_overwrite(tmp_path: Path):
    src = tmp_path / "src"
    bank_root = tmp_path / "bank"
    bank_root.mkdir()
    _write_slug(src, "keep-me")
    bank = ProblemBank(bank_root)
    bank.import_tree(src / "keep-me")
    try:
        bank.import_tree(src / "keep-me", overwrite=False)
        assert False
    except ProblemError as exc:
        assert "已存在" in str(exc)


def test_merge_files_creates_slug_dir(tmp_path: Path):
    incoming = tmp_path / "up"
    _write_slug(incoming, "file-slug")
    bank = ProblemBank(tmp_path / "bank")
    problem = bank.merge_files("file-slug", incoming / "file-slug")
    assert problem.slug == "file-slug"
    dest = tmp_path / "bank" / "file-slug"
    assert (dest / "meta.yaml").is_file()
    assert (dest / "tests.jsonl").read_text(encoding="utf-8").splitlines()[1].startswith('{"args":[2]')
    assert not (dest / "starter").exists()


def test_merge_files_refuses_partial_create(tmp_path: Path):
    incoming = tmp_path / "up"
    incoming.mkdir()
    (incoming / "statement.md").write_text("# T\n", encoding="utf-8")
    bank = ProblemBank(tmp_path / "bank")
    try:
        bank.merge_files("half-slug", incoming)
        assert False
    except ProblemError as exc:
        assert "四个文件" in str(exc)
    assert not (tmp_path / "bank" / "half-slug").exists()


def test_merge_files_patches_existing(tmp_path: Path):
    root = tmp_path / "bank"
    root.mkdir()
    _write_slug(root, "keep-me")
    bank = ProblemBank(root)
    incoming = tmp_path / "patch"
    incoming.mkdir()
    (incoming / "statement.md").write_text("# patched\n", encoding="utf-8")
    problem = bank.merge_files("keep-me", incoming)
    assert problem.statement_md.startswith("# patched")
    assert (root / "keep-me" / "meta.yaml").is_file()
    assert (root / "keep-me" / "starter" / "python3.py").is_file()


def test_write_starters_from_signature_not_qwen(tmp_path: Path):
    root = tmp_path / "bank"
    root.mkdir()
    _write_slug(root, "file-slug")
    shutil.rmtree(root / "file-slug" / "starter")
    bank = ProblemBank(root)
    out = bank.write_starters("file-slug")
    assert "python3" in out["wrote"]
    text = (root / "file-slug" / "starter" / "python3.py").read_text(encoding="utf-8")
    assert "def foo(" in text
    assert "return x" not in text
    assert bank.get("file-slug").starter["python3"] == text
