from __future__ import annotations

import io
import json
import math
import re
import shutil
import subprocess
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import yaml

from ..config import PROBLEMS_DIR, ROOT
from ..judge.typespec import is_allowed_type, languages_for_signature
from ..schemas import ParamSpec, Signature, TestCase

_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_REQUIRED_FILES = ("meta.yaml", "statement.md", "signature.yaml", "tests.jsonl")
_IMPORT_MAX_BYTES = 80 * 1024 * 1024
_IMPORT_MAX_UNCOMPRESSED = 512 * 1024 * 1024
_IMPORT_MAX_FILES = 800


class ProblemError(ValueError):
    pass


def coerce_meta_int(value: Any) -> int | None:
    """Read meta numbers. YAML 1.1 treats `1.0e9` (no sign after e) as a string."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return int(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            return None
        return int(value)
    if isinstance(value, str):
        text = value.strip().strip("'\"")
        if not text:
            return None
        try:
            return int(text, 10)
        except ValueError:
            try:
                parsed = float(text)
            except ValueError:
                return None
            if not math.isfinite(parsed):
                return None
            return int(parsed)
    return None


def _check_type(type_name: str) -> None:
    if not is_allowed_type(type_name):
        raise ProblemError(f"不支持的类型: {type_name}")


def parse_signature(raw: dict[str, Any]) -> Signature:
    sig = Signature(
        class_name=raw.get("class_name") or "Solution",
        method=raw["method"],
        params=[ParamSpec(**p) for p in raw.get("params") or []],
        return_type=raw["return_type"],
        compare=raw.get("compare") or "exact",
    )
    _check_type(sig.return_type)
    for param in sig.params:
        _check_type(param.type)
    return sig


def parse_tests(text: str) -> list[TestCase]:
    tests: list[TestCase] = []
    for line_no, line in enumerate(text.splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            tests.append(TestCase.model_validate(obj))
        except Exception as exc:
            raise ProblemError(f"tests.jsonl 第 {line_no} 行无效: {exc}") from exc
    return tests


def dump_tests(tests: list[TestCase]) -> str:
    lines = [
        json.dumps(t.model_dump(), ensure_ascii=False, separators=(",", ":"))
        for t in tests
    ]
    return "\n".join(lines) + ("\n" if lines else "")


def jsonl_lines(text: str) -> tuple[str, ...]:
    return tuple(line.strip() for line in text.splitlines() if line.strip())


def _skip_ws(s: str, i: int) -> int:
    n = len(s)
    while i < n and s[i] in " \t\r\n":
        i += 1
    return i


def _skip_string(s: str, i: int) -> int:
    n = len(s)
    i += 1
    while i < n:
        c = s[i]
        if c == "\\":
            i += 2
            continue
        if c == '"':
            return i + 1
        i += 1
    return n


def _skip_value(s: str, i: int) -> int:
    i = _skip_ws(s, i)
    n = len(s)
    if i >= n:
        return i
    c = s[i]
    if c == '"':
        return _skip_string(s, i)
    if c == "{":
        i += 1
        while i < n:
            i = _skip_ws(s, i)
            if i < n and s[i] == "}":
                return i + 1
            if i < n and s[i] == ",":
                i += 1
                continue
            if i >= n or s[i] != '"':
                return n
            i = _skip_string(s, i)
            i = _skip_ws(s, i)
            if i < n and s[i] == ":":
                i += 1
            i = _skip_value(s, i)
        return n
    if c == "[":
        i += 1
        while i < n:
            i = _skip_ws(s, i)
            if i < n and s[i] == "]":
                return i + 1
            if i < n and s[i] == ",":
                i += 1
                continue
            i = _skip_value(s, i)
        return n
    if s.startswith("true", i):
        return i + 4
    if s.startswith("false", i):
        return i + 5
    if s.startswith("null", i):
        return i + 4
    while i < n and s[i] in "+-0123456789.eE":
        i += 1
    return i


def jsonl_top_bool(line: str, key: str = "hidden", default: bool = False) -> bool:
    """Read a top-level JSON bool without materializing nested args/expected."""
    i = _skip_ws(line, 0)
    if i >= len(line) or line[i] != "{":
        return default
    i += 1
    n = len(line)
    while i < n:
        i = _skip_ws(line, i)
        if i < n and line[i] == "}":
            return default
        if i < n and line[i] == ",":
            i += 1
            continue
        if i >= n or line[i] != '"':
            return default
        start = i
        i = _skip_string(line, i)
        try:
            field = json.loads(line[start:i])
        except json.JSONDecodeError:
            return default
        i = _skip_ws(line, i)
        if i < n and line[i] == ":":
            i += 1
        if field == key:
            i = _skip_ws(line, i)
            if line.startswith("true", i):
                return True
            if line.startswith("false", i):
                return False
            return default
        i = _skip_value(line, i)
    return default


def parse_test_line(line: str) -> TestCase:
    return TestCase.model_validate(json.loads(line))


def load_added_dates(problems_root: Path) -> dict[str, datetime]:
    """First git add of problems/<slug>/meta.yaml; empty if git is unavailable."""
    out: dict[str, datetime] = {}
    try:
        proc = subprocess.run(
            [
                "git",
                "log",
                "--diff-filter=A",
                "--reverse",
                "--name-only",
                "--pretty=format:%cI",
                "--",
                "problems",
            ],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=8,
        )
    except (OSError, subprocess.TimeoutExpired):
        return out
    if proc.returncode != 0:
        return out
    current: datetime | None = None
    for raw in proc.stdout.splitlines():
        line = raw.strip()
        if not line:
            current = None
            continue
        if line[0].isdigit() and "T" in line:
            try:
                current = datetime.fromisoformat(line.replace("Z", "+00:00"))
            except ValueError:
                current = None
            continue
        if current is None:
            continue
        parts = line.replace("\\", "/").split("/")
        if len(parts) >= 3 and parts[0] == "problems" and parts[-1] == "meta.yaml":
            slug = parts[1]
            if slug not in out:
                out[slug] = current
    _ = problems_root
    return out


class Problem:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.slug = path.name
        meta_path = path / "meta.yaml"
        statement_path = path / "statement.md"
        signature_path = path / "signature.yaml"
        tests_path = path / "tests.jsonl"
        if not meta_path.is_file() or not statement_path.is_file() or not signature_path.is_file():
            raise ProblemError(f"题目 {self.slug} 缺少 meta/statement/signature")
        meta = yaml.safe_load(meta_path.read_text(encoding="utf-8")) or {}
        self.title = str(meta.get("title") or self.slug)
        self.difficulty = str(meta.get("difficulty") or "easy")
        self.time_limit_ms = int(meta.get("time_limit_ms") or 2000)
        self.memory_limit_mb = int(meta.get("memory_limit_mb") or 256)
        self.tags = [str(t) for t in (meta.get("tags") or [])]
        raw_nmax = meta.get("scale_max", meta.get("n_max"))
        self.n_max = coerce_meta_int(raw_nmax)
        raw_emin = meta.get("elem_min")
        raw_emax = meta.get("elem_max")
        if raw_emin is None or raw_emax is None:
            bound_map = meta.get("bounds") if isinstance(meta.get("bounds"), dict) else {}
            for slot in bound_map.values():
                if isinstance(slot, dict) and "min" in slot and "max" in slot:
                    if raw_emin is None:
                        raw_emin = slot.get("min")
                    if raw_emax is None:
                        raw_emax = slot.get("max")
                    if raw_emin is not None and raw_emax is not None:
                        break
        self.elem_min = coerce_meta_int(raw_emin)
        self.elem_max = coerce_meta_int(raw_emax)
        self.added_at = datetime.fromtimestamp(meta_path.stat().st_mtime, tz=timezone.utc)
        self.statement_md = statement_path.read_text(encoding="utf-8")
        self.signature = parse_signature(yaml.safe_load(signature_path.read_text(encoding="utf-8")) or {})
        allow = meta.get("languages")
        allowlist = [str(x) for x in allow] if allow else None
        type_names = [p.type for p in self.signature.params] + [self.signature.return_type]
        self.languages = languages_for_signature(type_names, allowlist)
        self.tests_path = tests_path
        self._arsenal_cache: list[dict[str, Any]] | None = None
        self.starter: dict[str, str] = {}
        starter_dir = path / "starter"
        if starter_dir.is_dir():
            for file in starter_dir.iterdir():
                if file.is_file() and file.stem in self.languages:
                    self.starter[file.stem] = file.read_text(encoding="utf-8")

    def iter_test_lines(self):
        """Yield raw jsonl lines. Do not retain the file in memory."""
        path = self.tests_path
        if not path.is_file():
            return
        with path.open(encoding="utf-8") as handle:
            for raw in handle:
                line = raw.strip()
                if line:
                    yield line

    @property
    def tests_jsonl(self) -> str:
        lines = list(self.iter_test_lines())
        return "\n".join(lines) + ("\n" if lines else "")

    @property
    def test_count(self) -> int:
        return sum(1 for _ in self.iter_test_lines())

    @property
    def hidden_flags(self) -> tuple[bool, ...]:
        return tuple(jsonl_top_bool(line) for line in self.iter_test_lines())

    def iter_public_test_lines(self):
        """Yield leading public jsonl lines. Stop at the first hidden case."""
        for line in self.iter_test_lines():
            if jsonl_top_bool(line):
                return
            yield line

    def public_tests(self) -> list[TestCase]:
        return [parse_test_line(line) for line in self.iter_public_test_lines()]

    def test_at(self, index: int) -> TestCase:
        for i, line in enumerate(self.iter_test_lines()):
            if i == index:
                return parse_test_line(line)
        raise IndexError(index)

    def tests_stdin(self, *, public_only: bool = False) -> str:
        if public_only:
            lines = list(self.iter_public_test_lines())
        else:
            lines = list(self.iter_test_lines())
        return "\n".join(lines) + ("\n" if lines else "")

    def iter_trap_tests(self):
        """Yield one parsed case at a time for arsenal(); do not retain the list."""
        for line in self.iter_test_lines():
            hidden = jsonl_top_bool(line)
            if not hidden:
                yield SimpleNamespace(hidden=False, args=[])
                continue
            obj = json.loads(line)
            yield SimpleNamespace(hidden=True, args=obj.get("args") or [])

    def meta_dict(self) -> dict[str, Any]:
        return {
            "slug": self.slug,
            "title": self.title,
            "difficulty": self.difficulty,
            "time_limit_ms": self.time_limit_ms,
            "memory_limit_mb": self.memory_limit_mb,
            "tags": self.tags,
        }


class ProblemBank:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or PROBLEMS_DIR
        self._items: dict[str, Problem] = {}
        self.reload()

    def reload(self) -> None:
        items: dict[str, Problem] = {}
        dates = load_added_dates(self.root)
        if self.root.is_dir():
            for path in sorted(self.root.iterdir()):
                if not path.is_dir() or path.name.startswith("."):
                    continue
                problem = Problem(path)
                if problem.slug in dates:
                    problem.added_at = dates[problem.slug]
                items[path.name] = problem
        self._items = items

    def list(self) -> list[Problem]:
        return list(self._items.values())

    def get(self, slug: str) -> Problem:
        problem = self._items.get(slug)
        if not problem:
            raise KeyError(slug)
        return problem

    def write_problem(
        self,
        *,
        slug: str,
        title: str,
        difficulty: str,
        time_limit_ms: int,
        memory_limit_mb: int,
        tags: list[str],
        statement_md: str,
        signature: Signature,
        starter: dict[str, str],
        tests: list[TestCase] | None = None,
        overwrite: bool = False,
    ) -> Problem:
        if not _SLUG_RE.match(slug):
            raise ProblemError("slug 只能包含小写字母、数字和连字符")
        dest = self.root / slug
        if dest.exists() and not overwrite:
            raise ProblemError(f"题目已存在: {slug}")
        dest.mkdir(parents=True, exist_ok=True)
        (dest / "starter").mkdir(exist_ok=True)
        meta = {
            "slug": slug,
            "title": title,
            "difficulty": difficulty,
            "time_limit_ms": time_limit_ms,
            "memory_limit_mb": memory_limit_mb,
            "tags": tags,
        }
        (dest / "meta.yaml").write_text(
            yaml.safe_dump(meta, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        (dest / "statement.md").write_text(statement_md, encoding="utf-8")
        (dest / "signature.yaml").write_text(
            yaml.safe_dump(signature.model_dump(), allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        if tests is not None:
            (dest / "tests.jsonl").write_text(dump_tests(tests), encoding="utf-8")
        for lang, code in starter.items():
            (dest / "starter" / f"{lang}{ _starter_ext(lang)}").write_text(code, encoding="utf-8")
        problem = Problem(dest)
        self._items[slug] = problem
        return problem

    def write_tests(self, slug: str, tests: list[TestCase], append: bool = False) -> Problem:
        problem = self.get(slug)
        chunk = dump_tests(tests)
        if append:
            existing = problem.tests_jsonl.rstrip("\n")
            text = f"{existing}\n{chunk}" if existing else chunk
        else:
            text = chunk
        (problem.path / "tests.jsonl").write_text(text, encoding="utf-8")
        self._items[slug] = Problem(problem.path)
        return self._items[slug]

    def import_slug_dir(self, src: Path, *, overwrite: bool = False) -> Problem:
        slug = _validate_slug_dir(src)
        dest = self.root / slug
        if dest.exists() and not overwrite:
            raise ProblemError(f"题目已存在: {slug}")
        tmp = self.root / f".import-{slug}"
        if tmp.exists():
            shutil.rmtree(tmp)
        shutil.copytree(src, tmp, ignore=shutil.ignore_patterns(".git", "__pycache__"))
        if dest.exists():
            shutil.rmtree(dest)
        tmp.rename(dest)
        problem = Problem(dest)
        self._items[slug] = problem
        return problem

    def merge_files(self, slug: str, incoming: Path) -> Problem:
        """Write uploaded files into problems/<slug>/. Never leave a half-built directory."""
        if not _SLUG_RE.match(slug):
            raise ProblemError("slug 只能包含小写字母、数字和连字符")
        uploaded = [name for name in _REQUIRED_FILES if (incoming / name).is_file()]
        if not uploaded:
            raise ProblemError("请上传 meta.yaml、statement.md、signature.yaml、tests.jsonl 中的至少一个")
        meta_path = incoming / "meta.yaml"
        if meta_path.is_file():
            try:
                meta = yaml.safe_load(meta_path.read_text(encoding="utf-8")) or {}
            except yaml.YAMLError as exc:
                raise ProblemError(f"meta.yaml 无效: {exc}") from exc
            meta_slug = str(meta.get("slug") or "").strip()
            if meta_slug and meta_slug != slug:
                raise ProblemError(f"meta.yaml 的 slug 是 {meta_slug}，与目录 {slug} 不一致")
        dest = self.root / slug
        exists = dest.is_dir()
        if not exists:
            missing = [name for name in _REQUIRED_FILES if name not in uploaded]
            if missing:
                raise ProblemError(f"新建 problems/{slug}/ 必须一次上传四个文件，还缺 {', '.join(missing)}")
        tmp = self.root / f".patch-{slug}"
        if tmp.exists():
            shutil.rmtree(tmp)
        try:
            if exists:
                shutil.copytree(dest, tmp, ignore=shutil.ignore_patterns(".git", "__pycache__"))
            else:
                tmp.mkdir(parents=True)
            for name in uploaded:
                shutil.copyfile(incoming / name, tmp / name)
            Problem(tmp)
        except ProblemError:
            if tmp.exists():
                shutil.rmtree(tmp, ignore_errors=True)
            raise
        except Exception as exc:
            if tmp.exists():
                shutil.rmtree(tmp, ignore_errors=True)
            raise ProblemError(str(exc)) from exc
        if dest.exists():
            shutil.rmtree(dest)
        tmp.rename(dest)
        problem = Problem(dest)
        self._items[slug] = problem
        return problem

    def write_starters(self, slug: str) -> dict[str, Any]:
        """Generate empty starters from signature.yaml. Does not read tests.jsonl."""
        from .starters import write_starter_files

        problem = self.get(slug)
        try:
            summary = write_starter_files(problem.path, problem.signature, problem.languages)
        except ValueError as exc:
            raise ProblemError(str(exc)) from exc
        self._items[slug] = Problem(problem.path)
        summary["slug"] = slug
        return summary

    def import_tree(self, tree: Path, *, overwrite: bool = False, fallback_slug: str = "") -> list[str]:
        dirs = discover_slug_dirs(tree, fallback_slug=fallback_slug)
        if not dirs:
            raise ProblemError("没有找到题目目录（需要 meta.yaml / statement.md / signature.yaml / tests.jsonl）")
        slugs: list[str] = []
        for src in dirs:
            slugs.append(self.import_slug_dir(src, overwrite=overwrite).slug)
        return slugs


def _validate_slug_dir(src: Path) -> str:
    slug = src.name
    if not _SLUG_RE.match(slug):
        raise ProblemError(f"无效 slug: {slug}")
    missing = [name for name in _REQUIRED_FILES if not (src / name).is_file()]
    if missing:
        raise ProblemError(f"{slug} 缺少 {', '.join(missing)}")
    return slug


def discover_slug_dirs(root: Path, fallback_slug: str = "") -> list[Path]:
    if all((root / name).is_file() for name in _REQUIRED_FILES):
        if _SLUG_RE.match(root.name):
            return [root]
        slug = fallback_slug.strip()
        if slug and _SLUG_RE.match(slug):
            alias = root.parent / slug
            if alias.resolve() != root.resolve():
                if alias.exists():
                    shutil.rmtree(alias)
                root.rename(alias)
                return [alias]
        raise ProblemError("题目文件在压缩包根上，请改用 <slug>/ 目录打包，或填写 slug")
    scan = root / "problems" if (root / "problems").is_dir() else root
    found: list[Path] = []
    if not scan.is_dir():
        return found
    for path in sorted(scan.iterdir()):
        if not path.is_dir() or path.name.startswith("."):
            continue
        if all((path / name).is_file() for name in _REQUIRED_FILES):
            found.append(path)
    return found


def _safe_zip_name(name: str) -> Path | None:
    raw = name.replace("\\", "/").lstrip("/")
    if not raw or raw.endswith("/"):
        return None
    path = Path(raw)
    if path.is_absolute() or ".." in path.parts:
        raise ProblemError(f"压缩包路径不合法: {name}")
    return path


def extract_problem_zip(data: bytes, dest: Path) -> Path:
    if len(data) > _IMPORT_MAX_BYTES:
        raise ProblemError("压缩包太大")
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as exc:
        raise ProblemError("不是有效的 zip") from exc
    infos = [info for info in zf.infolist() if not info.is_dir()]
    if len(infos) > _IMPORT_MAX_FILES:
        raise ProblemError("压缩包文件过多")
    uncompressed = sum(max(info.file_size, 0) for info in infos)
    if uncompressed > _IMPORT_MAX_UNCOMPRESSED:
        raise ProblemError("压缩包解压后太大")
    dest.mkdir(parents=True, exist_ok=True)
    for info in infos:
        rel = _safe_zip_name(info.filename)
        if rel is None:
            continue
        out = dest / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        with zf.open(info) as src, out.open("wb") as dst:
            shutil.copyfileobj(src, dst)
    return dest


def write_upload_tree(files: list[tuple[str, bytes]], dest: Path) -> Path:
    if len(files) > _IMPORT_MAX_FILES:
        raise ProblemError("上传文件过多")
    total = 0
    dest.mkdir(parents=True, exist_ok=True)
    for name, payload in files:
        total += len(payload)
        if total > _IMPORT_MAX_UNCOMPRESSED:
            raise ProblemError("上传体积太大")
        rel = _safe_zip_name(name)
        if rel is None:
            continue
        out = dest / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(payload)
    return dest


def _starter_ext(lang: str) -> str:
    return {
        "python3": ".py",
        "c": ".c",
        "cpp17": ".cpp",
        "javascript": ".js",
        "go": ".go",
        "rust": ".rs",
        "zig": ".zig",
        "typescript": ".ts",
    }.get(lang, ".txt")


bank = ProblemBank()
