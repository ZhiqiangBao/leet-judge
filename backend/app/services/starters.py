"""Empty function starters from a problem signature. Judge-owned; not the Qwen authoring tools."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from ..judge.typespec import c_maps
from ..schemas import Signature

CORE_LANGS = ("python3", "c", "cpp17")
EXT = {
    "python3": ".py",
    "c": ".c",
    "cpp17": ".cpp",
    "javascript": ".js",
    "go": ".go",
    "rust": ".rs",
    "zig": ".zig",
    "typescript": ".ts",
}


def inner_list(type_name: str) -> str | None:
    t = type_name.strip()
    if t.startswith("List[") and t.endswith("]"):
        return t[5:-1].strip()
    return None


def pascal(name: str) -> str:
    if "_" in name:
        return "".join(p[:1].upper() + p[1:] for p in name.split("_") if p)
    return name[:1].upper() + name[1:]


def snake(name: str) -> str:
    out: list[str] = []
    for i, ch in enumerate(name):
        if ch.isupper() and i and name[i - 1] != "_":
            out.append("_")
        out.append(ch.lower())
    return "".join(out).replace("__", "_")


def py_type(type_name: str) -> str:
    t = type_name.strip()
    inner = inner_list(t)
    if inner is not None:
        return f"list[{py_type(inner)}]"
    return {"int": "int", "long": "int", "float": "float", "bool": "bool", "str": "str"}[t]


def _c_tables() -> tuple[dict[str, str], dict[str, str], dict[str, str]]:
    scalar, one, two = c_maps()
    return scalar, {k: v[0] for k, v in one.items()}, {k: v[0] for k, v in two.items()}


def c_params(params: list[dict[str, str]], return_type: str) -> str:
    scalar, ptr, ptr2 = _c_tables()
    parts: list[str] = []
    for p in params:
        t, name = p["type"], p["name"]
        inner = inner_list(t)
        if inner is None:
            parts.append(f"{scalar[t]} {name}")
            continue
        inner2 = inner_list(inner)
        if inner2 is not None:
            if inner_list(inner2) is not None or inner2 not in ptr2:
                raise ValueError(f"unsupported C param type: {t}")
            parts.append(f"{ptr2[inner2]} {name}")
            parts.append(f"int {name}Size")
            parts.append(f"int* {name}ColSize")
        else:
            if inner not in ptr:
                raise ValueError(f"unsupported C param type: {t}")
            parts.append(f"{ptr[inner]} {name}")
            parts.append(f"int {name}Size")
    ret_inner = inner_list(return_type)
    if ret_inner is not None:
        parts.append("int* returnSize")
        if inner_list(ret_inner) is not None:
            parts.append("int** returnColumnSizes")
    return ", ".join(parts)


def c_return(return_type: str) -> str:
    scalar, ptr, ptr2 = _c_tables()
    inner = inner_list(return_type)
    if inner is None:
        return scalar[return_type]
    inner2 = inner_list(inner)
    if inner2 is not None:
        if inner_list(inner2) is not None or inner2 not in ptr2:
            raise ValueError(f"unsupported C return type: {return_type}")
        return ptr2[inner2]
    if inner not in ptr:
        raise ValueError(f"unsupported C return type: {return_type}")
    return ptr[inner]


def cpp_type(type_name: str) -> str:
    t = type_name.strip()
    inner = inner_list(t)
    if inner is not None:
        return f"vector<{cpp_type(inner)}>"
    return {"int": "int", "long": "long long", "float": "double", "bool": "bool", "str": "string"}[t]


def cpp_param(type_name: str, name: str) -> str:
    ct = cpp_type(type_name)
    if inner_list(type_name) is not None:
        return f"{ct}& {name}"
    return f"{ct} {name}"


def js_doc(type_name: str) -> str:
    t = type_name.strip()
    inner = inner_list(t)
    if inner is not None:
        return f"{js_doc(inner)}[]"
    return {"int": "number", "long": "number", "float": "number", "bool": "boolean", "str": "string"}[t]


def go_type(type_name: str) -> str:
    t = type_name.strip()
    inner = inner_list(t)
    if inner is not None:
        return f"[]{go_type(inner)}"
    return {"int": "int", "long": "int64", "float": "float64", "bool": "bool", "str": "string"}[t]


def rust_type(type_name: str) -> str:
    t = type_name.strip()
    inner = inner_list(t)
    if inner is not None:
        return f"Vec<{rust_type(inner)}>"
    return {"int": "i32", "long": "i64", "float": "f64", "bool": "bool", "str": "String"}[t]


def zig_type(type_name: str, *, ret: bool = False) -> str:
    t = type_name.strip()
    inner = inner_list(t)
    if inner is not None:
        inner_ty = zig_type(inner, ret=ret or inner_list(inner) is not None)
        return f"[]{inner_ty}" if ret else f"[]const {inner_ty}"
    if t == "str":
        return "[]const u8"
    return {"int": "i32", "long": "i64", "float": "f64", "bool": "bool"}[t]


def _as_dict(sig: Signature) -> dict[str, Any]:
    return {
        "class_name": sig.class_name,
        "method": sig.method,
        "params": [{"name": p.name, "type": p.type} for p in sig.params],
        "return_type": sig.return_type,
    }


def emit_python3(sig: dict[str, Any]) -> str:
    args = ", ".join(["self"] + [f"{p['name']}: {py_type(p['type'])}" for p in sig["params"]])
    ret = py_type(sig["return_type"])
    return f"class {sig['class_name']}:\n    def {sig['method']}({args}) -> {ret}:\n        \n"


def emit_c(sig: dict[str, Any]) -> str:
    ret = c_return(sig["return_type"])
    args = c_params(sig["params"], sig["return_type"])
    header = ""
    ret_inner = inner_list(sig["return_type"])
    if ret_inner is not None and inner_list(ret_inner) is not None:
        header = (
            "/**\n"
            " * Return an array of arrays of size *returnSize.\n"
            " * The sizes of the arrays are returned as *returnColumnSizes array.\n"
            " * Note: Both returned array and *returnColumnSizes array must be malloced,"
            " assume caller calls free().\n"
            " */\n"
        )
    elif ret_inner is not None:
        header = (
            "/**\n"
            " * Note: The returned array must be malloced, assume caller calls free().\n"
            " */\n"
        )
    return f"{header}{ret} {sig['method']}({args}) {{\n    \n}}\n"


def emit_cpp17(sig: dict[str, Any]) -> str:
    args = ", ".join(cpp_param(p["type"], p["name"]) for p in sig["params"])
    ret = cpp_type(sig["return_type"])
    return (
        f"class {sig['class_name']} {{\n"
        f"public:\n"
        f"    {ret} {sig['method']}({args}) {{\n"
        f"        \n"
        f"    }}\n"
        f"}};\n"
    )


def emit_javascript(sig: dict[str, Any]) -> str:
    args = ", ".join(p["name"] for p in sig["params"])
    docs = [f"     * @param {{{js_doc(p['type'])}}} {p['name']}" for p in sig["params"]]
    docs.append(f"     * @return {{{js_doc(sig['return_type'])}}}")
    doc = "    /**\n" + "\n".join(docs) + "\n     */\n"
    return (
        f"class {sig['class_name']} {{\n"
        f"{doc}"
        f"    {sig['method']}({args}) {{\n"
        f"        \n"
        f"    }}\n"
        f"}}\n"
    )


def emit_typescript(sig: dict[str, Any]) -> str:
    args = ", ".join(f"{p['name']}: {js_doc(p['type'])}" for p in sig["params"])
    ret = js_doc(sig["return_type"])
    return (
        f"class {sig['class_name']} {{\n"
        f"    {sig['method']}({args}): {ret} {{\n"
        f"        \n"
        f"    }}\n"
        f"}}\n"
    )


def emit_go(sig: dict[str, Any]) -> str:
    args = ", ".join(f"{p['name']} {go_type(p['type'])}" for p in sig["params"])
    ret = go_type(sig["return_type"])
    method = pascal(sig["method"])
    used = {p["name"] for p in sig["params"]}
    recv = "this" if "sol" in used else "sol"
    return (
        f"package main\n"
        f"\n"
        f"type {sig['class_name']} struct{{}}\n"
        f"\n"
        f"func ({recv} *{sig['class_name']}) {method}({args}) {ret} {{\n"
        f"    \n"
        f"}}\n"
    )


def emit_rust(sig: dict[str, Any]) -> str:
    args = ", ".join(f"{p['name']}: {rust_type(p['type'])}" for p in sig["params"])
    ret = rust_type(sig["return_type"])
    method = snake(sig["method"])
    cls = sig["class_name"]
    return (
        f"pub struct {cls};\n"
        f"\n"
        f"impl {cls} {{\n"
        f"    pub fn {method}({args}) -> {ret} {{\n"
        f"        \n"
        f"    }}\n"
        f"}}\n"
    )


def emit_zig(sig: dict[str, Any]) -> str:
    args = ", ".join(
        ["self: @This()"] + [f"{p['name']}: {zig_type(p['type'])}" for p in sig["params"]]
    )
    ret = zig_type(sig["return_type"], ret=True)
    return (
        f"const {sig['class_name']} = struct {{\n"
        f"    pub fn {sig['method']}({args}) {ret} {{\n"
        f"        \n"
        f"    }}\n"
        f"}};\n"
    )


EMITTERS = {
    "python3": emit_python3,
    "c": emit_c,
    "cpp17": emit_cpp17,
    "javascript": emit_javascript,
    "typescript": emit_typescript,
    "go": emit_go,
    "rust": emit_rust,
    "zig": emit_zig,
}


def write_starter_files(problem_dir: Path, signature: Signature, langs: list[str]) -> dict[str, Any]:
    if not signature.method:
        raise ValueError("signature 缺少 method")
    payload = _as_dict(signature)
    dest = problem_dir / "starter"
    dest.mkdir(parents=True, exist_ok=True)
    wanted = [lang for lang in langs if lang in EMITTERS]
    wrote: list[str] = []
    skipped: list[str] = []
    for lang in wanted:
        try:
            text = EMITTERS[lang](payload)
        except (KeyError, ValueError) as exc:
            skipped.append(f"{lang}:{exc}")
            continue
        (dest / f"{lang}{EXT[lang]}").write_text(text, encoding="utf-8")
        wrote.append(lang)
    ok = all(lang in wrote for lang in CORE_LANGS if lang in wanted)
    return {"ok": ok, "wrote": wrote, "skipped": skipped}
