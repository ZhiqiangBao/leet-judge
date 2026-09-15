from __future__ import annotations

import os
from pathlib import Path

from ...config import DATA_DIR
from ..base import CompileResult, LanguageAdapter
from ..sandbox import run_limited
from .bins import find_tool
from .idents import inner_list
from .versions import fmt_version, zig_flavor, zig_version

# Debug uses Zig's self-hosted x86_64 backend on Linux (~5x vs LLVM).
# Per-job cache lives in workdir and is deleted with the TemporaryDirectory.
ZIG_COMPILE_MS = 30000
ZIG_OPT = "Debug"

# Ubuntu 26.04 `apt install zig` provides Zig 0.14.x (zig-defaults → zig0.14).


def zig_type(type_name: str, *, ret: bool = False) -> str:
    t = type_name.strip()
    inner = inner_list(t)
    if inner is not None:
        # Nested params use mutable inner slices so allocated [][]T coerces to []const []T.
        inner_ty = zig_type(inner, ret=ret or inner_list(inner) is not None)
        return f"[]{inner_ty}" if ret else f"[]const {inner_ty}"
    if t == "str":
        return "[]const u8"
    return {"int": "i32", "long": "i64", "float": "f64", "bool": "bool"}[t]


def zig_from(type_name: str) -> str:
    return "leetFrom_" + type_name.replace("[", "_").replace("]", "")


def zig_to(type_name: str) -> str:
    return "leetTo_" + type_name.replace("[", "_").replace("]", "")


def needs_alloc(type_name: str) -> bool:
    return inner_list(type_name) is not None


def call_from(type_name: str, expr: str) -> str:
    fn = zig_from(type_name)
    if needs_alloc(type_name):
        return f"try {fn}(alloc, {expr})"
    return f"try {fn}({expr})"


def call_to(type_name: str, expr: str) -> str:
    fn = zig_to(type_name)
    if needs_alloc(type_name):
        return f"try {fn}(alloc, {expr})"
    return f"{fn}({expr})"


def emit_zig_converters(types: list[str], flavor: str = "14") -> str:
    seen: set[str] = set()
    chunks: list[str] = []

    def emit(type_name: str) -> None:
        if type_name in seen:
            return
        inner = inner_list(type_name)
        if inner is not None:
            emit(inner)
        seen.add(type_name)
        fn = zig_from(type_name)
        toj = zig_to(type_name)
        if type_name == "int":
            chunks.append(
                "fn leetFrom_int(v: std.json.Value) !i32 {\n"
                "    return switch (v) {\n"
                "        .integer => |n| @intCast(n),\n"
                "        .float => |n| @intFromFloat(n),\n"
                "        else => error.BadJson,\n"
                "    };\n"
                "}\n"
                "fn leetTo_int(v: i32) std.json.Value {\n"
                "    return .{ .integer = @as(i64, v) };\n"
                "}"
            )
        elif type_name == "long":
            chunks.append(
                "fn leetFrom_long(v: std.json.Value) !i64 {\n"
                "    return switch (v) {\n"
                "        .integer => |n| n,\n"
                "        .float => |n| @intFromFloat(n),\n"
                "        else => error.BadJson,\n"
                "    };\n"
                "}\n"
                "fn leetTo_long(v: i64) std.json.Value {\n"
                "    return .{ .integer = v };\n"
                "}"
            )
        elif type_name == "float":
            chunks.append(
                "fn leetFrom_float(v: std.json.Value) !f64 {\n"
                "    return switch (v) {\n"
                "        .integer => |n| @floatFromInt(n),\n"
                "        .float => |n| n,\n"
                "        else => error.BadJson,\n"
                "    };\n"
                "}\n"
                "fn leetTo_float(v: f64) std.json.Value {\n"
                "    return .{ .float = v };\n"
                "}"
            )
        elif type_name == "bool":
            chunks.append(
                "fn leetFrom_bool(v: std.json.Value) !bool {\n"
                "    return switch (v) {\n"
                "        .bool => |b| b,\n"
                "        else => error.BadJson,\n"
                "    };\n"
                "}\n"
                "fn leetTo_bool(v: bool) std.json.Value {\n"
                "    return .{ .bool = v };\n"
                "}"
            )
        elif type_name == "str":
            chunks.append(
                "fn leetFrom_str(v: std.json.Value) ![]const u8 {\n"
                "    return switch (v) {\n"
                "        .string => |s| s,\n"
                "        else => error.BadJson,\n"
                "    };\n"
                "}\n"
                "fn leetTo_str(v: []const u8) std.json.Value {\n"
                "    return .{ .string = v };\n"
                "}"
            )
        else:
            assert inner is not None
            zt = zig_type(type_name, ret=True)
            inner_zt = zig_type(inner, ret=True)
            inner_from = call_from(inner, "item")
            inner_to = call_to(inner, "item")
            if flavor == "16":
                arr_init = "    var arr = std.json.Array.init(alloc);"
                arr_append = f"        try arr.append({inner_to});"
            else:
                arr_init = "    var arr = std.ArrayList(std.json.Value).init(alloc);"
                arr_append = f"        try arr.append({inner_to});"
            chunks.append(
                f"fn {fn}(alloc: std.mem.Allocator, v: std.json.Value) !{zt} {{\n"
                f"    const arr = switch (v) {{\n"
                f"        .array => |a| a,\n"
                f"        else => return error.BadJson,\n"
                f"    }};\n"
                f"    const out = try alloc.alloc({inner_zt}, arr.items.len);\n"
                f"    for (arr.items, 0..) |item, i| {{\n"
                f"        out[i] = {inner_from};\n"
                f"    }}\n"
                f"    return out;\n"
                f"}}\n"
                f"fn {toj}(alloc: std.mem.Allocator, v: {zt}) !std.json.Value {{\n"
                f"{arr_init}\n"
                f"    for (v) |item| {{\n"
                f"{arr_append}\n"
                f"    }}\n"
                f"    return .{{ .array = arr }};\n"
                f"}}"
            )

    for t in types:
        emit(t)
    return "\n\n".join(chunks)


def zig_runtime_bits(flavor: str) -> dict[str, str]:
    if flavor == "16":
        return {
            "alloc": "    const alloc = std.heap.smp_allocator;",
            "dump_new": "    var out: std.ArrayList(u8) = .empty;",
            "dump_push": "    try out.appendSlice(alloc, s);",
            "dump_owned": "    return out.toOwnedSlice(alloc);",
            "line_new": "    var line: std.ArrayList(u8) = .empty;",
            "read_n": (
                "blk: {\n"
                "            while (true) {\n"
                "                const n = std.posix.read(std.posix.STDIN_FILENO, &tmp) catch |err| switch (err) {\n"
                "                    error.WouldBlock => continue,\n"
                "                    else => return err,\n"
                "                };\n"
                "                break :blk n;\n"
                "            }\n"
                "        }"
            ),
            "line_append": "            try line.appendSlice(alloc, tmp[0..n]);",
            "stdout": (
                "    var off: usize = 0;\n"
                "    while (off < s.len) {\n"
                "        const rc = std.os.linux.write(1, s[off..].ptr, s.len - off);\n"
                "        const signed: isize = @bitCast(rc);\n"
                "        if (signed < 0 or rc == 0) return error.WriteFailed;\n"
                "        off += rc;\n"
                "    }\n"
                "    off = 0;\n"
                '    const nl = "\\n";\n'
                "    while (off < nl.len) {\n"
                "        const rc = std.os.linux.write(1, nl[off..].ptr, nl.len - off);\n"
                "        const signed: isize = @bitCast(rc);\n"
                "        if (signed < 0 or rc == 0) return error.WriteFailed;\n"
                "        off += rc;\n"
                "    }"
            ),
        }
    if flavor == "15":
        return {
            "alloc": (
                "    var gpa = std.heap.GeneralPurposeAllocator(.{}){};\n"
                "    defer _ = gpa.deinit();\n"
                "    const alloc = gpa.allocator();"
            ),
            "dump_new": "    var out = std.ArrayList(u8).init(alloc);",
            "dump_push": "    try out.appendSlice(s);",
            "dump_owned": "    return out.toOwnedSlice();",
            "line_new": "    var line = std.ArrayList(u8).init(alloc);",
            "read_n": "try std.fs.File.stdin().read(&tmp)",
            "line_append": "            try line.appendSlice(tmp[0..n]);",
            "stdout": (
                "    try std.fs.File.stdout().writeAll(s);\n"
                '    try std.fs.File.stdout().writeAll("\\n");'
            ),
        }
    return {
        "alloc": (
            "    var gpa = std.heap.GeneralPurposeAllocator(.{}){};\n"
            "    defer _ = gpa.deinit();\n"
            "    const alloc = gpa.allocator();"
        ),
        "dump_new": "    var out = std.ArrayList(u8).init(alloc);",
        "dump_push": "    try out.appendSlice(s);",
        "dump_owned": "    return out.toOwnedSlice();",
        "line_new": "    var line = std.ArrayList(u8).init(alloc);",
        "read_n": "try std.io.getStdIn().reader().read(&tmp)",
        "line_append": "            try line.appendSlice(tmp[0..n]);",
        "stdout": '    try std.io.getStdOut().writer().print("{s}\\n", .{s});',
    }


def zig_helpers(flavor: str) -> str:
    b = zig_runtime_bits(flavor)
    return f'''
pub fn leetClose(a: std.json.Value, b: std.json.Value) bool {{
    return switch (a) {{
        .null => b == .null,
        .bool => |x| switch (b) {{ .bool => |y| x == y, else => false }},
        .integer => |x| switch (b) {{
            .integer => |y| x == y,
            .float => |y| blk: {{
                const xf: f64 = @floatFromInt(x);
                const d = @abs(xf - y);
                break :blk d <= 1e-6 or d <= 1e-6 * @max(@abs(xf), @abs(y));
            }},
            else => false,
        }},
        .float => |x| switch (b) {{
            .integer => |y| blk: {{
                const yf: f64 = @floatFromInt(y);
                const d = @abs(x - yf);
                break :blk d <= 1e-6 or d <= 1e-6 * @max(@abs(x), @abs(yf));
            }},
            .float => |y| blk: {{
                const d = @abs(x - y);
                break :blk d <= 1e-6 or d <= 1e-6 * @max(@abs(x), @abs(y));
            }},
            else => false,
        }},
        .string => |x| switch (b) {{ .string => |y| std.mem.eql(u8, x, y), else => false }},
        .array => |x| switch (b) {{
            .array => |y| blk: {{
                if (x.items.len != y.items.len) break :blk false;
                for (x.items, y.items) |p, q| {{
                    if (!leetClose(p, q)) break :blk false;
                }}
                break :blk true;
            }},
            else => false,
        }},
        else => false,
    }};
}}

pub fn leetPush(alloc: std.mem.Allocator, out: *std.ArrayList(u8), s: []const u8) !void {{
{"" if flavor == "16" else "    _ = alloc;"}
    {"try out.appendSlice(alloc, s);" if flavor == "16" else "try out.appendSlice(s);"}
}}

pub fn leetDump(alloc: std.mem.Allocator, v: std.json.Value) ![]u8 {{
{b["dump_new"]}
    try leetDumpInto(alloc, &out, v);
{b["dump_owned"]}
}}

pub fn leetDumpInto(alloc: std.mem.Allocator, out: *std.ArrayList(u8), v: std.json.Value) !void {{
    switch (v) {{
        .null => try leetPush(alloc, out, "null"),
        .bool => |flag| try leetPush(alloc, out, if (flag) "true" else "false"),
        .integer => |n| {{
            var buf: [32]u8 = undefined;
            const s = std.fmt.bufPrint(&buf, "{{d}}", .{{n}}) catch unreachable;
            try leetPush(alloc, out, s);
        }},
        .float => |n| {{
            var buf: [64]u8 = undefined;
            const s = std.fmt.bufPrint(&buf, "{{d}}", .{{n}}) catch unreachable;
            try leetPush(alloc, out, s);
        }},
        .number_string => |s| try leetPush(alloc, out, s),
        .string => |s| {{
            try leetPush(alloc, out, "\\"");
            try leetPush(alloc, out, s);
            try leetPush(alloc, out, "\\"");
        }},
        .array => |a| {{
            try leetPush(alloc, out, "[");
            for (a.items, 0..) |item, i| {{
                if (i != 0) try leetPush(alloc, out, ",");
                try leetDumpInto(alloc, out, item);
            }}
            try leetPush(alloc, out, "]");
        }},
        .object => |o| {{
            try leetPush(alloc, out, "{{");
            var first = true;
            var it = o.iterator();
            while (it.next()) |kv| {{
                if (!first) try leetPush(alloc, out, ",");
                first = false;
                try leetPush(alloc, out, "\\"");
                try leetPush(alloc, out, kv.key_ptr.*);
                try leetPush(alloc, out, "\\":");
                try leetDumpInto(alloc, out, kv.value_ptr.*);
            }}
            try leetPush(alloc, out, "}}");
        }},
    }}
}}

pub fn leetEq(alloc: std.mem.Allocator, got: std.json.Value, expected: std.json.Value, any_order: bool) !bool {{
    if (any_order) {{
        switch (got) {{
            .array => |g| switch (expected) {{
                .array => |e| {{
                    if (g.items.len != e.items.len) return false;
                    const gs = try alloc.alloc([]u8, g.items.len);
                    const es = try alloc.alloc([]u8, e.items.len);
                    for (g.items, 0..) |item, i| gs[i] = try leetDump(alloc, item);
                    for (e.items, 0..) |item, i| es[i] = try leetDump(alloc, item);
                    const less = struct {{
                        fn f(_: void, a: []u8, b: []u8) bool {{
                            return std.mem.lessThan(u8, a, b);
                        }}
                    }}.f;
                    std.mem.sort([]u8, gs, {{}}, less);
                    std.mem.sort([]u8, es, {{}}, less);
                    for (gs, es) |a, b| {{
                        if (!std.mem.eql(u8, a, b)) return false;
                    }}
                    return true;
                }},
                else => {{}},
            }},
            else => {{}},
        }}
    }}
    return leetClose(got, expected);
}}

pub fn leetWrite(alloc: std.mem.Allocator, v: std.json.Value) !void {{
    const s = try leetDump(alloc, v);
{b["stdout"]}
}}
'''


def zig_harness_source(flavor: str) -> str:
    b = zig_runtime_bits(flavor)
    if flavor == "16":
        obj_new = "var o: std.json.ObjectMap = .empty;"

        def put(key: str, expr: str) -> str:
            return f'try o.put(alloc, "{key}", {expr});'
    else:
        obj_new = "var o = std.json.ObjectMap.init(alloc);"

        def put(key: str, expr: str) -> str:
            return f'try o.put("{key}", {expr});'

    str_re = put("verdict", '.{ .string = "RE" }')
    str_wa = put("verdict", '.{ .string = "WA" }')
    str_ac = put("verdict", '.{ .string = "AC" }')
    msg_parse = put("message", '.{ .string = "json parse" }')
    msg_runtime = put("message", '.{ .string = "runtime" }')
    put_failed = put("failed_index", ".{ .integer = @intCast(index) }")
    put_got = put("got", "gotj")
    put_passed_i = put("passed", ".{ .integer = @intCast(index) }")
    put_passed_t = put("passed", ".{ .integer = @intCast(index) }")
    put_total = put("total", ".{ .integer = @intCast(index) }")
    return f'''const std = @import("std");
{zig_helpers(flavor)}

pub const SolveFn = *const fn (std.mem.Allocator, std.json.Value) anyerror!std.json.Value;

pub fn leetParse(alloc: std.mem.Allocator, line: []const u8) !std.json.Parsed(std.json.Value) {{
    return std.json.parseFromSlice(std.json.Value, alloc, line, .{{}});
}}

fn leetOneLine(alloc: std.mem.Allocator, solve: SolveFn, any_order: bool, index: usize, text: []const u8) !bool {{
    var parsed = leetParse(alloc, text) catch {{
        {obj_new}
        {str_re}
        {msg_parse}
        try leetWrite(alloc, .{{ .object = o }});
        return false;
    }};
    defer parsed.deinit();
    const obj = parsed.value.object;
    const args_v = obj.get("args") orelse return error.MissingArgs;
    const expected = obj.get("expected") orelse return error.MissingExpected;
    const gotj = solve(alloc, args_v) catch {{
        {obj_new}
        {str_re}
        {put_failed}
        {msg_runtime}
        {put_passed_i}
        {put_total}
        try leetWrite(alloc, .{{ .object = o }});
        return false;
    }};
    if (!try leetEq(alloc, gotj, expected, any_order)) {{
        {obj_new}
        {str_wa}
        {put_failed}
        {put_got}
        {put_passed_i}
        {put_total}
        try leetWrite(alloc, .{{ .object = o }});
        return false;
    }}
    return true;
}}

pub fn run(alloc: std.mem.Allocator, solve: SolveFn, any_order: bool) !void {{
{b["line_new"]}
    var tmp: [8192]u8 = undefined;
    var index: usize = 0;
    var eof = false;
    while (!eof) {{
        const n = {b["read_n"]};
        if (n == 0) {{
            eof = true;
        }} else {{
{b["line_append"]}
        }}
        while (true) {{
            if (std.mem.indexOfScalar(u8, line.items, '\\n')) |nl| {{
                const text = std.mem.trim(u8, line.items[0..nl], " \\r");
                if (text.len != 0) {{
                    if (!try leetOneLine(alloc, solve, any_order, index, text)) return;
                    index += 1;
                }}
                const rest_len = line.items.len - nl - 1;
                std.mem.copyForwards(u8, line.items[0..rest_len], line.items[nl + 1 ..]);
                line.shrinkRetainingCapacity(rest_len);
            }} else if (eof) {{
                const text = std.mem.trim(u8, line.items, " \\r");
                if (text.len != 0) {{
                    if (!try leetOneLine(alloc, solve, any_order, index, text)) return;
                    index += 1;
                }}
                break;
            }} else {{
                break;
            }}
        }}
    }}
    {obj_new}
    {str_ac}
    {put_passed_t}
    {put_total}
    try leetWrite(alloc, .{{ .object = o }});
}}
'''


def zig_harness_path(flavor: str) -> Path:
    folder = DATA_DIR / "zig-harness"
    folder.mkdir(parents=True, exist_ok=True)
    return folder / f"leet_harness_{flavor}.zig"


def write_zig_harness(flavor: str) -> Path:
    path = zig_harness_path(flavor)
    text = zig_harness_source(flavor)
    if not path.is_file() or path.read_text(encoding="utf-8") != text:
        path.write_text(text, encoding="utf-8")
    return path


def zig_posix_path(path: Path) -> str:
    return path.resolve().as_posix()


def wrap_zig(user_code: str, signature: dict, flavor: str = "14") -> str:
    method = signature["method"]
    class_name = signature.get("class_name") or "Solution"
    compare = signature.get("compare") or "exact"
    params = signature.get("params") or []
    return_type = signature["return_type"]
    types = [p["type"] for p in params] + [return_type]
    converters = emit_zig_converters(types, flavor)
    bits = zig_runtime_bits(flavor)
    bind_lines = []
    call_args = []
    for i, p in enumerate(params):
        bind_lines.append(
            f"    const arg{i} = {call_from(p['type'], f'args.items[{i}]')};"
        )
        call_args.append(f"arg{i}")
    bind = "\n".join(bind_lines)
    call = ", ".join(call_args)
    any_order = "true" if compare == "any_order" else "false"
    to_got = call_to(return_type, "got")
    uses_alloc = any(needs_alloc(t) for t in types)
    discard_alloc = "    _ = alloc;\n" if not uses_alloc else ""
    body = user_code.rstrip()
    if '@import("std")' not in body and "@import(\"std\")" not in body:
        body = 'const std = @import("std");\n\n' + body
    return f'''{body}

const leet = @import("leet");

{converters}

fn leetSolve(alloc: std.mem.Allocator, args_v: std.json.Value) anyerror!std.json.Value {{
{discard_alloc}    const args = switch (args_v) {{
        .array => |a| a,
        else => return error.BadArgs,
    }};
{bind}
    const sol = {class_name}{{}};
    const got = sol.{method}({call});
    return {to_got};
}}

pub fn main() !void {{
{bits["alloc"]}
    try leet.run(alloc, leetSolve, {any_order});
}}
'''


class ZigAdapter(LanguageAdapter):
    id = "zig"
    display_name = "Zig"
    source_filename = "solution.zig"
    implemented = True

    def zig_bin(self) -> str | None:
        return find_tool("zig", linux_paths=("/usr/bin/zig", "/usr/local/bin/zig"))

    def detect(self) -> bool:
        return self.zig_bin() is not None

    def runtime_version(self) -> str | None:
        path = self.zig_bin()
        return fmt_version(zig_version(path)) if path else None

    def wrap(self, user_code: str, signature: dict) -> str:
        path = self.zig_bin()
        flavor = zig_flavor(zig_version(path) if path else None)
        return wrap_zig(user_code, signature, flavor)

    def compile(self, workdir: str) -> CompileResult:
        compiler = self.zig_bin()
        if not compiler:
            return CompileResult(ok=False, log="zig not found")
        out = "program.exe" if os.name == "nt" else "program"
        cache = Path(workdir) / ".zig-cache"
        (cache / "global").mkdir(parents=True, exist_ok=True)
        (cache / "local").mkdir(parents=True, exist_ok=True)
        flavor = zig_flavor(zig_version(compiler))
        harness = write_zig_harness(flavor)
        argv = [
            compiler,
            "build-exe",
            f"-femit-bin={out}",
            "--dep",
            "leet",
            "-O",
            ZIG_OPT,
            f"-Mroot={self.source_filename}",
            "-O",
            ZIG_OPT,
            f"-Mleet={zig_posix_path(harness)}",
        ]
        result = run_limited(
            argv,
            cwd=Path(workdir),
            stdin="",
            time_ms=ZIG_COMPILE_MS,
            memory_mb=4096,
            for_compile=True,
            extra_env={
                "ZIG_GLOBAL_CACHE_DIR": str(cache / "global"),
                "ZIG_LOCAL_CACHE_DIR": str(cache / "local"),
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
