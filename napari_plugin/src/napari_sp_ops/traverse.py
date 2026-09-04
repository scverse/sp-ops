"""Open an sp-ops collection and everything image-like beneath it, within a layer budget."""

import warnings
from dataclasses import dataclass, field, replace
from typing import Any

from napari_sp_ops import features, nodes, placement, rfc8, rounds, vector
from napari_sp_ops.images import Placement, read_multiscale
from napari_sp_ops.settings import Settings

AnyLayerData = tuple[Any, dict[str, Any], str]


@dataclass
class Budget:
    limit: int
    used: int = 0
    skipped: list[str] = field(default_factory=list)

    @property
    def exhausted(self) -> bool:
        return self.used >= self.limit

    def count(self, layers: list[AnyLayerData]) -> None:
        self.used += sum(napari_layer_count(layer) for layer in layers)


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
        warnings.warn(f"napari-sp-ops stopped after {budget.used} layers (budget {budget.limit}); skipped {', '.join(budget.skipped)}", stacklevel=2)
    elif not layers and nodes.kind(node) not in ("table", "unknown"):
        warnings.warn(f"napari-sp-ops found nothing to show under {node.name}", stacklevel=2)
    return layers


def _read(node: nodes.Node, where: Placement, settings: Settings, budget: Budget) -> list[AnyLayerData]:
    if budget.exhausted:
        budget.skipped.append(node.name)
        return []
    kind = nodes.kind(node)
    if kind == "multiscale":
        layers: list[AnyLayerData] = [read_multiscale(node, where)]
    elif kind == "shapes":
        layers = [vector.read_shapes(node, where)]
    elif kind == "points":
        layers = [vector.read_points(node, settings.points_cap, where)]
    elif kind == "table":
        warnings.warn(f"napari-sp-ops opens nothing for the table {node.name}: tables have no napari layer type", stacklevel=2)
        return []
    elif kind == "screen":
        return _read_screen(node, where, settings, budget)
    elif kind == "plate":
        return _read_plate(node, where, settings, budget)
    elif kind == "well":
        return _read_children(node, where, settings, budget, prefix_children=True)
    elif kind == "modality":
        return _read_modality(node, where, settings, budget)
    elif kind == "tiles":
        return _read_tiles(node, where, settings, budget)
    elif kind == "tile":
        return _read_tile(node, where, settings, budget)
    elif kind == "round":
        return _read_children(node, _prefixed(where, nodes.round_label(node)), settings, budget)
    elif kind in ("merged", "collection"):
        return _read_children(node, where, settings, budget)
    else:
        warnings.warn(f"napari-sp-ops does not know how to open {node.name}", stacklevel=2)
        return []
    budget.count(layers)
    return layers


def _prefixed(where: Placement, label: str) -> Placement:
    return replace(where, name_prefix=f"{where.name_prefix}{label} ")


def _warn_scene(node: nodes.Node) -> None:
    if "scene" in node.attributes:
        warnings.warn(f"napari-sp-ops does not apply the scene transforms of {node.name} yet; placing tiles from the layout", stacklevel=2)


def _read_children(node: nodes.Node, where: Placement, settings: Settings, budget: Budget, prefix_children: bool = False) -> list[AnyLayerData]:
    _warn_scene(node)
    layers: list[AnyLayerData] = []
    for child in node.children():
        child_where = _prefixed(where, child.name) if prefix_children else where
        child_layers = _read(child, child_where, settings, budget)
        for _, metadata, layer_type in child_layers:
            if layer_type == "labels":
                table_features = features.label_features(node, child.name)
                if table_features is not None:
                    metadata["features"] = table_features
        layers.extend(child_layers)
    return layers


def _read_screen(node: nodes.Node, where: Placement, settings: Settings, budget: Budget) -> list[AnyLayerData]:
    plates = [ref for ref in node.child_refs() if ref.type == "collection"]
    if not plates:
        warnings.warn(f"napari-sp-ops found no plate in {node.name}", stacklevel=2)
        return []
    preferred = [ref for ref in plates if ref.attributes.get("sp-ops:stage") == settings.stage]
    chosen = (preferred or plates)[0]
    if len(plates) > 1:
        warnings.warn(f"napari-sp-ops opens plate {chosen.name}; the screen also has {', '.join(p.name for p in plates if p is not chosen)}", stacklevel=2)
    child = node.child(chosen)
    return _read(child, where, settings, budget) if child else []


def _read_plate(node: nodes.Node, where: Placement, settings: Settings, budget: Budget) -> list[AnyLayerData]:
    plate = node.attributes.get("plate", {})
    rows = [row.get("id", row.get("name")) for row in plate.get("rows", [])]
    columns = [column.get("id", column.get("name")) for column in plate.get("columns", [])]

    def order(ref: rfc8.NodeRef) -> tuple[int, int]:
        well = ref.attributes.get("well", {})
        row = well.get("row", {}).get("id")
        column = well.get("column", {}).get("id")
        return (rows.index(row) if row in rows else len(rows), columns.index(column) if column in columns else len(columns))

    wells = sorted((ref for ref in node.child_refs() if "well" in ref.attributes), key=order)
    if not wells:
        warnings.warn(f"napari-sp-ops found no well in {node.name}", stacklevel=2)
        return []
    if len(wells) > 1:
        warnings.warn(f"napari-sp-ops opens well {wells[0].name}; the plate also has {', '.join(w.name for w in wells[1:])}", stacklevel=2)
    child = node.child(wells[0])
    return _read(child, where, settings, budget) if child else []


def _read_modality(node: nodes.Node, where: Placement, settings: Settings, budget: Budget) -> list[AnyLayerData]:
    _warn_scene(node)
    children = {nodes.kind(child): child for child in node.children()}
    order = ("merged", "tiles") if settings.prefer != "tiles" else ("tiles", "merged")
    for kind in order:
        if kind in children:
            return _read(children[kind], where, settings, budget)
    return _read_children(node, where, settings, budget)


def _read_tiles(node: nodes.Node, where: Placement, settings: Settings, budget: Budget) -> list[AnyLayerData]:
    _warn_scene(node)
    children = node.children()
    layout = placement.layout_node(node, children)
    offsets: dict[int, tuple[float, float]] = {}
    layers: list[AnyLayerData] = []
    if layout is None:
        warnings.warn(f"napari-sp-ops found no layout in {node.name}; its tiles share the origin", stacklevel=2)
    else:
        layout_layers = _read(layout, where, settings, budget)
        if layout_layers:
            offsets = placement.tile_offsets(layout_layers[0])
        layers.extend(layout_layers)
    for child in children:
        if child is layout:
            continue
        if nodes.kind(child) != "tile":
            layers.extend(_read(child, where, settings, budget))
            continue
        index = placement.tile_index(child)
        offset = offsets.get(index) if index is not None else None
        if offset is None and offsets:
            warnings.warn(f"napari-sp-ops found no layout polygon for {child.name}; it stays at the origin", stacklevel=2)
        tile_where = replace(_prefixed(where, child.name), translation_yx=placement.compose(where, offset), metadata={**where.metadata, "tile": index})
        layers.extend(_read(child, tile_where, settings, budget))
    return layers


def _read_tile(node: nodes.Node, where: Placement, settings: Settings, budget: Budget) -> list[AnyLayerData]:
    children = node.children()
    round_nodes = [child for child in children if nodes.kind(child) == "round"]
    layers: list[AnyLayerData] = []
    if round_nodes:
        stacked = rounds.stack_rounds(node, round_nodes, where)
        budget.count(stacked)
        layers.extend(stacked)
    for child in children:
        if nodes.kind(child) != "round":
            layers.extend(_read(child, where, settings, budget))
    return layers
