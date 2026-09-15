"""Persistent g++ PCH for leet_std.hpp. Lives under data/cpp-pch, not the job dir."""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
from pathlib import Path

from ..config import DATA_DIR
from .sandbox import run_limited

CXX_FLAGS = ("-O2", "-std=c++20", "-pipe")
HEADER_NAME = "leet_std.hpp"
GCH_NAME = "leet_std.hpp.gch"
STD_HEADER = Path(__file__).resolve().parent / "runtimes" / "cpp" / "leet_std.hpp"


def pch_enabled() -> bool:
    return os.environ.get("LOCAL_LEET_CPP_PCH", "1").strip().lower() not in ("0", "false", "no", "off")


def pch_root() -> Path:
    return DATA_DIR / "cpp-pch"


def cache_key(compiler: str, header: Path | None = None) -> str:
    src = Path(header) if header is not None else STD_HEADER
    try:
        ver = subprocess.run(
            [compiler, "--version"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        version = (ver.stdout or "") + (ver.stderr or "")
    except (OSError, subprocess.TimeoutExpired):
        version = ""
    h = hashlib.sha256()
    h.update(str(Path(compiler).resolve()).encode("utf-8"))
    h.update(version.encode("utf-8"))
    h.update(" ".join(CXX_FLAGS).encode("utf-8"))
    h.update(src.read_bytes())
    return h.hexdigest()[:32]


def _lock(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    fh = open(path, "a+b")
    try:
        fh.seek(0)
        if fh.read(1) == b"":
            fh.write(b"0")
            fh.flush()
        fh.seek(0)
        if sys.platform == "win32":
            import msvcrt

            msvcrt.locking(fh.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl

            fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
    except Exception:
        fh.close()
        raise
    return fh


def _unlock(fh) -> None:
    try:
        if sys.platform == "win32":
            import msvcrt

            fh.seek(0)
            msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
    finally:
        fh.close()


def _prune(keep: Path) -> None:
    root = keep.parent
    if not root.is_dir():
        return
    for child in root.iterdir():
        if child == keep or child.name.startswith("."):
            continue
        if child.is_dir():
            shutil.rmtree(child, ignore_errors=True)


def ensure_pch(compiler: str) -> Path | None:
    """Return dir with leet_std.hpp + .gch, or None to compile without PCH."""
    if not pch_enabled():
        return None
    if not STD_HEADER.is_file():
        return None
    key = cache_key(compiler)
    dest = pch_root() / key
    gch = dest / GCH_NAME
    hdr = dest / HEADER_NAME
    if gch.is_file() and hdr.is_file() and hdr.read_bytes() == STD_HEADER.read_bytes():
        return dest

    lock_fh = _lock(pch_root() / ".lock")
    try:
        if gch.is_file() and hdr.is_file() and hdr.read_bytes() == STD_HEADER.read_bytes():
            return dest
        dest.mkdir(parents=True, exist_ok=True)
        shutil.copy2(STD_HEADER, hdr)
        building = dest / (GCH_NAME + ".new")
        if building.exists():
            building.unlink()
        result = run_limited(
            [compiler, *CXX_FLAGS, "-x", "c++-header", HEADER_NAME, "-o", building.name],
            cwd=dest,
            stdin="",
            time_ms=60000,
            memory_mb=4096,
            for_compile=True,
        )
        if result.tle or result.returncode != 0 or not building.is_file():
            if building.exists():
                building.unlink(missing_ok=True)
            return None
        os.replace(building, gch)
        _prune(dest)
        return dest
    finally:
        _unlock(lock_fh)
