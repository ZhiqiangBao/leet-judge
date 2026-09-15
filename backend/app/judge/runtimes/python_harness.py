from __future__ import annotations

import json
from typing import Any

HARNESS = r'''
# --- local-leet harness (do not edit) ---
import json
import math
import sys
import traceback

METHOD = {method!r}
CLASS_NAME = {class_name!r}
COMPARE = {compare!r}


def _canon(value):
    if isinstance(value, tuple):
        value = list(value)
    if isinstance(value, list):
        return [_canon(x) for x in value]
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return value
    if isinstance(value, str):
        return value
    raise TypeError(f"unsupported return type: {{type(value).__name__}}")


def _close(a, b):
    if isinstance(a, bool) or isinstance(b, bool):
        return a is b if isinstance(a, bool) and isinstance(b, bool) else False
    if isinstance(a, int) and isinstance(b, int):
        return a == b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return math.isclose(float(a), float(b), rel_tol=1e-6, abs_tol=1e-6)
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            return False
        return all(_close(x, y) for x, y in zip(a, b))
    return a == b


def _sort_key(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False)


def _eq(got, expected, mode):
    if mode == "any_order" and isinstance(got, list) and isinstance(expected, list):
        if len(got) != len(expected):
            return False
        return sorted(got, key=_sort_key) == sorted(expected, key=_sort_key) or (
            all(_close(a, b) for a, b in zip(sorted(got, key=_sort_key), sorted(expected, key=_sort_key)))
        )
    return _close(got, expected)


def _emit(payload):
    sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def main():
    if CLASS_NAME not in globals():
        _emit({{"verdict": "RE", "message": f"missing class {{CLASS_NAME}}"}})
        return
    cls = globals()[CLASS_NAME]
    try:
        inst = cls()
    except Exception as exc:
        _emit({{"verdict": "RE", "message": f"construct {{CLASS_NAME}}: {{exc}}"}})
        return
    method = getattr(inst, METHOD, None)
    if method is None:
        _emit({{"verdict": "RE", "message": f"missing method {{METHOD}}"}})
        return
    index = 0
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        test = json.loads(line)
        args = test.get("args") or []
        expected = test.get("expected")
        try:
            got = method(*args)
            got_c = _canon(got)
        except Exception:
            _emit({{
                "verdict": "RE",
                "failed_index": index,
                "message": traceback.format_exc()[-2000:],
                "passed": index,
                "total": index,
            }})
            return
        if not _eq(got_c, expected, COMPARE):
            _emit({{
                "verdict": "WA",
                "failed_index": index,
                "got": got_c,
                "passed": index,
                "total": index,
            }})
            return
        del test, args, expected, got, got_c
        index += 1
    _emit({{"verdict": "AC", "passed": index, "total": index}})


if __name__ == "__main__":
    main()
'''


def wrap_python(user_code: str, signature: dict[str, Any]) -> str:
    harness = HARNESS.format(
        method=signature["method"],
        class_name=signature.get("class_name") or "Solution",
        compare=signature.get("compare") or "exact",
    )
    return user_code.rstrip() + "\n\n" + harness
