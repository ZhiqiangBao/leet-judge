from __future__ import annotations

import os
import shutil
from pathlib import Path

from ..base import CompileResult, LanguageAdapter
from ..sandbox import run_limited
from .bins import find_tool
from .idents import inner_list, snake
from .versions import fmt_version, rust_edition, rustc_version

JSON_RS = Path(__file__).resolve().parents[1] / "runtimes" / "rust" / "mini_json.rs"


def rust_type(type_name: str) -> str:
    t = type_name.strip()
    inner = inner_list(t)
    if inner is not None:
        return f"Vec<{rust_type(inner)}>"
    return {"int": "i32", "long": "i64", "float": "f64", "bool": "bool", "str": "String"}[t]


def rust_fn(type_name: str) -> str:
    return "leet_from_" + type_name.replace("[", "_").replace("]", "").replace(" ", "")


def rust_to_json_fn(type_name: str) -> str:
    return "leet_to_json_" + type_name.replace("[", "_").replace("]", "").replace(" ", "")


def emit_rust_converters(types: list[str]) -> str:
    seen: set[str] = set()
    chunks: list[str] = []

    def emit(type_name: str) -> None:
        if type_name in seen:
            return
        inner = inner_list(type_name)
        if inner is not None:
            emit(inner)
        seen.add(type_name)
        fn = rust_fn(type_name)
        toj = rust_to_json_fn(type_name)
        rt = rust_type(type_name)
        if type_name == "int":
            chunks.append(f"fn {fn}(v: &JsonValue) -> Result<i32, String> {{ v.as_i32() }}")
            chunks.append(f"fn {toj}(v: i32) -> JsonValue {{ json_from_i32(v) }}")
        elif type_name == "long":
            chunks.append(f"fn {fn}(v: &JsonValue) -> Result<i64, String> {{ v.as_i64() }}")
            chunks.append(f"fn {toj}(v: i64) -> JsonValue {{ json_from_i64(v) }}")
        elif type_name == "float":
            chunks.append(f"fn {fn}(v: &JsonValue) -> Result<f64, String> {{ v.as_f64() }}")
            chunks.append(f"fn {toj}(v: f64) -> JsonValue {{ json_from_f64(v) }}")
        elif type_name == "bool":
            chunks.append(f"fn {fn}(v: &JsonValue) -> Result<bool, String> {{ v.as_bool() }}")
            chunks.append(f"fn {toj}(v: bool) -> JsonValue {{ json_from_bool(v) }}")
        elif type_name == "str":
            chunks.append(f"fn {fn}(v: &JsonValue) -> Result<String, String> {{ v.as_string() }}")
            chunks.append(f"fn {toj}(v: String) -> JsonValue {{ json_from_string(v) }}")
        else:
            inner_fn = rust_fn(inner or "")
            inner_to = rust_to_json_fn(inner or "")
            chunks.append(
                f"fn {fn}(v: &JsonValue) -> Result<{rt}, String> {{\n"
                f"    v.as_array()?.iter().map({inner_fn}).collect()\n"
                f"}}"
            )
            chunks.append(
                f"fn {toj}(v: {rt}) -> JsonValue {{\n"
                f"    json_from_vec(v, {inner_to})\n"
                f"}}"
            )

    for t in types:
        emit(t)
    return "\n".join(chunks)


def wrap_rust(user_code: str, signature: dict) -> str:
    method = snake(signature["method"])
    compare = signature.get("compare") or "exact"
    params = signature.get("params") or []
    return_type = signature["return_type"]
    types = [p["type"] for p in params] + [return_type]
    converters = emit_rust_converters(types)
    binds = []
    call_args = []
    for i, p in enumerate(params):
        binds.append(
            f"        let arg{i} = {rust_fn(p['type'])}(&args[{i}])?;"
        )
        call_args.append(f"arg{i}")
    bind = "\n".join(binds)
    call = ", ".join(call_args)
    any_order = "true" if compare == "any_order" else "false"
    toj = rust_to_json_fn(return_type)
    return f'''#![allow(dead_code, unused_imports)]
{user_code.rstrip()}

include!("mini_json.rs");

{converters}

fn leet_emit(v: &JsonValue) {{
    println!("{{}}", v.dumps());
}}

fn leet_payload(verdict: &str, extra: Vec<(&str, JsonValue)>) -> JsonValue {{
    let mut obj = std::collections::BTreeMap::new();
    obj.insert("verdict".into(), JsonValue::Str(verdict.into()));
    for (k, v) in extra {{
        obj.insert(k.into(), v);
    }}
    JsonValue::Obj(obj)
}}

fn leet_run() -> Result<(), String> {{
    let stdin = std::io::stdin();
    let mut lock = stdin.lock();
    let mut line_buf = String::new();
    let mut index: i64 = 0;
    loop {{
        line_buf.clear();
        let n = std::io::BufRead::read_line(&mut lock, &mut line_buf).map_err(|e| e.to_string())?;
        if n == 0 {{
            break;
        }}
        let line = line_buf.trim();
        if line.is_empty() {{
            continue;
        }}
        let root = JsonParser::parse(line)?;
        let args = root.get("args")?.as_array()?;
        let expected = root.get("expected")?;
{bind}
        let got = Solution::{method}({call});
        let gotj = {toj}(got);
        if !json_equal(&gotj, expected, {any_order}) {{
            leet_emit(&leet_payload("WA", vec![
                ("failed_index", JsonValue::Int(index)),
                ("got", gotj),
                ("passed", JsonValue::Int(index)),
                ("total", JsonValue::Int(index)),
            ]));
            return Ok(());
        }}
        index += 1;
    }}
    leet_emit(&leet_payload("AC", vec![
        ("passed", JsonValue::Int(index)),
        ("total", JsonValue::Int(index)),
    ]));
    Ok(())
}}

fn main() {{
    match leet_run() {{
        Ok(()) => {{}}
        Err(message) => {{
            leet_emit(&leet_payload("RE", vec![
                ("message", JsonValue::Str(message)),
            ]));
        }}
    }}
}}
'''


class RustAdapter(LanguageAdapter):
    id = "rust"
    display_name = "Rust"
    source_filename = "solution.rs"
    implemented = True

    def rustc(self) -> str | None:
        return find_tool("rustc", linux_paths=("/usr/bin/rustc", "/usr/local/bin/rustc"))

    def detect(self) -> bool:
        return self.rustc() is not None

    def runtime_version(self) -> str | None:
        path = self.rustc()
        return fmt_version(rustc_version(path)) if path else None

    def wrap(self, user_code: str, signature: dict) -> str:
        return wrap_rust(user_code, signature)

    def compile(self, workdir: str) -> CompileResult:
        compiler = self.rustc()
        if not compiler:
            return CompileResult(ok=False, log="rustc not found")
        shutil.copy2(JSON_RS, Path(workdir) / "mini_json.rs")
        out = "program.exe" if os.name == "nt" else "program"
        result = run_limited(
            [compiler, "-O", "--edition", rust_edition(rustc_version(compiler)), "-o", out, self.source_filename],
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
