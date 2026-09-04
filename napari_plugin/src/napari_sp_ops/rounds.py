"""Stack the rounds of a raw tile along a ``round`` axis, for viewing only."""

import warnings
from dataclasses import replace
from typing import Any

import dask.array as da

from napari_sp_ops import nodes
from napari_sp_ops.images import LayerData, Placement, read_multiscale

FALLBACK_BASE = 1000


def channel_layers(round_node: nodes.Node, placement: Placement) -> dict[int, LayerData]:
    """One layer per channel multiscale of a round, keyed by its declared array position.

    Channels without ``sp-ops:axis`` are keyed by their order after every
    declared position, and a duplicate position is reported and shifted.
    """
    layers: dict[int, LayerData] = {}
    for order, child in enumerate(round_node.children()):
        if nodes.kind(child) != "multiscale":
            continue
        position = nodes.channel_position(child)
        key = FALLBACK_BASE + order if position is None else position
        while key in layers:
            warnings.warn(f"napari-sp-ops found two channels at position {key} in {round_node.name}; shifting {child.name}", stacklevel=2)
            key += FALLBACK_BASE
        layers[key] = read_multiscale(child, placement)
    return layers


def _stackable(entries: list[tuple[nodes.Node, LayerData]]) -> bool:
    if any(isinstance(layer[1].get("name"), list) for _, layer in entries):
        return False
    signature = {tuple((level.shape, str(level.dtype)) for level in layer[0]) for _, layer in entries}
    return len(signature) == 1


def _prefixed(name: str | list[str], prefix: str) -> str | list[str]:
    return [prefix + item for item in name] if isinstance(name, list) else prefix + name


def stack_rounds(tile: nodes.Node, round_nodes: list[nodes.Node], placement: Placement) -> list[LayerData]:
    """Return one layer per channel position with the rounds stacked along a leading axis.

    Rounds are stacked lazily when every round of a channel position is a
    single-channel multiscale with the same pyramid shapes and dtype.
    Otherwise that channel falls back to one layer per round. Nothing is
    resampled and the layer name says the data is unaligned.
    """
    ordered = sorted(round_nodes, key=lambda node: node.attributes.get("sp-ops:axis", {}).get("index", 0))
    per_round = [(round_node, channel_layers(round_node, replace(placement, name_prefix=""))) for round_node in ordered]
    positions = sorted({position for _, layers in per_round for position in layers})
    result: list[LayerData] = []
    for position in positions:
        entries = [(round_node, layers[position]) for round_node, layers in per_round if position in layers]
        if not _stackable(entries):
            warnings.warn(f"napari-sp-ops cannot stack channel {position} of {tile.name}: rounds differ in shape, dtype or channel count", stacklevel=2)
            for round_node, (pyramid, metadata, layer_type) in entries:
                metadata["name"] = _prefixed(metadata["name"], f"{placement.name_prefix}{nodes.round_label(round_node)} ")
                result.append((pyramid, metadata, layer_type))
            continue
        pyramids = [layer[0] for _, layer in entries]
        first_metadata = entries[0][1][1]
        stacked = [da.stack([pyramid[level] for pyramid in pyramids]) for level in range(len(pyramids[0]))]
        metadata: dict[str, Any] = dict(first_metadata)
        metadata["name"] = f"{placement.name_prefix}{first_metadata['name']} (unaligned)"
        metadata["scale"] = [1.0, *first_metadata["scale"]]
        metadata["translate"] = [0.0, *first_metadata["translate"]]
        metadata["axis_labels"] = ("round", *first_metadata["axis_labels"])
        if "units" in first_metadata:
            metadata["units"] = (None, *first_metadata["units"])
        sp_ops = dict(first_metadata["metadata"]["sp-ops"])
        sp_ops["rounds"] = [{**round_node.attributes.get("sp-ops:axis", {}), "acquisition": round_node.attributes.get("acquisition")} for round_node, _ in entries]
        metadata["metadata"] = {"sp-ops": sp_ops}
        result.append((stacked, metadata, "image"))
    return result
