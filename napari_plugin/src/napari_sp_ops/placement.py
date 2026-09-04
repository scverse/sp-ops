"""Where each tile of a ``tiles`` collection sits in the well frame."""

import warnings

from napari_sp_ops import nodes, vector


def tile_translations(tiles: nodes.Node, children: list[nodes.Node]) -> dict[int, tuple[float, float]]:
    """Return y, x offsets in micrometres per tile index, from the ``layout`` polygons.

    A ``scene`` on the collection is reported but not applied yet; the layout
    polygon's minimum corner places every tile.
    """
    if "scene" in tiles.attributes:
        warnings.warn(f"napari-sp-ops does not apply the scene transforms of {tiles.name} yet; placing tiles from the layout", stacklevel=2)
    layout = next((child for child in children if nodes.kind(child) == "shapes"), None)
    if layout is None:
        return {}
    try:
        return vector.polygon_min_corners(layout.group)
    except Exception as exc:
        warnings.warn(f"napari-sp-ops could not read the layout of {tiles.name}: {exc}", stacklevel=2)
        return {}


def tile_index(tile: nodes.Node) -> int | None:
    value = tile.attributes.get("sp-ops:tile", {}).get("index")
    return int(value) if value is not None else None
