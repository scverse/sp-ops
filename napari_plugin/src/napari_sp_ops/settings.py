"""Reader settings with defaults in one place, overridable through environment variables."""

import os
from dataclasses import dataclass

ENV_PREFIX = "NAPARI_SP_OPS_"


@dataclass(frozen=True)
class Settings:
    layer_budget: int = 64
    stage_preference: str = "processed"
    prefer_merged: bool = True
    points_cap: int = 2_000_000

    @classmethod
    def from_env(cls) -> "Settings":
        """Read ``NAPARI_SP_OPS_LAYER_BUDGET`` and friends, falling back to the defaults."""
        defaults = cls()
        return cls(
            layer_budget=int(os.environ.get(f"{ENV_PREFIX}LAYER_BUDGET", defaults.layer_budget)),
            stage_preference=os.environ.get(f"{ENV_PREFIX}STAGE", defaults.stage_preference),
            prefer_merged=os.environ.get(f"{ENV_PREFIX}PREFER", "merged") != "tiles",
            points_cap=int(os.environ.get(f"{ENV_PREFIX}POINTS_CAP", defaults.points_cap)),
        )
