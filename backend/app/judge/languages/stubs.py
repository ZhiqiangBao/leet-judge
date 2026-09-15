from __future__ import annotations

from ..base import LanguageAdapter


class _StubAdapter(LanguageAdapter):
    implemented = False

    def wrap(self, user_code: str, signature: dict) -> str:
        raise NotImplementedError(f"{self.id} adapter is a reserved stub")

    def run_argv(self, workdir: str) -> list[str]:
        raise NotImplementedError(f"{self.id} adapter is a reserved stub")
