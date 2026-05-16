"""Trusted execution context for AiNIR public demo.

Pre-v1 Phase 5 separates runtime context from model-authored draft metadata. A
model draft may mention an environment, but that value is not used to relax
safety policies. Allowed contexts are read from the Safety Registry so verifier,
policy core, and CLI share the same boundary.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .safety_registry import get_registry

_DEFAULT_ENV = "public_demo"


def _context_config() -> dict:
    data = get_registry().data.get("trusted_execution_context", {}) or {}
    return data if isinstance(data, dict) else {}


def _allowed() -> set[str]:
    envs = _context_config().get("environments", []) or []
    return {str(e) for e in envs} or {"public_demo", "test", "staging", "production"}


def _test_like() -> set[str]:
    envs = _context_config().get("test_like", []) or []
    return {str(e) for e in envs} or {"public_demo", "test"}


@dataclass(frozen=True)
class TrustedExecutionContext:
    environment: str = _DEFAULT_ENV
    source: str = "cli"
    purpose: str = "verification"

    @classmethod
    def from_environment(cls, environment: str | None, *, source: str = "cli", purpose: str = "verification") -> "TrustedExecutionContext":
        env = (environment or _DEFAULT_ENV).strip().lower()
        allowed = _allowed()
        if env not in allowed:
            raise ValueError(f"Unsupported trusted environment: {environment!r}")
        return cls(environment=env, source=source, purpose=purpose)

    @classmethod
    def public_demo(cls) -> "TrustedExecutionContext":
        return cls(environment=_DEFAULT_ENV, source="default", purpose="verification")

    @property
    def is_test_like(self) -> bool:
        return self.environment in _test_like()

    @property
    def is_production(self) -> bool:
        return self.environment in set(_context_config().get("production", []) or ["production"])


def allowed_environments() -> Iterable[str]:
    return sorted(_allowed())
