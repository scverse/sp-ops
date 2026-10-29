"""``sp-ops:channels`` to napari layer names and colormaps."""

from dataclasses import dataclass
from typing import Any

NUCLEAR_COLORMAP = "blue"
BASE_PALETTE = ("green", "red", "magenta", "cyan")
STAIN_PALETTE = ("green", "magenta")
OTHER_COLORMAP = "gray"
GRAY_CHANNEL_TYPES = {"labelfree", "predicted"}


@dataclass(frozen=True)
class Channel:
    name: str
    role: str = "other"
    channel_type: str | None = None
    description: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "role": self.role, "channel_type": self.channel_type, "description": self.description}


def parse_channels(attributes: dict[str, Any], count: int) -> list[Channel]:
    """Return ``count`` channels from ``sp-ops:channels``, padding or truncating to match the array.

    A per-round list of lists (channels that differ between rounds) is
    collapsed to its first round; the round slider still shows every round.
    """
    raw = attributes.get("sp-ops:channels") or []
    if raw and isinstance(raw[0], list):
        raw = raw[0]
    channels: list[Channel] = []
    for index in range(count):
        entry = raw[index] if index < len(raw) and isinstance(raw[index], dict) else {}
        name = entry.get("name") or f"channel{index}"
        channels.append(Channel(name, entry.get("role") or "other", entry.get("channel_type"), entry.get("description")))
    return channels


def colormaps(channels: list[Channel]) -> list[str]:
    """Assign one napari colormap name per channel from its role."""
    names: list[str] = []
    base_seen = 0
    stain_seen = 0
    for channel in channels:
        if channel.channel_type in GRAY_CHANNEL_TYPES:
            names.append(OTHER_COLORMAP)
        elif channel.role == "nuclear":
            names.append(NUCLEAR_COLORMAP)
        elif channel.role == "base":
            names.append(BASE_PALETTE[base_seen % len(BASE_PALETTE)])
            base_seen += 1
        elif channel.role == "stain":
            names.append(STAIN_PALETTE[stain_seen % len(STAIN_PALETTE)])
            stain_seen += 1
        else:
            names.append(OTHER_COLORMAP)
    return names
