from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from hashlib import sha256
from typing import Any, Dict, Iterable, List, Optional

import re
import yaml


Severity = str


class DuplicateKeyYAMLError(yaml.YAMLError):
    """Raised when untrusted YAML contains duplicate mapping keys.

    PyYAML's default loaders silently keep the last duplicate key. AiNIR receipts
    and trust decisions must not let a raw model/provider draft shadow one meaning
    with another, so draft loading rejects duplicates at every mapping depth.
    """


class ComplexKeyYAMLError(yaml.YAMLError):
    """Raised when untrusted YAML uses non-scalar mapping keys.

    AiNIR public drafts do not need YAML sequence/object keys. Rejecting them avoids
    unhashable-key crashes and prevents parser/viewer ambiguity in receipt inputs.
    """


class AliasYAMLError(yaml.YAMLError):
    """Raised when YAML aliases/anchors exceed the public demo input budget."""


class DepthLimitYAMLError(yaml.YAMLError):
    """Raised when parsed YAML exceeds the public demo nesting budget."""


MAX_YAML_BYTES = 1_000_000
MAX_YAML_DEPTH = 120
MAX_YAML_ALIAS_TOKENS = 64


class _UniqueKeySafeLoader(yaml.SafeLoader):
    pass


def _construct_unique_mapping(loader: yaml.SafeLoader, node: yaml.nodes.MappingNode, deep: bool = False):
    seen: set[object] = set()
    for key_node, _value_node in node.value:
        mark = getattr(key_node, "start_mark", None)
        location = f" at line {mark.line + 1}, column {mark.column + 1}" if mark is not None else ""
        if not isinstance(key_node, yaml.nodes.ScalarNode):
            raise ComplexKeyYAMLError(f"complex YAML mapping keys are forbidden{location}")
        key = loader.construct_object(key_node, deep=deep)
        if key in seen:
            raise DuplicateKeyYAMLError(f"duplicate YAML key {key!r}{location}")
        seen.add(key)
    return yaml.SafeLoader.construct_mapping(loader, node, deep=deep)


_UniqueKeySafeLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_unique_mapping,
)


def _depth_of(value: Any, limit: int = MAX_YAML_DEPTH, current: int = 0) -> int:
    if current > limit:
        raise DepthLimitYAMLError(f"YAML nesting depth exceeds {limit}")
    if isinstance(value, dict):
        if not value:
            return current
        return max(_depth_of(k, limit, current + 1) for k in value.keys()) if False else max(_depth_of(v, limit, current + 1) for v in value.values())
    if isinstance(value, list):
        if not value:
            return current
        return max(_depth_of(v, limit, current + 1) for v in value)
    return current


def load_yaml_no_duplicate_keys(text: str) -> Any:
    """Parse YAML while rejecting duplicate keys and resource-abusive shapes."""
    alias_tokens = len(re.findall(r"(?m)(?:^|[\s:,\[\{])([*&][A-Za-z0-9_-]+)", text))
    if alias_tokens > MAX_YAML_ALIAS_TOKENS:
        raise AliasYAMLError(f"YAML aliases/anchors exceed limit {MAX_YAML_ALIAS_TOKENS}")
    data = yaml.load(text, Loader=_UniqueKeySafeLoader)
    _depth_of(data)
    return data


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

    Raw-source provenance is captured separately from the canonical parsed draft
    because two distinct YAML byte streams can otherwise collapse to the same
    object. Duplicate mapping keys are rejected before semantic verification.
    """
    source = Path(path)
    try:
        raw_bytes = source.read_bytes()
    except OSError as exc:
        return DraftModule(raw={"__load_error__": str(exc), "__source_path__": str(source)})

    raw_source_sha256 = "sha256:" + sha256(raw_bytes).hexdigest()
    if len(raw_bytes) > MAX_YAML_BYTES:
        return DraftModule(raw={
            "__size_error__": f"draft exceeds {MAX_YAML_BYTES} byte limit",
            "__source_path__": str(source),
            "__raw_source_sha256__": raw_source_sha256,
        })
    try:
        text = raw_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        return DraftModule(raw={
            "__decode_error__": str(exc),
            "__source_path__": str(source),
            "__raw_source_sha256__": raw_source_sha256,
        })
    try:
        data = load_yaml_no_duplicate_keys(text)
    except DuplicateKeyYAMLError as exc:
        return DraftModule(raw={
            "__duplicate_key_error__": str(exc),
            "__source_path__": str(source),
            "__raw_source_sha256__": raw_source_sha256,
        })
    except ComplexKeyYAMLError as exc:
        return DraftModule(raw={
            "__complex_key_error__": str(exc),
            "__source_path__": str(source),
            "__raw_source_sha256__": raw_source_sha256,
        })
    except AliasYAMLError as exc:
        return DraftModule(raw={
            "__alias_error__": str(exc),
            "__source_path__": str(source),
            "__raw_source_sha256__": raw_source_sha256,
        })
    except DepthLimitYAMLError as exc:
        return DraftModule(raw={
            "__depth_error__": str(exc),
            "__source_path__": str(source),
            "__raw_source_sha256__": raw_source_sha256,
        })
    except (yaml.YAMLError, RecursionError, MemoryError) as exc:
        return DraftModule(raw={
            "__parse_error__": str(exc),
            "__source_path__": str(source),
            "__raw_source_sha256__": raw_source_sha256,
        })
    except Exception as exc:
        return DraftModule(raw={
            "__resource_error__": str(exc),
            "__source_path__": str(source),
            "__raw_source_sha256__": raw_source_sha256,
        })

    if data is None:
        data = {}
    if not isinstance(data, dict):
        return DraftModule(raw={
            "__invalid_root__": type(data).__name__,
            "__source_path__": str(source),
            "__raw_source_sha256__": raw_source_sha256,
        })
    data = dict(data)
    data["__source_path__"] = str(source)
    data["__raw_source_sha256__"] = raw_source_sha256
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
