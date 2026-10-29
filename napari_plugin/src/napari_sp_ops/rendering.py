"""OME-NGFF ``omero`` rendering hints to napari colormaps and contrast limits."""

import re
from dataclasses import dataclass
from typing import Any

import zarr

from napari_sp_ops import rfc8

HEX_COLOR = re.compile(r"^#?([0-9A-Fa-f]{6})$")


@dataclass(frozen=True)
class Rendering:
    """Per-channel display hints: a ``#RRGGBB`` color and a ``(start, end)`` window."""

    color: str | None = None
    window: tuple[float, float] | None = None


def parse_omero(group: zarr.Group) -> list[Rendering]:
    """Return one ``Rendering`` per ``omero.channels`` entry, empty when the node has none.

    Malformed colors and windows are dropped entry by entry, so a store that
    writes only colors still gets them.
    """
    omero = rfc8.ome(group).get("omero")
    if not isinstance(omero, dict):
        return []
    channels = omero.get("channels")
    if not isinstance(channels, list):
        return []
    return [_parse_channel(entry) for entry in channels]


def _parse_channel(entry: Any) -> Rendering:
    if not isinstance(entry, dict):
        return Rendering()
    color = None
    match = HEX_COLOR.match(str(entry.get("color", "")))
    if match:
        color = f"#{match.group(1).upper()}"
    window = None
    raw = entry.get("window")
    if isinstance(raw, dict):
        try:
            start, end = float(raw["start"]), float(raw["end"])
        except (KeyError, TypeError, ValueError):
            start = end = float("nan")
        if start < end:
            window = (start, end)
    return Rendering(color, window)


def apply(renderings: list[Rendering], colormaps: list[str], limits: list[list[float]] | None) -> tuple[list[str], list[list[float] | None]]:
    """Override role colormaps and estimated limits with the store's hints, channel by channel.

    A channel without a window and without an estimate gets ``None``, which
    napari reads as its own default.
    """
    colormaps = list(colormaps)
    merged: list[list[float] | None] = [list(pair) for pair in limits] if limits else [None] * len(colormaps)
    for index, rendering in enumerate(renderings[: len(colormaps)]):
        if rendering.color:
            colormaps[index] = rendering.color
        if rendering.window:
            merged[index] = list(rendering.window)
    return colormaps, merged
