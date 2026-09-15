from __future__ import annotations

import os
from pathlib import Path

from ..base import CompileResult, LanguageAdapter
from ..sandbox import run_limited
from .bins import find_tool
from .idents import inner_list, pascal
from .versions import fmt_version, go_mod_directive, go_version

GO_HELPERS = r'''
func leetClose(a, b interface{}) bool {
	switch x := a.(type) {
	case bool:
		y, ok := b.(bool)
		return ok && x == y
	case string:
		y, ok := b.(string)
		return ok && x == y
	case float64:
		y, ok := b.(float64)
		if !ok {
			return false
		}
		if x == math.Trunc(x) && y == math.Trunc(y) && math.Abs(x) < 1e15 && math.Abs(y) < 1e15 {
			return int64(x) == int64(y)
		}
		d := math.Abs(x - y)
		return d <= 1e-6 || d <= 1e-6*math.Max(math.Abs(x), math.Abs(y))
	case []interface{}:
		y, ok := b.([]interface{})
		if !ok || len(x) != len(y) {
			return false
		}
		for i := range x {
			if !leetClose(x[i], y[i]) {
				return false
			}
		}
		return true
	default:
		return false
	}
}

func leetKey(v interface{}) string {
	b, _ := json.Marshal(v)
	return string(b)
}

func leetEq(got, expected interface{}, anyOrder bool) bool {
	if anyOrder {
		g, ok1 := got.([]interface{})
		e, ok2 := expected.([]interface{})
		if ok1 && ok2 {
			if len(g) != len(e) {
				return false
			}
			gs := append([]interface{}(nil), g...)
			es := append([]interface{}(nil), e...)
			sort.Slice(gs, func(i, j int) bool { return leetKey(gs[i]) < leetKey(gs[j]) })
			sort.Slice(es, func(i, j int) bool { return leetKey(es[i]) < leetKey(es[j]) })
			for i := range gs {
				if leetKey(gs[i]) != leetKey(es[i]) && !leetClose(gs[i], es[i]) {
					return false
				}
			}
			return true
		}
	}
	return leetClose(got, expected)
}

func leetEmit(v interface{}) {
	b, _ := json.Marshal(v)
	os.Stdout.Write(append(b, '\n'))
}

func leetAsAny(v interface{}) interface{} {
	b, err := json.Marshal(v)
	if err != nil {
		panic(err)
	}
	var out interface{}
	if err := json.Unmarshal(b, &out); err != nil {
		panic(err)
	}
	return out
}
'''


def go_type(type_name: str) -> str:
    t = type_name.strip()
    inner = inner_list(t)
    if inner is not None:
        return "[]" + go_type(inner)
    return {"int": "int", "long": "int64", "float": "float64", "bool": "bool", "str": "string"}[t]


def go_conv(type_name: str, expr: str) -> str:
    return f"leetConv_{type_name.replace('[', '_').replace(']', '')}({expr})"


def emit_go_converters(types: list[str]) -> str:
    seen: set[str] = set()
    chunks: list[str] = []

    def emit(type_name: str) -> None:
        if type_name in seen:
            return
        inner = inner_list(type_name)
        if inner is not None:
            emit(inner)
        seen.add(type_name)
        fn = f"leetConv_{type_name.replace('[', '_').replace(']', '')}"
        gt = go_type(type_name)
        if inner is None:
            chunks.append(
                f"func {fn}(raw json.RawMessage) ({gt}, error) {{\n"
                f"\tvar v {gt}\n"
                f"\terr := json.Unmarshal(raw, &v)\n"
                f"\treturn v, err\n"
                f"}}"
            )
        else:
            chunks.append(
                f"func {fn}(raw json.RawMessage) ({gt}, error) {{\n"
                f"\tvar parts []json.RawMessage\n"
                f"\tif err := json.Unmarshal(raw, &parts); err != nil {{\n"
                f"\t\treturn nil, err\n"
                f"\t}}\n"
                f"\tout := make({gt}, len(parts))\n"
                f"\tfor i, p := range parts {{\n"
                f"\t\tx, err := leetConv_{inner.replace('[', '_').replace(']', '')}(p)\n"
                f"\t\tif err != nil {{\n"
                f"\t\t\treturn nil, err\n"
                f"\t\t}}\n"
                f"\t\tout[i] = x\n"
                f"\t}}\n"
                f"\treturn out, nil\n"
                f"}}"
            )

    for t in types:
        emit(t)
    return "\n\n".join(chunks)


def wrap_go(user_code: str, signature: dict) -> str:
    method = pascal(signature["method"])
    compare = signature.get("compare") or "exact"
    params = signature.get("params") or []
    return_type = signature["return_type"]
    types = [p["type"] for p in params] + [return_type]
    converters = emit_go_converters(types)
    binds = []
    call_args = []
    for i, p in enumerate(params):
        binds.append(
            f"\t\targ{i}, err := {go_conv(p['type'], f'line.Args[{i}]')}\n"
            f"\t\tif err != nil {{\n"
            f"\t\t\tleetEmit(map[string]any{{\"verdict\": \"RE\", \"failed_index\": index, \"message\": err.Error(), \"passed\": index, \"total\": index}})\n"
            f"\t\t\treturn\n"
            f"\t\t}}"
        )
        call_args.append(f"arg{i}")
    bind = "\n".join(binds)
    call = ", ".join(call_args)
    nil_fix = ""
    if inner_list(return_type) is not None:
        nil_fix = "\t\tif got == nil {\n\t\t\tgot = " + go_type(return_type) + "{}\n\t\t}\n"
    any_order = "true" if compare == "any_order" else "false"
    imports = (
        "import (\n"
        '\t"bufio"\n'
        '\t"encoding/json"\n'
        '\t"math"\n'
        '\t"os"\n'
        '\t"sort"\n'
        ")"
    )
    harness = f"""
type leetLine struct {{
	Args     []json.RawMessage `json:"args"`
	Expected json.RawMessage   `json:"expected"`
}}

{converters}

{GO_HELPERS}

func main() {{
	scanner := bufio.NewScanner(os.Stdin)
	buf := make([]byte, 0, 64*1024)
	scanner.Buffer(buf, 8<<20)
	sol := &Solution{{}}
	index := 0
	for scanner.Scan() {{
		text := scanner.Text()
		if text == "" {{
			continue
		}}
		var line leetLine
		if err := json.Unmarshal([]byte(text), &line); err != nil {{
			leetEmit(map[string]any{{"verdict": "RE", "message": err.Error()}})
			return
		}}
{bind}
		got := sol.{method}({call})
{nil_fix}		gotAny := leetAsAny(got)
		var expected any
		if err := json.Unmarshal(line.Expected, &expected); err != nil {{
			leetEmit(map[string]any{{"verdict": "RE", "failed_index": index, "message": err.Error(), "passed": index, "total": index}})
			return
		}}
		if !leetEq(gotAny, expected, {any_order}) {{
			leetEmit(map[string]any{{"verdict": "WA", "failed_index": index, "got": gotAny, "passed": index, "total": index}})
			return
		}}
		index++
	}}
	leetEmit(map[string]any{{"verdict": "AC", "passed": index, "total": index}})
}}
"""
    return _inject_after_package(user_code, imports) + "\n" + harness


def _inject_after_package(user_code: str, imports: str) -> str:
    lines = user_code.replace("\r\n", "\n").split("\n")
    out: list[str] = []
    inserted = False
    for line in lines:
        out.append(line)
        if not inserted and line.startswith("package "):
            out.append("")
            out.append(imports)
            inserted = True
    if not inserted:
        out = ["package main", "", imports, ""] + out
    return "\n".join(out).rstrip() + "\n"



class GoAdapter(LanguageAdapter):
    id = "go"
    display_name = "Go"
    source_filename = "solution.go"
    implemented = True

    def go_bin(self) -> str | None:
        return find_tool("go", linux_paths=("/usr/bin/go", "/usr/local/go/bin/go"))

    def detect(self) -> bool:
        return self.go_bin() is not None

    def runtime_version(self) -> str | None:
        path = self.go_bin()
        return fmt_version(go_version(path)) if path else None

    def wrap(self, user_code: str, signature: dict) -> str:
        return wrap_go(user_code, signature)

    def compile(self, workdir: str) -> CompileResult:
        compiler = self.go_bin()
        if not compiler:
            return CompileResult(ok=False, log="go not found")
        Path(workdir, "go.mod").write_text(
            "module solution\n\n" + go_mod_directive(go_version(compiler)) + "\n",
            encoding="utf-8",
        )
        out = "program.exe" if os.name == "nt" else "program"
        scratch = Path(workdir) / ".scratch"
        for name in ("gocache", "gotmp", "gomod", "gopath"):
            (scratch / name).mkdir(parents=True, exist_ok=True)
        result = run_limited(
            [compiler, "build", "-o", out, self.source_filename],
            cwd=Path(workdir),
            stdin="",
            time_ms=30000,
            memory_mb=4096,
            for_compile=True,
            extra_env={
                "CGO_ENABLED": "0",
                "GOPROXY": "off",
                "GOSUMDB": "off",
                "GOFLAGS": "-mod=mod",
                "GOTOOLCHAIN": "local",
                "GOENV": "off",
                "GOCACHE": str(scratch / "gocache"),
                "GOTMPDIR": str(scratch / "gotmp"),
                "GOMODCACHE": str(scratch / "gomod"),
                "GOPATH": str(scratch / "gopath"),
            },
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
