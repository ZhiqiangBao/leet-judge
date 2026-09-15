from __future__ import annotations

import shutil
import sys
from pathlib import Path


def first_existing(paths: list[str]) -> str | None:
    seen: set[str] = set()
    for path in paths:
        if not path or path in seen:
            continue
        seen.add(path)
        if Path(path).exists():
            return path
    return None


def find_tool(name: str, *, linux_paths: tuple[str, ...] = ()) -> str | None:
    candidates: list[str] = []
    if sys.platform.startswith("linux"):
        candidates.extend(linux_paths)
    found = shutil.which(name)
    if found:
        candidates.append(found)
    home = Path.home()
    if name == "rustc":
        candidates.append(str(home / ".cargo" / "bin" / "rustc"))
    if name == "go":
        candidates.append("/usr/local/go/bin/go")
    if name == "zig":
        candidates.extend(("/usr/local/zig/zig", str(home / ".local" / "bin" / "zig")))
    return first_existing(candidates)
