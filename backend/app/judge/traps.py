"""Hidden-test weapons and which one killed a wrong submission.

Never puts args / expected / got into the payload.
"""
from __future__ import annotations

from typing import Any

# case_n / size_band imported lazily inside arsenal() to avoid a cycle with hints.

GRAPH_TAGS = {
    "graph",
    "bfs",
    "dfs",
    "shortest-path",
    "dijkstra",
    "0-1-bfs",
    "floyd",
    "topological-sort",
    "union-find",
    "mst",
    "scc",
    "max-flow",
    "bipartite-matching",
    "eulerian",
    "functional-graph",
    "two-sat",
    "tree",
    "diameter",
    "lca",
    "binary-lifting",
}
GRID_TAGS = {"grid", "matrix", "flood-fill"}
WINDOW_TAGS = {"sliding-window", "two-pointers"}
BINARY_TAGS = {"binary-search", "binary-search-answer", "ternary-search"}
DP_TAGS = {"dp", "knapsack", "memoization", "digit-dp", "interval-dp", "tree-dp"}

CATALOG: dict[str, dict[str, str]] = {
    "public": {
        "title": "公开示例",
        "blurb": "题面输入还没过。隐藏火力还没轮到。",
    },
    "boundary": {
        "title": "边界形态",
        "blurb": "很小的隐藏测例：最小规模、端点下标、全同或逆序一类。",
    },
    "scale": {
        "title": "顶满规模",
        "blurb": "数组长度、字符串长度或点数刚好等于上限。漏掉满规模或差一档复杂度会挂在这里。",
    },
    "mid": {
        "title": "中段规模",
        "blurb": "不是最小也不是上限，常打漏掉的一种形态或常数。",
    },
    "values": {
        "title": "约束端点",
        "blurb": "元素或单独给出的数打到约束最小 / 最大。",
    },
    "graph": {
        "title": "图结构",
        "blurb": "链、星、晚连通、点号两端。打爆栈 find、把边数当点数。",
    },
    "grid": {
        "title": "网格形态",
        "blurb": "单行单列、墙与空、贴边走。打八连通、漏 1×n。",
    },
    "window": {
        "title": "窗口 / 双指针",
        "blurb": "窗口长 1 与整段、贴左贴右。打 r-l+1 写错。",
    },
    "binary": {
        "title": "二分边界",
        "blurb": "答案贴下界 / 上界，刚好可行与再紧一档。",
    },
    "dp": {
        "title": "DP 退化",
        "blurb": "k=1、不能选、必须选满。打滚错维、初始化反了。",
    },
    "complexity": {
        "title": "复杂度",
        "blurb": "整次超时。隐藏里通常有 1～2 条规模刚好等于上限。",
    },
    "memory": {
        "title": "内存",
        "blurb": "整次超内存。按上限开了过大的表。",
    },
}


def _walk_ints(obj: Any):
    if isinstance(obj, bool):
        return
    if isinstance(obj, int):
        yield obj
        return
    if isinstance(obj, list):
        for x in obj:
            yield from _walk_ints(x)


def _looks_edges(args: list) -> bool:
    for x in args:
        if not isinstance(x, list) or not x:
            continue
        if isinstance(x[0], list) and x[0] and isinstance(x[0][0], int) and not isinstance(x[0][0], bool):
            row = x[0]
            if 2 <= len(row) <= 3:
                return True
    return False


def _looks_grid(args: list) -> bool:
    for x in args:
        if isinstance(x, list) and x and isinstance(x[0], str):
            return True
        if isinstance(x, list) and x and isinstance(x[0], list):
            row = x[0]
            if row and all(v in (0, 1, 2) for v in row if isinstance(v, int)):
                return True
    return False


def _meta_bounds(problem) -> tuple[int | None, int | None]:
    lo = getattr(problem, "elem_min", None)
    hi = getattr(problem, "elem_max", None)
    return (int(lo) if lo is not None else None, int(hi) if hi is not None else None)


def _slot(wid: str, *, loaded: bool, family: str) -> dict[str, Any]:
    spec = CATALOG[wid]
    return {
        "id": wid,
        "title": spec["title"],
        "blurb": spec["blurb"],
        "loaded": loaded,
        "family": family,
        "verified": False,
    }


def arsenal(problem) -> list[dict[str, Any]]:
    """Weapons from meta/tags, or from an explicit tests list. Does not open tests.jsonl."""
    cache = getattr(problem, "_arsenal_cache", None)
    if cache is not None:
        return cache
    from .hints import case_n, size_band
    tags = set(getattr(problem, "tags", None) or [])
    n_max = getattr(problem, "n_max", None)
    tests = getattr(problem, "tests", None)
    lo, hi = _meta_bounds(problem)
    tiny = at_max = mid = values = edges = grid = False
    sig = getattr(problem, "signature", None)
    params = getattr(sig, "params", None) if sig is not None else None
    if tests is not None:
        for test in tests:
            if not getattr(test, "hidden", False):
                continue
            args = getattr(test, "args", None) or []
            n = case_n(args, params)
            band = size_band(n, n_max)
            if band == "lt100":
                tiny = True
            elif band == "at_max":
                at_max = True
            elif band in {"mid", "large"}:
                mid = True
            if lo is not None or hi is not None:
                for v in _walk_ints(args):
                    if lo is not None and v == lo:
                        values = True
                    if hi is not None and v == hi:
                        values = True
            if _looks_edges(args):
                edges = True
            if _looks_grid(args):
                grid = True
    elif n_max is not None and n_max >= 5000:
        at_max = True
    if lo is not None or hi is not None:
        values = True
    slots = [
        _slot("boundary", loaded=tiny, family="scale"),
        _slot("scale", loaded=at_max, family="scale"),
        _slot("values", loaded=values, family="scale"),
        _slot("graph", loaded=edges or bool(tags & GRAPH_TAGS), family="shape"),
        _slot("grid", loaded=grid or bool(tags & GRID_TAGS), family="shape"),
        _slot("complexity", loaded=bool(n_max and n_max >= 5000) or at_max, family="scale"),
    ]
    extras = []
    if tags & WINDOW_TAGS:
        extras.append(_slot("window", loaded=True, family="tag"))
    if tags & BINARY_TAGS:
        extras.append(_slot("binary", loaded=True, family="tag"))
    if tags & DP_TAGS:
        extras.append(_slot("dp", loaded=True, family="tag"))
    if mid and not at_max:
        extras.append(_slot("mid", loaded=True, family="scale"))
    out = slots + extras
    try:
        problem._arsenal_cache = out
    except Exception:
        pass
    return out


def weapon_for(
    verdict: str,
    *,
    hidden: bool,
    band: str,
) -> str:
    if verdict == "TLE":
        return "complexity"
    if verdict == "MLE":
        return "memory"
    if not hidden:
        return "public"
    if band == "at_max":
        return "scale"
    if band == "lt100":
        return "boundary"
    if band in {"mid", "large"}:
        return "mid"
    return "boundary"


def attach_kill(
    details: dict[str, Any],
    verdict: str,
    *,
    hidden: bool = False,
    band: str = "unknown",
    index: int | None = None,
    n: int | None = None,
) -> dict[str, Any]:
    if verdict == "AC":
        details["kill"] = {
            "cleared": True,
            "weapon": None,
            "title": "穿过火力网",
            "blurb": "隐藏测例没有打中这份解。",
            "hidden": False,
            "index": None,
            "n": None,
        }
        return details
    wid = weapon_for(verdict, hidden=hidden, band=band)
    spec = CATALOG.get(wid, CATALOG["boundary"])
    kill: dict[str, Any] = {
        "cleared": False,
        "weapon": wid,
        "title": spec["title"],
        "blurb": spec["blurb"],
        "hidden": hidden,
        "index": index,
        "n": n if hidden else None,
    }
    details["kill"] = kill
    return details
