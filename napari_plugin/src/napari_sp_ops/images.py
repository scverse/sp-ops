"""Turn one RFC-8 multiscale node into napari image, labels or RGB layer data."""

import posixpath
import warnings
from dataclasses import dataclass, field, replace
from typing import Any

import dask.array as da
import numpy as np
from napari.utils.transforms import Affine

from napari_sp_ops import channels as channels_module
from napari_sp_ops import nodes, rfc8, upstream

LayerData = tuple[list[da.Array], dict[str, Any], str]

RGB_LENGTHS = {3, 4}
CONTRAST_MAX_ELEMENTS = 2**20
CONTRAST_PERCENTILES = (1.0, 99.0)


@dataclass
class Placement:
    """Extra layer-level context a collection passes down to its leaves."""

    name_prefix: str = ""
    translation_yx: tuple[float, float] | None = None
    visible: bool | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    ancestors: list[tuple[nodes.Node, str]] = field(default_factory=list)

    def descend(self, parent: nodes.Node, child: nodes.Node) -> "Placement":
        """The placement for ``child``, recording ``parent`` and every earlier collection above it."""
        step = posixpath.normpath(child.ref.path) if child.ref and child.ref.path else child.name
        ancestors = [(collection, f"{relative}/{step}") for collection, relative in self.ancestors] + [(parent, step)]
        return replace(self, ancestors=ancestors)


def _channel_index(axes: list[rfc8.Axis]) -> int | None:
    for index, axis in enumerate(axes):
        if axis.type == "channel":
            return index
    return None


def classify(node: nodes.Node, axes: list[rfc8.Axis], array: da.Array) -> str:
    """Return ``rgb``, ``labels`` or ``image`` for a multiscale node."""
    channel_index = _channel_index(axes)
    if channel_index is not None and array.shape[channel_index] in RGB_LENGTHS and array.dtype == np.uint8:
        return "rgb"
    if "labels" in node.attributes:
        return "labels"
    return "image"


def _drop_axes(transforms: list[dict[str, Any]], indices: list[int]) -> list[dict[str, Any]]:
    for index in sorted(indices, reverse=True):
        transforms = [upstream.remove_axis_from_transform(transform, index) for transform in transforms]
    return transforms


def _transform_metadata(transforms: list[dict[str, Any]], ndim: int) -> dict[str, Any]:
    """``scale`` and ``translate`` for diagonal transforms; the full ``affine`` otherwise."""
    affine = upstream.transforms_to_affine(transforms, None) if transforms else None
    if affine is None:
        return {"scale": [1.0] * ndim, "translate": [0.0] * ndim}
    matrix = np.asarray(affine.affine_matrix, dtype=float)
    linear = matrix[:-1, :-1]
    if np.allclose(linear, np.diag(np.diag(linear))):
        return {"scale": np.diag(linear).tolist(), "translate": matrix[:-1, -1].tolist()}
    return {"scale": [1.0] * ndim, "translate": [0.0] * ndim, "affine": Affine(affine_matrix=matrix)}


def contrast_limits(level: da.Array, channel_index: int | None) -> list[list[float]] | None:
    """Percentile contrast limits per channel from a pyramid level small enough to read whole."""
    if level.size > CONTRAST_MAX_ELEMENTS or level.size == 0:
        return None
    values = np.asarray(level.compute())
    stacks = np.moveaxis(values, channel_index, 0) if channel_index is not None else values[np.newaxis]
    limits: list[list[float]] = []
    for stack in stacks:
        low, high = np.percentile(stack, CONTRAST_PERCENTILES)
        if not np.isfinite([low, high]).all() or high <= low:
            return None
        limits.append([float(low), float(high)])
    return limits


def scene_transforms(node: nodes.Node, placement: Placement, axes: list[rfc8.Axis]) -> list[dict[str, Any]]:
    """Transforms an ancestor's ``scene`` declares for this node, padded to the node's axes by name.

    Only scale and translation (or a sequence of them) are applied; anything
    else is reported and skipped. The scene's output coordinate system names
    the axes the transform acts on; other axes of the node get identity.
    """
    result: list[dict[str, Any]] = []
    names = [axis.name.lower() for axis in axes]
    for collection, relative in placement.ancestors:
        scene = collection.attributes.get("scene")
        if not isinstance(scene, dict):
            continue
        systems = {system.get("id"): [axis["name"].lower() for axis in system.get("axes", [])] for system in scene.get("coordinateSystems", [])}
        for transform in scene.get("coordinateTransformations", []):
            target = transform.get("input", {}).get("path", {})
            target = target.get("path") if isinstance(target, dict) else target
            if target is None or posixpath.normpath(target) != relative:
                continue
            scene_axes = systems.get(transform.get("output", {}).get("id"), names[-2:])
            padded = _pad_transform(transform, scene_axes, names)
            if padded is None:
                warnings.warn(f"napari-sp-ops skips a {transform.get('type')} scene transform on {node.name}", stacklevel=2)
            else:
                result.append(padded)
    return result


def _pad_transform(transform: dict[str, Any], scene_axes: list[str], names: list[str]) -> dict[str, Any] | None:
    kind = transform.get("type")
    if kind == "sequence":
        parts = [_pad_transform(part, scene_axes, names) for part in transform.get("transformations", [])]
        return None if any(part is None for part in parts) else {"type": "sequence", "transformations": parts}
    if kind not in ("scale", "translation") or len(transform[kind]) != len(scene_axes):
        return None
    identity = 1.0 if kind == "scale" else 0.0
    values = [identity] * len(names)
    for axis, value in zip(scene_axes, transform[kind], strict=True):
        if axis in names:
            values[names.index(axis)] = value
    return {"type": kind, kind: values}


def read_multiscale(node: nodes.Node, placement: Placement | None = None) -> LayerData:
    """Return layer data for a multiscale node with sp-ops names, colormaps and placement.

    Singleton axes other than ``y`` and ``x`` are squeezed. Images with a
    channel axis split into one layer per channel. A three- or four-long
    ``uint8`` channel axis opens as one RGB layer with the channel moved
    last. RFC-8 ``labels`` open as a hidden labels layer.
    """
    placement = placement or Placement()
    group = node.group
    attributes = node.attributes
    axes = rfc8.multiscale_axes(group)
    levels = rfc8.multiscale_levels(group)
    pyramid = [da.from_zarr(group[path]) for path, _ in levels]
    transforms = list(levels[0][1])
    transforms.extend(scene_transforms(node, placement, axes))

    squeezed = [index for index, axis in enumerate(axes) if pyramid[0].shape[index] == 1 and not axis.is_yx]
    if squeezed:
        pyramid = [da.squeeze(level, axis=tuple(squeezed)) for level in pyramid]
        transforms = _drop_axes(transforms, squeezed)
        axes = [axis for index, axis in enumerate(axes) if index not in squeezed]

    kind = classify(node, axes, pyramid[0])
    channel_index = _channel_index(axes)
    sp_ops: dict[str, Any] = {**placement.metadata, "path": node.path, "node": node.name}
    metadata: dict[str, Any] = {"metadata": {"sp-ops": sp_ops}}
    layer_type = "image"

    if kind == "labels":
        layer_type = "labels"
        metadata["name"] = placement.name_prefix + node.name
        metadata["visible"] = False if placement.visible is None else placement.visible
        sp_ops["label_kind"] = attributes.get("sp-ops:label_kind")
    elif kind == "rgb":
        metadata["name"] = placement.name_prefix + node.name
        metadata["rgb"] = True
        pyramid = [da.moveaxis(level, channel_index, -1) for level in pyramid]
        transforms = _drop_axes(transforms, [channel_index])
        axes = [axis for index, axis in enumerate(axes) if index != channel_index]
    elif channel_index is None:
        channel_list = channels_module.parse_channels(attributes, 1)
        metadata["name"] = placement.name_prefix + channel_list[0].name
        metadata["colormap"] = channels_module.colormaps(channel_list)[0]
        sp_ops["channel"] = channel_list[0].to_dict()
        limits = contrast_limits(pyramid[-1], None)
        if limits:
            metadata["contrast_limits"] = limits[0]
    else:
        count = pyramid[0].shape[channel_index]
        channel_list = channels_module.parse_channels(attributes, count)
        metadata["channel_axis"] = channel_index
        metadata["name"] = [placement.name_prefix + channel.name for channel in channel_list]
        metadata["colormap"] = channels_module.colormaps(channel_list)
        metadata["metadata"] = [{"sp-ops": {**sp_ops, "channel": channel.to_dict()}} for channel in channel_list]
        limits = contrast_limits(pyramid[-1], channel_index)
        if limits:
            metadata["contrast_limits"] = limits
        transforms = _drop_axes(transforms, [channel_index])
        axes = [axis for index, axis in enumerate(axes) if index != channel_index]

    if placement.visible is not None and "visible" not in metadata:
        metadata["visible"] = placement.visible
    metadata.update(_transform_metadata(transforms, len(axes)))
    if placement.translation_yx is not None:
        metadata["translate"][-2] += placement.translation_yx[0]
        metadata["translate"][-1] += placement.translation_yx[1]
    metadata["axis_labels"] = tuple(axis.name.lower() for axis in axes)
    if any(axis.unit for axis in axes):
        metadata["units"] = tuple(axis.unit for axis in axes)
    if "affine" in metadata:
        warnings.warn(f"napari-sp-ops passes the rotation or shear of {node.name} to napari as an affine", stacklevel=2)
    return pyramid, metadata, layer_type
