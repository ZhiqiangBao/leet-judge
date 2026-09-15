from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class CompileResult:
    ok: bool
    log: str = ""


@dataclass
class RunResult:
    stdout: str = ""
    stderr: str = ""
    returncode: int = 0
    time_ms: int = 0
    tle: bool = False
    mle: bool = False


class LanguageAdapter(ABC):
    id: str
    display_name: str
    source_filename: str
    implemented: bool = True

    def detect(self) -> bool:
        return False

    def available(self) -> bool:
        return self.implemented and self.detect()

    def reason(self) -> str | None:
        if not self.implemented:
            return "adapter_stub"
        if not self.detect():
            return "compiler_missing"
        return None

    def runtime_version(self) -> str | None:
        return None

    @abstractmethod
    def wrap(self, user_code: str, signature: dict) -> str:
        raise NotImplementedError

    def compile(self, workdir: str) -> CompileResult:
        return CompileResult(ok=True)

    @abstractmethod
    def run_argv(self, workdir: str) -> list[str]:
        raise NotImplementedError
