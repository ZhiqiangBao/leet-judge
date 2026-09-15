from __future__ import annotations

import re
import subprocess
from functools import lru_cache


def run_version(argv: list[str]) -> str:
    try:
        proc = subprocess.run(
            argv,
            capture_output=True,
            timeout=8,
            text=True,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return ((proc.stdout or "") + (proc.stderr or "")).strip()


def parse_semver(text: str) -> tuple[int, int, int] | None:
    match = re.search(r"(\d+)\.(\d+)(?:\.(\d+))?", text)
    if not match:
        return None
    return int(match.group(1)), int(match.group(2)), int(match.group(3) or 0)


@lru_cache(maxsize=16)
def go_version(bin_path: str) -> tuple[int, int, int] | None:
    return parse_semver(run_version([bin_path, "version"]))


@lru_cache(maxsize=16)
def rustc_version(bin_path: str) -> tuple[int, int, int] | None:
    return parse_semver(run_version([bin_path, "--version"]))


@lru_cache(maxsize=16)
def zig_version(bin_path: str) -> tuple[int, int, int] | None:
    return parse_semver(run_version([bin_path, "version"]))


def fmt_version(ver: tuple[int, int, int] | None) -> str | None:
    if not ver:
        return None
    return f"{ver[0]}.{ver[1]}.{ver[2]}"


def go_mod_directive(ver: tuple[int, int, int] | None) -> str:
    if ver is None:
        return "go 1.18"
    if ver >= (1, 22, 0):
        return "go 1.22"
    if ver >= (1, 18, 0):
        return f"go {ver[0]}.{ver[1]}"
    return f"go {ver[0]}.{ver[1]}"


def rust_edition(ver: tuple[int, int, int] | None) -> str:
    if ver and ver >= (1, 56, 0):
        return "2021"
    return "2018"


def zig_flavor(ver: tuple[int, int, int] | None) -> str:
    """Harness family: std IO / ArrayList changed at 0.15 and 0.16."""
    if ver is None:
        return "14"
    if ver >= (0, 16, 0):
        return "16"
    if ver >= (0, 15, 0):
        return "15"
    return "14"
