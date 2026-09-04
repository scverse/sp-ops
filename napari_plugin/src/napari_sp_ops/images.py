"""Turn one RFC-8 multiscale group into napari image, labels or RGB layer data."""

import warnings
from dataclasses import dataclass, field
from typing import Any

import dask.array as da
import numpy as np
import zarr

from napari_sp_ops import channels as channels_module
from napari_sp_ops import rfc8, upstream

LayerData = tuple[list[da.Array], dict[str, Any], str]

RGB_LENGTHS = {3, 4}


@dataclass
class Placement:
    """Extra layer-level context a collection passes down to its leaves."""

    name_prefix: str = ""
    translation: list[float] | None = None
    visible: bool | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


def classify(group: zarr.Group, axes: list[rfc8.Axis], array: da.Array) -> str:
    """Return ``rgb``, ``labels`` or ``image`` for a multiscale group."""
    channel_index = _channel_index(axes)
    if channel_index == len(axes) - 1 and array.shape[channel_index] in RGB_LENGTHS and array.dtype == np.uint8:
        return "rgb"
    if "labels" in rfc8.ome_attributes(group):
        return "labels"
    return "image"


def _channel_index(axes: list[rfc8.Axis]) -> int | None:
    for index, axis in enumerate(axes):
        if axis.type == "channel":
            return index
    return None


def _drop_axes(transforms: list[dict[str, Any]], indices: list[int]) -> list[dict[str, Any]]:
    for index in sorted(indices, reverse=True):
        transforms = [upstream.remove_axis_from_transform(transform, index) for transform in transforms]
    return transforms


def _scale_and_translate(transforms: list[dict[str, Any]], ndim: int) -> tuple[list[float], list[float]]:
    if not transforms:
        return [1.0] * ndim, [0.0] * ndim
    affine = upstream.transforms_to_affine(transforms, None)
    matrix = affine.affine_matrix
    linear = matrix[:-1, :-1]
    if not np.allclose(linear, np.diag(np.diag(linear))):
        warnings.warn("napari-sp-ops keeps only scale and translation of a dataset transform; rotation or shear is dropped", stacklevel=2)
    return np.diag(linear).tolist(), matrix[:-1, -1].tolist()


def read_multiscale(group: zarr.Group, placement: Placement | None = None) -> LayerData:
    """Return layer data for a multiscale group with sp-ops names, colormaps and placement.

    Singleton axes other than ``y`` and ``x`` are squeezed. Images with a
    channel axis split into one layer per channel. A trailing three- or
    four-long ``uint8`` channel axis opens as one RGB layer. RFC-8 ``labels``
    open as a hidden labels layer.
    """
    placement = placement or Placement()
    attributes = rfc8.ome_attributes(group)
    axes = rfc8.multiscale_axes(group)
    datasets = rfc8.ome(group)["multiscales"][0]["datasets"]
    pyramid = [da.from_zarr(group[dataset["path"]]) for dataset in datasets]
    transforms = rfc8.dataset_transforms(group)
    if placement.translation is not None:
        transforms.append({"type": "translation", "translation": list(placement.translation)})

    squeezed = [index for index, axis in enumerate(axes) if pyramid[0].shape[index] == 1 and not axis.is_yx]
    if squeezed:
        pyramid = [da.squeeze(level, axis=tuple(squeezed)) for level in pyramid]
        transforms = _drop_axes(transforms, squeezed)
        axes = [axis for index, axis in enumerate(axes) if index not in squeezed]

    kind = classify(group, axes, pyramid[0])
    channel_index = _channel_index(axes)
    name = rfc8.node_name(group)
    metadata: dict[str, Any] = {"metadata": {"sp-ops": {**placement.metadata, "path": str(group.store_path), "node": name}}}
    layer_type = "image"

    if kind == "labels":
        layer_type = "labels"
        metadata["name"] = placement.name_prefix + name
        metadata["visible"] = False if placement.visible is None else placement.visible
        metadata["metadata"]["sp-ops"]["label_kind"] = attributes.get("sp-ops:label_kind")
    elif kind == "rgb":
        metadata["name"] = placement.name_prefix + name
        metadata["rgb"] = True
        transforms = _drop_axes(transforms, [channel_index])
        axes = axes[:channel_index]
    elif channel_index is None:
        channel_list = channels_module.parse_channels(attributes, 1)
        metadata["name"] = placement.name_prefix + channel_list[0].name
        metadata["colormap"] = channels_module.colormaps(channel_list)[0]
        metadata["metadata"]["sp-ops"]["channel"] = channel_list[0].to_dict()
    else:
        count = pyramid[0].shape[channel_index]
        channel_list = channels_module.parse_channels(attributes, count)
        metadata["channel_axis"] = channel_index
        metadata["name"] = [placement.name_prefix + channel.name for channel in channel_list]
        metadata["colormap"] = channels_module.colormaps(channel_list)
        base = metadata.pop("metadata")["sp-ops"]
        metadata["metadata"] = [{"sp-ops": {**base, "channel": channel.to_dict()}} for channel in channel_list]
        transforms = _drop_axes(transforms, [channel_index])
        axes = [axis for index, axis in enumerate(axes) if index != channel_index]

    if placement.visible is not None and "visible" not in metadata:
        metadata["visible"] = placement.visible
    scale, translate = _scale_and_translate(transforms, len(axes))
    metadata["scale"] = scale
    metadata["translate"] = translate
    metadata["axis_labels"] = tuple(axis.name.lower() for axis in axes)
    if any(axis.unit for axis in axes):
        metadata["units"] = tuple(axis.unit for axis in axes)
    return pyramid, metadata, layer_type
