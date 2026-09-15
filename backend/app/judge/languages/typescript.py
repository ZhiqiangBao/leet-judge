from __future__ import annotations

import json
from pathlib import Path

from ..base import CompileResult, LanguageAdapter
from ..runtimes.node_harness import find_node, find_tsc, wrap_typescript
from ..sandbox import run_limited

TSCONFIG = {
    "compilerOptions": {
        "target": "ES2020",
        "module": "commonjs",
        "lib": ["ES2020"],
        "skipLibCheck": True,
        "strict": False,
        "noEmitOnError": True,
        "outDir": ".",
        "rootDir": ".",
        "types": [],
        "typeRoots": [],
    },
    "files": ["solution.ts"],
}


class TypescriptAdapter(LanguageAdapter):
    id = "typescript"
    display_name = "TypeScript"
    source_filename = "solution.ts"
    implemented = True

    def detect(self) -> bool:
        return find_node() is not None and find_tsc() is not None

    def wrap(self, user_code: str, signature: dict) -> str:
        return wrap_typescript(user_code, signature)

    def compile(self, workdir: str) -> CompileResult:
        tsc = find_tsc()
        if not tsc:
            return CompileResult(ok=False, log="tsc not found")
        Path(workdir, "tsconfig.json").write_text(
            json.dumps(TSCONFIG, indent=2) + "\n",
            encoding="utf-8",
        )
        result = run_limited(
            tsc + ["-p", "tsconfig.json", "--pretty", "false"],
            cwd=Path(workdir),
            stdin="",
            time_ms=30000,
            memory_mb=4096,
            for_compile=True,
        )
        if result.tle:
            return CompileResult(ok=False, log="compile timeout")
        if result.returncode != 0:
            return CompileResult(ok=False, log=(result.stderr or result.stdout)[-8000:])
        if not (Path(workdir) / "solution.js").exists():
            return CompileResult(ok=False, log="tsc produced no solution.js")
        return CompileResult(ok=True, log="")

    def run_argv(self, workdir: str) -> list[str]:
        node = find_node()
        if not node:
            raise FileNotFoundError("node not found")
        return [node, "--no-warnings", "solution.js"]
