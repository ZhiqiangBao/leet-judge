from __future__ import annotations

from ..base import LanguageAdapter
from .c11 import C11Adapter
from .cpp17 import Cpp17Adapter
from .go import GoAdapter
from .javascript import JavascriptAdapter
from .python3 import Python3Adapter
from .rust import RustAdapter
from .typescript import TypescriptAdapter
from .zig import ZigAdapter

ADAPTERS: dict[str, LanguageAdapter] = {
    adapter.id: adapter
    for adapter in (
        Python3Adapter(),
        C11Adapter(),
        Cpp17Adapter(),
        JavascriptAdapter(),
        TypescriptAdapter(),
        GoAdapter(),
        RustAdapter(),
        ZigAdapter(),
    )
}


def get_adapter(language: str) -> LanguageAdapter | None:
    return ADAPTERS.get(language)


def language_status() -> list[dict]:
    out = []
    for adapter in ADAPTERS.values():
        out.append(
            {
                "id": adapter.id,
                "display_name": adapter.display_name,
                "implemented": adapter.implemented,
                "available": adapter.available(),
                "runtime_detected": adapter.detect(),
                "runtime_version": adapter.runtime_version(),
                "reason": adapter.reason(),
            }
        )
    return out
