"""Fail hints for judge details. Never include hidden args/expected/got."""
from __future__ import annotations

from typing import Any

from .traps import attach_kill
from .typespec import scale_from_signature


def _param_pairs(params) -> list[tuple[str, str]]:
    if not params:
        return []
    out: list[tuple[str, str]] = []
    for p in params:
        if isinstance(p, (tuple, list)) and len(p) >= 2:
            out.append((str(p[0]), str(p[1])))
        else:
            out.append((str(getattr(p, "name", "")), str(getattr(p, "type", ""))))
    return out


def case_n(args: list, params=None) -> int | None:
    if not isinstance(args, (list, tuple)) or not args:
        return None
    pairs = _param_pairs(params)
    if pairs:
        scale = scale_from_signature(pairs)
        if scale is None:
            return None
        kind, i = scale
        if i >= len(args):
            return None
        val = args[i]
        if kind == "value":
            if isinstance(val, int) and not isinstance(val, bool):
                return int(val)
            return None
        if isinstance(val, (list, str)):
            return len(val)
        return None
    return None


def size_band(n: int | None, n_max: int | None) -> str:
    if n is None:
        return "unknown"
    if n_max is not None and n == n_max:
        return "at_max"
    if n < 100:
        return "lt100"
    if n <= 5000:
        return "mid"
    return "large"


def _text(verdict: str, *, hidden: bool, band: str, n: int | None) -> str:
    if verdict in {"TLE", "MLE"}:
        if verdict == "TLE":
            return "整次运行超时。隐藏测例里通常有 1～2 条顶满规模，劣一档复杂度往往会挂在这里。"
        return "整次运行超内存。检查是否按规模上限开了过大的表。"
    if not hidden:
        return "公开示例未过，对照题面输入。"
    if band == "at_max":
        return "挂在上限附近的隐藏测例，像是复杂度或没处理满规模。"
    if band == "lt100":
        return "挂在很小的隐藏测例上，先查边界和特殊形态。"
    if n is not None:
        return f"挂在规模约 {n} 的隐藏测例上。"
    return "挂在一条隐藏测例上（不展示输入）。"


def attach_hint(
    details: dict[str, Any],
    tests: list,
    verdict: str,
    n_max: int | None,
    *,
    public_only: bool = False,
    params=None,
) -> dict[str, Any]:
    if verdict == "AC":
        return attach_kill(details, "AC")
    idx = details.get("failed_index")
    if verdict in {"TLE", "MLE"}:
        details["hint"] = {
            "kind": verdict.lower(),
            "hidden": True,
            "band": "at_max" if n_max else "unknown",
            "at_max": bool(n_max),
            "text": _text(verdict, hidden=True, band="at_max", n=n_max),
        }
        return attach_kill(
            details,
            verdict,
            hidden=True,
            band="at_max",
            n=n_max,
        )
    if idx is None or not isinstance(idx, int) or idx < 0 or idx >= len(tests):
        return attach_kill(details, verdict, hidden=not public_only)
    test = tests[idx]
    hidden = bool(getattr(test, "hidden", False)) and not public_only
    n = case_n(getattr(test, "args", None) or [], params)
    band = size_band(n, n_max)
    hint: dict[str, Any] = {
        "kind": verdict.lower(),
        "index": idx,
        "hidden": hidden,
        "band": band,
        "at_max": band == "at_max",
        "text": _text(verdict, hidden=hidden, band=band, n=n),
    }
    if hidden and n is not None:
        hint["n"] = n
    details["hint"] = hint
    return attach_kill(details, verdict, hidden=hidden, band=band, index=idx, n=n if hidden else None)
