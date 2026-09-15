"""Load docs/types.yaml (which languages can wrap each signature type)."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

_LEAF_LIST_MEANING = {
    "int": ("整数数组", "二维整数数组（包括矩阵、格子、边的列表）"),
    "long": ("64位整数数组", "二维64位整数数组（包括矩阵、格子、边的列表）"),
    "float": ("小数数组", "二维小数数组"),
    "bool": ("bool数组", "二维bool数组"),
    "str": ("字符串数组", "二维字符串数组"),
}

_TYPES_FILE = Path("docs") / "types.yaml"


def _find_root(start: Path | None = None) -> Path:
    starts = []
    if start is not None:
        starts.append(Path(start).resolve())
    starts.append(Path(__file__).resolve().parent)
    seen: set[Path] = set()
    for cur in starts:
        for p in [cur, *cur.parents]:
            if p in seen:
                continue
            seen.add(p)
            if (p / _TYPES_FILE).is_file():
                return p
    raise FileNotFoundError("docs/types.yaml")


@lru_cache(maxsize=1)
def load_catalog(root: Path | None = None) -> dict:
    path = _find_root(root) / _TYPES_FILE
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return data


def languages(root: Path | None = None) -> list[str]:
    return list(load_catalog(root).get("languages") or [])


def max_list_depth(root: Path | None = None) -> int:
    return int(load_catalog(root).get("max_list_depth") or 2)


def leaves(root: Path | None = None) -> dict:
    return dict(load_catalog(root).get("leaves") or {})


def list_depth_leaf(type_name: str) -> tuple[int, str]:
    depth = 0
    t = (type_name or "").strip()
    while t.startswith("List[") and t.endswith("]"):
        depth += 1
        t = t[5:-1].strip()
    return depth, t


def is_allowed_type(type_name: str, root: Path | None = None) -> bool:
    depth, leaf = list_depth_leaf(type_name)
    if depth > max_list_depth(root):
        return False
    return leaf in leaves(root)


def leaf_spec(leaf: str, root: Path | None = None) -> dict:
    return dict(leaves(root).get(leaf) or {})


def bounds_kind(type_name: str, root: Path | None = None) -> str:
    _, leaf = list_depth_leaf(type_name)
    spec = leaf_spec(leaf, root)
    return str(spec.get("bounds_shape") or spec.get("bounds") or "none")


def leaf_scale(leaf: str, root: Path | None = None) -> str:
    return str(leaf_spec(leaf, root).get("scale") or "none")


def scale_from_signature(params: list[tuple[str, str]], root: Path | None = None) -> tuple[str, int] | None:
    """Scale slot from leaf.scale in types.yaml plus argument order.

    ("value", i): depth-0 leaf with scale=value before a depth-2 list whose leaf also has scale=value.
    ("length", i): first List[*] (any leaf) or depth-0 leaf with scale=length.
    None: no scale slot.
    """
    edge_i: int | None = None
    for i, (_, typ) in enumerate(params):
        depth, leaf = list_depth_leaf(typ)
        if depth == 2 and leaf_scale(leaf, root) == "value":
            edge_i = i
            break
    if edge_i is not None:
        for i, (_, typ) in enumerate(params):
            if i >= edge_i:
                break
            depth, leaf = list_depth_leaf(typ)
            if depth == 0 and leaf_scale(leaf, root) == "value":
                return ("value", i)
    for i, (_, typ) in enumerate(params):
        depth, leaf = list_depth_leaf(typ)
        if depth >= 1:
            return ("length", i)
        if depth == 0 and leaf_scale(leaf, root) == "length":
            return ("length", i)
    return None


def wrap_languages(type_name: str, root: Path | None = None) -> list[str]:
    if not is_allowed_type(type_name, root):
        return []
    _, leaf = list_depth_leaf(type_name)
    spec = leaf_spec(leaf, root)
    langs = spec.get("langs") or "all"
    all_langs = languages(root)
    if langs == "all":
        return list(all_langs)
    return [x for x in all_langs if x in langs]


def languages_for_signature(
    type_names: list[str],
    allowlist: list[str] | None = None,
    root: Path | None = None,
) -> list[str]:
    out = list(languages(root))
    if allowlist:
        allowed = set(allowlist)
        out = [x for x in out if x in allowed]
    for t in type_names:
        wrap = set(wrap_languages(t, root))
        out = [x for x in out if x in wrap]
    return out


def meta_language_allowlist(root: Path, slug: str) -> list[str] | None:
    path = Path(root) / "problems" / slug / "meta.yaml"
    if not path.is_file():
        return None
    meta = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    raw = meta.get("languages") if isinstance(meta, dict) else None
    if not raw:
        return None
    return [str(x) for x in raw]


def languages_for_problem(root: Path, slug: str, type_names: list[str]) -> list[str]:
    return languages_for_signature(type_names, meta_language_allowlist(root, slug))


def c_maps(root: Path | None = None) -> tuple[dict[str, str], dict[str, tuple], dict[str, tuple]]:
    scalar: dict[str, str] = {}
    one: dict[str, tuple] = {}
    two: dict[str, tuple] = {}
    for leaf, spec in leaves(root).items():
        c = spec.get("c") or {}
        if "scalar" in c:
            scalar[leaf] = c["scalar"]
        if "ptr1" in c and "as1" in c and "from1" in c:
            one[leaf] = (c["ptr1"], c["as1"], c["from1"])
        if "ptr2" in c and "as2" in c and "from2" in c:
            two[leaf] = (c["ptr2"], c["as2"], c["from2"])
    return scalar, one, two


def type_meaning(type_name: str, root: Path | None = None) -> str:
    depth, leaf = list_depth_leaf(type_name)
    spec = leaf_spec(leaf, root)
    if depth == 0:
        return str(spec.get("meaning") or leaf)
    pair = _LEAF_LIST_MEANING.get(leaf, (leaf + " 数组", leaf + " 表"))
    return pair[0] if depth == 1 else pair[1]


def allowed_type_names(root: Path | None = None) -> list[str]:
    ordered = list(load_catalog(root).get("type_order") or [])
    if ordered:
        return [t for t in ordered if is_allowed_type(t, root)]
    out: list[str] = []
    for leaf in leaves(root):
        out.append(leaf)
        out.append(f"List[{leaf}]")
        out.append(f"List[List[{leaf}]]")
    return out
