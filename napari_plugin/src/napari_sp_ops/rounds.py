"""Stack the rounds of a raw tile along a ``round`` axis, for viewing only."""

import warnings
from typing import Any

import dask.array as da

from napari_sp_ops import nodes
from napari_sp_ops.images import LayerData, Placement, read_multiscale


def channel_layers(round_node: nodes.Node, placement: Placement) -> dict[int, LayerData]:
    """One layer per channel multiscale of a round, keyed by array position."""
    layers: dict[int, LayerData] = {}
    for child in round_node.children():
        if nodes.kind(child) == "multiscale":
            layers[nodes.channel_position(child)] = read_multiscale(child.group, placement)
    return layers


def stack_rounds(tile: nodes.Node, round_nodes: list[nodes.Node], placement: Placement) -> list[LayerData]:
    """Return one layer per channel position with the rounds stacked along a leading axis.

    Rounds are stacked lazily when every round of a channel position has the
    same pyramid shapes and dtype. Otherwise that channel falls back to one
    layer per round. Nothing is resampled and the layer name says the data is
    unaligned.
    """
    per_round: list[tuple[nodes.Node, dict[int, LayerData]]] = []
    for round_node in sorted(round_nodes, key=lambda node: node.attributes.get("sp-ops:axis", {}).get("index", 0)):
        per_round.append((round_node, channel_layers(round_node, Placement(translation_yx=placement.translation_yx))))
    positions = sorted({position for _, layers in per_round for position in layers})
    result: list[LayerData] = []
    for position in positions:
        entries = [(round_node, layers[position]) for round_node, layers in per_round if position in layers]
        pyramids = [layer[0] for _, layer in entries]
        signature = {tuple((level.shape, str(level.dtype)) for level in pyramid) for pyramid in pyramids}
        if len(signature) != 1:
            warnings.warn(f"napari-sp-ops cannot stack channel {position} of {tile.name}: rounds differ in shape or dtype", stacklevel=2)
            for round_node, (pyramid, metadata, layer_type) in entries:
                metadata["name"] = f"{placement.name_prefix}{nodes.round_label(round_node)} {metadata['name']}"
                result.append((pyramid, metadata, layer_type))
            continue
        first_metadata = entries[0][1][1]
        stacked = [da.stack([pyramid[level] for pyramid in pyramids]) for level in range(len(pyramids[0]))]
        metadata: dict[str, Any] = dict(first_metadata)
        metadata["name"] = f"{placement.name_prefix}{first_metadata['name']} (unaligned)"
        metadata["scale"] = [1.0, *first_metadata["scale"]]
        metadata["translate"] = [0.0, *first_metadata["translate"]]
        metadata["axis_labels"] = ("round", *first_metadata["axis_labels"])
        if "units" in first_metadata:
            metadata["units"] = (None, *first_metadata["units"])
        metadata["metadata"] = {
            "sp-ops": {
                **placement.metadata,
                **first_metadata["metadata"]["sp-ops"],
                "rounds": [round_node.attributes.get("sp-ops:axis", {}) | {"acquisition": round_node.attributes.get("acquisition")} for round_node, _ in entries],
            }
        }
        result.append((stacked, metadata, "image"))
    return result
