"""Where each tile of a ``tiles`` collection sits in the well frame."""

import warnings

import numpy as np

from napari_sp_ops import nodes, rfc8, vector
from napari_sp_ops.images import Placement


def layout_node(tiles: nodes.Node, children: list[nodes.Node]) -> nodes.Node | None:
    """The shapes node that ``sp-ops:tiles.layout`` references, else the first shapes child."""
    reference = tiles.attributes.get("sp-ops:tiles", {}).get("layout")
    ref = rfc8.resolve_reference([child.ref for child in children if child.ref], reference)
    if ref is not None:
        return next((child for child in children if child.ref is ref), None)
    return next((child for child in children if nodes.kind(child) == "shapes"), None)


def tile_offsets(layout_layer: vector.VectorLayerData) -> dict[int, tuple[float, float]]:
    """Per tile index, the y, x minimum corner of its layout polygon, in the layout's units."""
    polygons, metadata, _ = layout_layer
    keys = metadata["features"].get(vector.TILE_COLUMN)
    if keys is None:
        warnings.warn(f"napari-sp-ops found no {vector.TILE_COLUMN!r} column in {metadata['name']}; tiles stay at the origin", stacklevel=2)
        return {}
    return vector.min_corners(polygons, np.asarray(keys))


def tile_index(tile: nodes.Node) -> int | None:
    value = tile.attributes.get("sp-ops:tile", {}).get("index")
    return int(value) if value is not None else None


def compose(where: Placement, offset: tuple[float, float] | None) -> tuple[float, float] | None:
    """Add a tile offset to whatever translation the ancestors already carry."""
    if offset is None:
        return where.translation_yx
    if where.translation_yx is None:
        return offset
    return (where.translation_yx[0] + offset[0], where.translation_yx[1] + offset[1])
