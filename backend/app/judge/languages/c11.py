from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

from ..base import CompileResult, LanguageAdapter
from ..sandbox import run_limited
from ..typespec import c_maps
from .idents import list_depth_leaf

JSON_HEADER = Path(__file__).resolve().parents[1] / "runtimes" / "c" / "json.h"

_C_SCALAR = {
    "int": ("int", "json_as_int", "json_from_int"),
    "long": ("long long", "json_as_long", "json_from_long"),
    "float": ("double", "json_as_double", "json_num"),
    "bool": ("bool", "json_as_bool", "json_from_bool"),
    "str": ("char*", "json_as_cstr", "json_from_cstr"),
}
_, _C_1D, _C_2D = c_maps()


def _emit_arg(index: int, type_name: str, name: str) -> tuple[list[str], list[str]]:
    lines: list[str] = []
    call: list[str] = []
    src = f"json_at(args, {index})"
    depth, leaf = list_depth_leaf(type_name)
    if depth == 0:
        if leaf not in _C_SCALAR:
            raise ValueError(f"unsupported C type: {type_name}")
        ctype, as_fn, _ = _C_SCALAR[leaf]
        lines.append(f"        {ctype} {name} = {as_fn}({src});")
        call.append(name)
        return lines, call
    if leaf not in _C_1D:
        raise ValueError(f"unsupported C type: {type_name}")
    if depth == 1:
        ptr, as_fn, _ = _C_1D[leaf]
        lines.append(f"        int {name}Size = 0;")
        lines.append(f"        {ptr} {name} = {as_fn}({src}, &{name}Size);")
        call.extend([name, f"{name}Size"])
        return lines, call
    if depth == 2:
        ptr, as_fn, _ = _C_2D[leaf]
        lines.append(f"        int {name}Size = 0;")
        lines.append(f"        int* {name}ColSize = NULL;")
        lines.append(f"        {ptr} {name} = {as_fn}({src}, &{name}Size, &{name}ColSize);")
        call.extend([name, f"{name}Size", f"{name}ColSize"])
        return lines, call
    raise ValueError(f"unsupported C type: {type_name}")


def _call_with_outs(method: str, joined: str, outs: str) -> str:
    if joined:
        return f"{method}({joined}, {outs})"
    return f"{method}({outs})"


def _emit_call(method: str, params: list[dict], return_type: str) -> str:
    prep: list[str] = []
    call: list[str] = []
    for i, p in enumerate(params):
        extra, names = _emit_arg(i, p["type"], p["name"])
        prep.extend(extra)
        call.extend(names)
    joined = ", ".join(call)
    depth, leaf = list_depth_leaf(return_type)
    if depth == 0:
        if leaf not in _C_SCALAR:
            raise ValueError(f"unsupported C return type: {return_type}")
        ctype, _, from_fn = _C_SCALAR[leaf]
        prep.append(f"        {ctype} got = {method}({joined});")
        prep.append(f"        JsonValue gotj = {from_fn}(got);")
        return "\n".join(prep)
    if leaf not in _C_1D:
        raise ValueError(f"unsupported C return type: {return_type}")
    if depth == 1:
        ptr, _, from_fn = _C_1D[leaf]
        prep.append("        int returnSize = 0;")
        prep.append(f"        {ptr} got = {_call_with_outs(method, joined, '&returnSize')};")
        prep.append(f"        JsonValue gotj = {from_fn}(got, returnSize);")
        return "\n".join(prep)
    if depth == 2:
        ptr, _, from_fn = _C_2D[leaf]
        prep.append("        int returnSize = 0;")
        prep.append("        int* returnColumnSizes = NULL;")
        prep.append(
            f"        {ptr} got = {_call_with_outs(method, joined, '&returnSize, &returnColumnSizes')};"
        )
        prep.append(f"        JsonValue gotj = {from_fn}(got, returnSize, returnColumnSizes);")
        return "\n".join(prep)
    raise ValueError(f"unsupported C return type: {return_type}")


def wrap_c(user_code: str, signature: dict) -> str:
    method = signature["method"]
    compare = signature.get("compare") or "exact"
    params = signature.get("params") or []
    return_type = signature["return_type"]
    any_order = "true" if compare == "any_order" else "false"
    body = _emit_call(method, params, return_type)
    return f'''#include "json.h"

{user_code.rstrip()}

int main(void) {{
    const int line_cap = 8 << 20;
    char *line = (char *)malloc((size_t)line_cap);
    if (!line) return 1;
    int index = 0;
    while (fgets(line, line_cap, stdin)) {{
        size_t n = strlen(line);
        while (n && (line[n - 1] == '\\n' || line[n - 1] == '\\r')) line[--n] = 0;
        if (!n) continue;
        JsonValue root = json_parse(line);
        const JsonValue *args = json_get(&root, "args");
        const JsonValue *expected = json_get(&root, "expected");
{body}
        if (!json_equal(&gotj, expected, {any_order})) {{
            char *got_s = json_dumps(&gotj);
            printf("{{\\"verdict\\":\\"WA\\",\\"failed_index\\":%d,\\"got\\":%s,\\"passed\\":%d,\\"total\\":%d}}\\n",
                   index, got_s, index, index);
            return 0;
        }}
        ++index;
    }}
    printf("{{\\"verdict\\":\\"AC\\",\\"passed\\":%d,\\"total\\":%d}}\\n", index, index);
    return 0;
}}
'''


class C11Adapter(LanguageAdapter):
    id = "c"
    display_name = "C"
    source_filename = "solution.c"
    implemented = True

    def gcc(self) -> str | None:
        if sys.platform.startswith("linux"):
            for path in ("/usr/bin/gcc", "/usr/local/bin/gcc"):
                if Path(path).exists():
                    return path
        return shutil.which("gcc")

    def detect(self) -> bool:
        return self.gcc() is not None

    def wrap(self, user_code: str, signature: dict) -> str:
        return wrap_c(user_code, signature)

    def compile(self, workdir: str) -> CompileResult:
        compiler = self.gcc()
        if not compiler:
            return CompileResult(ok=False, log="gcc not found")
        shutil.copy2(JSON_HEADER, Path(workdir) / "json.h")
        result = run_limited(
            [compiler, "-O2", "-std=gnu11", "-pipe", "-o", "program", self.source_filename, "-lm"],
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
        return CompileResult(ok=True)

    def run_argv(self, workdir: str) -> list[str]:
        exe = Path(workdir) / ("program.exe" if os.name == "nt" else "program")
        if not exe.exists():
            exe = Path(workdir) / "program"
        return [str(exe)]
