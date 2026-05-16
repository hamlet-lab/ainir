from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import yaml


Severity = str


@dataclass(frozen=True)
class Finding:
    rule: str
    severity: Severity
    message: str
    target: str = "module"
    suggestion: Optional[str] = None

    def as_dict(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "rule": self.rule,
            "severity": self.severity,
            "target": self.target,
            "message": self.message,
        }
        if self.suggestion:
            data["suggestion"] = self.suggestion
        return data


@dataclass
class VerificationReport:
    module_id: str
    workflow: str
    status: str
    findings: List[Finding] = field(default_factory=list)

    @property
    def critical_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "critical")

    @property
    def warning_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "warning")

    def as_dict(self) -> Dict[str, Any]:
        return {
            "module_id": self.module_id,
            "workflow": self.workflow,
            "status": self.status,
            "critical_count": self.critical_count,
            "warning_count": self.warning_count,
            "findings": [f.as_dict() for f in self.findings],
        }


@dataclass
class DraftModule:
    raw: Dict[str, Any]

    @property
    def module_id(self) -> str:
        return str(self.raw.get("module", "unknown"))

    @property
    def workflow(self) -> str:
        return str(self.raw.get("workflow", "unknown"))

    @property
    def task(self) -> str:
        return str(self.raw.get("task", self.workflow))

    @property
    def environment(self) -> str:
        return str(self.raw.get("environment", "unspecified"))

    @property
    def operations(self) -> List[Dict[str, Any]]:
        value = self.raw.get("operations", [])
        if not isinstance(value, list):
            return []
        return [op for op in value if isinstance(op, dict)]

    @property
    def claims(self) -> List[Dict[str, Any]]:
        value = self.raw.get("claims", [])
        if not isinstance(value, list):
            return []
        return [claim for claim in value if isinstance(claim, dict)]

    @property
    def holes(self) -> List[Dict[str, Any]]:
        value = self.raw.get("holes", [])
        if not isinstance(value, list):
            return []
        return [hole for hole in value if isinstance(hole, dict)]

    @property
    def policies(self) -> List[Dict[str, Any]]:
        value = self.raw.get("policies", [])
        if not isinstance(value, list):
            return []
        return [policy for policy in value if isinstance(policy, dict)]

    def policy_ids(self) -> set[str]:
        ids: set[str] = set()
        for p in self.policies:
            pid = p.get("id") or p.get("policy")
            if isinstance(pid, str) and pid:
                ids.add(pid)
        return ids

    def all_effects(self) -> List[tuple[str, str]]:
        effects: List[tuple[str, str]] = []
        for op in self.operations:
            op_id = str(op.get("id", "unknown_op"))
            raw_effects = op.get("effects", [])
            if not isinstance(raw_effects, list):
                continue
            for eff in raw_effects:
                if isinstance(eff, str):
                    effects.append((op_id, eff))
        return effects

    def operation_by_id(self, op_id: str) -> Optional[Dict[str, Any]]:
        for op in self.operations:
            if str(op.get("id")) == op_id:
                return op
        return None


def load_draft(path: str | Path) -> DraftModule:
    """Load an untrusted YAML draft without throwing on malformed shape.

    The public demo treats provider/model output as untrusted. Non-object YAML
    and parse errors are converted into invalid DraftModule objects so the CLI
    reports `status: invalid` instead of printing a Python traceback.
    """
    source = Path(path)
    try:
        with source.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as exc:
        return DraftModule(raw={"__parse_error__": str(exc), "__source_path__": str(source)})
    except OSError as exc:
        return DraftModule(raw={"__load_error__": str(exc), "__source_path__": str(source)})

    if data is None:
        data = {}
    if not isinstance(data, dict):
        return DraftModule(raw={"__invalid_root__": type(data).__name__, "__source_path__": str(source)})
    data = dict(data)
    data["__source_path__"] = str(source)
    return DraftModule(raw=data)


def dump_yaml(data: Any, path: str | Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with Path(path).open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)


def iter_example_drafts(root: str | Path) -> Iterable[Path]:
    root_path = Path(root)
    if (root_path / "examples").exists():
        yield from sorted(root_path.glob("examples/*/draft.yaml"))
    else:
        yield from sorted(root_path.glob("*/draft.yaml"))
