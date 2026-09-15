from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from ..base import CompileResult, LanguageAdapter
from ..runtimes.python_harness import wrap_python


def _works(path: str) -> bool:
    if "WindowsApps" in path:
        return False
    try:
        proc = subprocess.run(
            [path, "-c", "import sys; print(sys.version_info[0])"],
            capture_output=True,
            timeout=5,
            text=True,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return proc.returncode == 0 and proc.stdout.strip().startswith("3")


class Python3Adapter(LanguageAdapter):
    id = "python3"
    display_name = "Python 3"
    source_filename = "solution.py"
    implemented = True

    def __init__(self) -> None:
        super().__init__()
        self._bin: str | None | bool = False

    def python_bin(self) -> str | None:
        if self._bin is not False:
            return self._bin  # type: ignore[return-value]
        candidates: list[str] = []
        if sys.platform.startswith("linux"):
            candidates += ["/usr/bin/python3", "/usr/local/bin/python3"]
        for name in ("python3", "python"):
            found = shutil.which(name)
            if found:
                candidates.append(found)
        if sys.executable:
            candidates.append(sys.executable)
        seen: set[str] = set()
        for path in candidates:
            if path in seen:
                continue
            seen.add(path)
            if _works(path):
                self._bin = path
                return path
        self._bin = None
        return None

    def detect(self) -> bool:
        return self.python_bin() is not None

    def wrap(self, user_code: str, signature: dict) -> str:
        return wrap_python(user_code, signature)

    def compile(self, workdir: str) -> CompileResult:
        bin_path = self.python_bin()
        if not bin_path:
            return CompileResult(ok=False, log="python3 not found")
        src = str(Path(workdir) / self.source_filename)
        from ..sandbox import run_limited

        result = run_limited(
            [bin_path, "-m", "py_compile", src],
            cwd=Path(workdir),
            stdin="",
            time_ms=5000,
            memory_mb=256,
            for_compile=True,
        )
        if result.tle:
            return CompileResult(ok=False, log="compile timeout")
        if result.returncode != 0:
            return CompileResult(ok=False, log=(result.stderr or result.stdout)[-4000:])
        return CompileResult(ok=True, log="")

    def run_argv(self, workdir: str) -> list[str]:
        bin_path = self.python_bin()
        if not bin_path:
            raise FileNotFoundError("python3 not found")
        return [bin_path, "-I", self.source_filename]
