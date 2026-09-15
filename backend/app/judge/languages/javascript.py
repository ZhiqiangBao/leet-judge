from __future__ import annotations

from pathlib import Path

from ..base import CompileResult, LanguageAdapter
from ..runtimes.node_harness import find_node, wrap_javascript
from ..sandbox import run_limited


class JavascriptAdapter(LanguageAdapter):
    id = "javascript"
    display_name = "JavaScript (Node)"
    source_filename = "solution.js"
    implemented = True

    def detect(self) -> bool:
        return find_node() is not None

    def wrap(self, user_code: str, signature: dict) -> str:
        return wrap_javascript(user_code, signature)

    def compile(self, workdir: str) -> CompileResult:
        node = find_node()
        if not node:
            return CompileResult(ok=False, log="node not found")
        src = str(Path(workdir) / self.source_filename)
        result = run_limited(
            [node, "--check", src],
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
        node = find_node()
        if not node:
            raise FileNotFoundError("node not found")
        return [node, "--no-warnings", self.source_filename]
