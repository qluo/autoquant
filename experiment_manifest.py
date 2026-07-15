from __future__ import annotations

import json
import hashlib
from dataclasses import asdict, dataclass, field
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
    selection_dataset_id: str = "qqq_selection_v1"
    hypothesis_id: str = ""
    complexity_budget: dict[str, object] = field(default_factory=dict)

    @classmethod
    def from_path(cls, path: Path) -> "ExperimentManifest":
        payload = json.loads(path.read_text())
        required = set(cls.__annotations__) - {"universe_id", "selection_dataset_id", "hypothesis_id", "complexity_budget"}
        missing = sorted(required - set(payload))
        extra = sorted(set(payload) - set(cls.__annotations__))
        if missing or extra:
            raise ValueError(f"manifest fields mismatch; missing={missing}, extra={extra}")
        payload.setdefault("universe_id", "qqq")
        payload.setdefault("selection_dataset_id", "qqq_selection_v1")
        payload.setdefault("hypothesis_id", payload["batch_id"])
        payload.setdefault("complexity_budget", {})
        manifest = cls(**payload)
        text_fields = {
            name: value for name, value in asdict(manifest).items()
            if isinstance(value, str)
        }
        if any(not value.strip() for value in text_fields.values()):
            raise ValueError("manifest fields must not be empty")
        if manifest.complexity_budget and set(manifest.complexity_budget) != {
            "new_features", "new_free_parameters", "new_branches",
            "parameter_values_considered", "parameter_value_sources",
            "expected_trade_count", "effective_degrees_of_freedom",
        }:
            raise ValueError("complexity_budget fields mismatch")
        return manifest

    def as_payload(self) -> dict[str, str]:
        return asdict(self)

    def selection_fingerprint(self) -> str:
        fields = {
            "universe_id": self.universe_id,
            "strategy_family": self.strategy_family,
            "economic_mechanism": self.economic_mechanism,
            "causal_inputs": self.causal_inputs,
            "parameter_budget": self.parameter_budget,
            "hypothesis": self.hypothesis,
        }
        return hashlib.sha256(json.dumps(fields, sort_keys=True).encode()).hexdigest()
