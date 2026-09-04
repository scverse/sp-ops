"""Reader settings with defaults in one place, overridable through environment variables."""

import os
import warnings
from dataclasses import dataclass, fields

ENV_PREFIX = "NAPARI_SP_OPS_"
ENV_NAMES = {"layer_budget": "LAYER_BUDGET", "stage": "STAGE", "prefer": "PREFER", "points_cap": "POINTS_CAP"}


@dataclass(frozen=True)
class Settings:
    layer_budget: int = 64
    stage: str = "processed"
    prefer: str = "merged"
    points_cap: int = 2_000_000

    @classmethod
    def from_env(cls) -> "Settings":
        """Read ``NAPARI_SP_OPS_LAYER_BUDGET`` and friends; a blank or unparsable value keeps the default."""
        values: dict[str, object] = {}
        for item in fields(cls):
            raw = os.environ.get(ENV_PREFIX + ENV_NAMES[item.name], "").strip()
            if not raw:
                continue
            try:
                values[item.name] = item.type(raw) if item.type is int else raw
            except ValueError:
                warnings.warn(f"napari-sp-ops ignores {ENV_PREFIX}{ENV_NAMES[item.name]}={raw!r}; expected an integer", stacklevel=2)
        return cls(**values)
