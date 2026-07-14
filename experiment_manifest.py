from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class ExperimentManifest:
    batch_id: str
    hypothesis: str
    strategy_family: str
    intended_universe: str
    economic_mechanism: str
    causal_inputs: str
    parameter_budget: str
    expected_failure_regime: str
    rejection_condition: str
    universe_id: str = "qqq"

    @classmethod
    def from_path(cls, path: Path) -> "ExperimentManifest":
        payload = json.loads(path.read_text())
        required = set(cls.__annotations__) - {"universe_id"}
        missing = sorted(required - set(payload))
        extra = sorted(set(payload) - set(cls.__annotations__))
        if missing or extra:
            raise ValueError(f"manifest fields mismatch; missing={missing}, extra={extra}")
        payload.setdefault("universe_id", "qqq")
        manifest = cls(**payload)
        if any(not value.strip() for value in asdict(manifest).values()):
            raise ValueError("manifest fields must not be empty")
        return manifest

    def as_payload(self) -> dict[str, str]:
        return asdict(self)
