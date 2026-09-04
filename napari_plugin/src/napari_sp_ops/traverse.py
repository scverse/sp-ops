"""Open an sp-ops collection and everything image-like beneath it, within a layer budget."""

import warnings
from dataclasses import dataclass, field
from typing import Any

from napari_sp_ops import nodes, placement, rounds, vector
from napari_sp_ops.images import Placement, read_multiscale
from napari_sp_ops.settings import Settings

AnyLayerData = tuple[Any, dict[str, Any], str]


@dataclass
class Budget:
    limit: int
    used: int = 0
    skipped: list[str] = field(default_factory=list)

    def allows(self, node: nodes.Node) -> bool:
        if self.used < self.limit:
            return True
        self.skipped.append(node.name)
        return False

    def add(self, layers: list[AnyLayerData]) -> list[AnyLayerData]:
        self.used += sum(napari_layer_count(layer) for layer in layers)
        return layers


def napari_layer_count(layer: AnyLayerData) -> int:
    """A channel-split image is one layer-data tuple but one napari layer per name."""
    name = layer[1].get("name")
    return len(name) if isinstance(name, list) else 1


def read_node(node: nodes.Node, settings: Settings | None = None) -> list[AnyLayerData]:
    """Return the layers for a node of any kind, warning about what the budget skipped."""
    settings = settings or Settings.from_env()
    budget = Budget(settings.layer_budget)
    layers = _read(node, Placement(), settings, budget)
    if budget.skipped:
        warnings.warn(f"napari-sp-ops stopped at {settings.layer_budget} layers; skipped {', '.join(budget.skipped)}", stacklevel=2)
    return layers


def _read(node: nodes.Node, where: Placement, settings: Settings, budget: Budget) -> list[AnyLayerData]:
    if not budget.allows(node):
        return []
    kind = nodes.kind(node)
    if kind == "multiscale":
        return budget.add([read_multiscale(node.group, where)])
    if kind == "shapes":
        return budget.add([vector.read_shapes(node.group, where)])
    if kind == "points":
        return budget.add([vector.read_points(node.group, settings.points_cap, where)])
    if kind == "table":
        return []
    if kind == "screen":
        return _read_screen(node, where, settings, budget)
    if kind == "plate":
        return _read_plate(node, where, settings, budget)
    if kind == "well":
        return _read_children(node, where, settings, budget, prefix_with_name=True)
    if kind == "modality":
        return _read_modality(node, where, settings, budget)
    if kind == "tiles":
        return _read_tiles(node, where, settings, budget)
    if kind == "tile":
        return _read_tile(node, where, settings, budget)
    if kind == "round":
        return _read_children(node, Placement(where.name_prefix + nodes.round_label(node) + " ", where.translation_yx, where.visible, where.metadata), settings, budget)
    if kind in ("merged", "collection"):
        return _read_children(node, where, settings, budget)
    warnings.warn(f"napari-sp-ops does not know how to open {node.name}", stacklevel=2)
    return []


def _read_children(node: nodes.Node, where: Placement, settings: Settings, budget: Budget, prefix_with_name: bool = False) -> list[AnyLayerData]:
    layers: list[AnyLayerData] = []
    for child in node.children():
        child_where = where
        if prefix_with_name:
            child_where = Placement(f"{where.name_prefix}{child.name} ", where.translation_yx, where.visible, where.metadata)
        layers.extend(_read(child, child_where, settings, budget))
    return layers


def _read_screen(node: nodes.Node, where: Placement, settings: Settings, budget: Budget) -> list[AnyLayerData]:
    plates = [child for child in node.children() if nodes.kind(child) == "plate"]
    if not plates:
        warnings.warn(f"napari-sp-ops found no plate in {node.name}", stacklevel=2)
        return []
    preferred = [plate for plate in plates if plate.attributes.get("sp-ops:stage") == settings.stage_preference]
    chosen = (preferred or plates)[0]
    if len(plates) > 1:
        warnings.warn(f"napari-sp-ops opens plate {chosen.name}; the screen also has {', '.join(p.name for p in plates if p is not chosen)}", stacklevel=2)
    return _read(chosen, where, settings, budget)


def _read_plate(node: nodes.Node, where: Placement, settings: Settings, budget: Budget) -> list[AnyLayerData]:
    plate = node.attributes.get("plate", {})
    rows = [row.get("id", row.get("name")) for row in plate.get("rows", [])]
    columns = [column.get("id", column.get("name")) for column in plate.get("columns", [])]

    def order(child: nodes.Node) -> tuple[int, int]:
        well = child.attributes.get("well", {})
        row = well.get("row", {}).get("id")
        column = well.get("column", {}).get("id")
        return (rows.index(row) if row in rows else len(rows), columns.index(column) if column in columns else len(columns))

    wells = sorted((child for child in node.children() if nodes.kind(child) == "well"), key=order)
    if not wells:
        warnings.warn(f"napari-sp-ops found no well in {node.name}", stacklevel=2)
        return []
    if len(wells) > 1:
        warnings.warn(f"napari-sp-ops opens well {wells[0].name}; the plate also has {', '.join(w.name for w in wells[1:])}", stacklevel=2)
    return _read(wells[0], where, settings, budget)


def _read_modality(node: nodes.Node, where: Placement, settings: Settings, budget: Budget) -> list[AnyLayerData]:
    children = {nodes.kind(child): child for child in node.children()}
    order = ("merged", "tiles") if settings.prefer_merged else ("tiles", "merged")
    for kind in order:
        if kind in children:
            return _read(children[kind], where, settings, budget)
    return _read_children(node, where, settings, budget)


def _read_tiles(node: nodes.Node, where: Placement, settings: Settings, budget: Budget) -> list[AnyLayerData]:
    children = node.children()
    offsets = placement.tile_translations(node, children)
    layers: list[AnyLayerData] = []
    for child in children:
        kind = nodes.kind(child)
        if kind == "shapes":
            layers.extend(_read(child, where, settings, budget))
        elif kind == "tile":
            index = placement.tile_index(child)
            offset = offsets.get(index) if index is not None else None
            tile_where = Placement(f"{where.name_prefix}{child.name} ", offset, where.visible, {**where.metadata, "tile": index})
            layers.extend(_read(child, tile_where, settings, budget))
        else:
            layers.extend(_read(child, where, settings, budget))
    return layers


def _read_tile(node: nodes.Node, where: Placement, settings: Settings, budget: Budget) -> list[AnyLayerData]:
    children = node.children()
    round_nodes = [child for child in children if nodes.kind(child) == "round"]
    layers: list[AnyLayerData] = []
    if round_nodes:
        layers.extend(budget.add(rounds.stack_rounds(node, round_nodes, where)))
    for child in children:
        if nodes.kind(child) != "round":
            layers.extend(_read(child, where, settings, budget))
    return layers
