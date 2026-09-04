"""Write a small sp-ops screen with zarr v3 and RFC-8 group metadata.

The layout mirrors the two conformant example stores: a processed plate whose
merged collection holds an image with singleton T and Z axes, RFC-8 labels and
an RGBA overlay, and a raw plate whose tiles hold one multiscale per channel.
"""

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import zarr

OME_VERSION = "0.6-rfc8-draft"
SPEC_VERSION = "0.2.0-draft"

TCZYX = [
    {"name": "T", "type": "time", "unit": "second"},
    {"name": "C", "type": "channel"},
    {"name": "Z", "type": "space", "unit": "micrometer"},
    {"name": "Y", "type": "space", "unit": "micrometer"},
    {"name": "X", "type": "space", "unit": "micrometer"},
]
YX = [
    {"name": "y", "type": "space", "unit": "micrometer"},
    {"name": "x", "type": "space", "unit": "micrometer"},
]
ZYX = [{"name": "z", "type": "space", "unit": "micrometer"}, *YX]
YXC = [*YX, {"name": "c", "type": "channel"}]


def node(node_type: str, name: str, attributes: dict | None = None) -> dict:
    descriptor: dict = {"type": node_type, "name": name, "path": {"type": "zarr", "path": f"./{name}"}}
    if attributes:
        descriptor["attributes"] = attributes
    return descriptor


def write_collection(group_dir: Path, name: str, nodes: list[dict], attributes: dict | None = None) -> None:
    group_dir.mkdir(parents=True, exist_ok=True)
    ome: dict = {"version": OME_VERSION, "type": "collection", "name": name, "nodes": nodes}
    if attributes:
        ome["attributes"] = attributes
    payload = {"zarr_format": 3, "node_type": "group", "attributes": {"ome": ome}}
    (group_dir / "zarr.json").write_text(json.dumps(payload, indent=2))


def write_multiscale(
    group_dir: Path,
    array: np.ndarray,
    axes: list[dict],
    scale: list[float],
    attributes: dict,
    coordinate_system: str,
    translation: list[float] | None = None,
) -> None:
    group_dir.mkdir(parents=True, exist_ok=True)
    zarr.create_array(store=str(group_dir / "0"), data=array, chunks=array.shape)
    transforms: list[dict] = [{"type": "scale", "scale": scale}]
    if translation is not None:
        transforms.append({"type": "translation", "translation": translation})
    multiscales = [{"version": OME_VERSION, "axes": axes, "datasets": [{"path": "0", "coordinateTransformations": transforms}]}]
    ome = {
        "version": OME_VERSION,
        "type": "multiscale",
        "multiscales": multiscales,
        "attributes": {**attributes, "coordinateSystems": [{"id": coordinate_system, "axes": axes}]},
    }
    payload = {"zarr_format": 3, "node_type": "group", "attributes": {"ome": ome}}
    (group_dir / "zarr.json").write_text(json.dumps(payload, indent=2))


@dataclass(frozen=True)
class SyntheticScreen:
    root: Path
    plate_processed: Path
    well: Path
    modality: Path
    merged: Path
    image: Path
    labels: Path
    overlay: Path
    plate_raw: Path
    raw_tile: Path
    raw_round: Path
    raw_channel_yx: Path
    raw_channel_zyx: Path


def _processed_plate(plate: Path) -> None:
    well_attrs = {"well": {"row": {"id": "A"}, "column": {"id": "1"}}}
    write_collection(
        plate,
        "plate1_processed",
        [node("collection", "A/1", well_attrs)],
        {
            "sp-ops:plate": {"id": "plate1"},
            "sp-ops:stage": "processed",
            "plate": {"rows": [{"id": "A"}], "columns": [{"id": "1"}], "acquisitions": [{"id": "pheno", "name": "phenotyping"}]},
        },
    )
    well = plate / "A" / "1"
    write_collection(well, "A/1", [node("collection", "pheno")], well_attrs)
    modality = well / "pheno"
    write_collection(modality, "pheno", [node("collection", "merged")], {"sp-ops:modality": "pheno", "acquisition": {"id": "pheno"}})
    merged = modality / "merged"
    write_collection(
        merged,
        "merged",
        [node("multiscale", "image"), node("multiscale", "cells"), node("multiscale", "overlay")],
        {"sp-ops:merged": {"source": []}},
    )
    rng = np.random.default_rng(0)
    write_multiscale(
        merged / "image",
        rng.random((1, 2, 1, 16, 16), dtype=np.float32),
        TCZYX,
        [1.0, 1.0, 2.0, 0.325, 0.325],
        {"sp-ops:channels": [{"name": "GFP", "role": "stain"}, {"name": "nuclei_prediction", "role": "other"}]},
        "well",
        translation=[0.0, 0.0, 0.0, 15600.0, 15600.0],
    )
    write_multiscale(
        merged / "cells",
        rng.integers(0, 5, (1, 1, 1, 16, 16), dtype=np.int32),
        TCZYX,
        [1.0, 1.0, 2.0, 0.65, 0.65],
        {
            "labels": {"source": [{"path": {"type": "zarr", "path": "../image"}, "id": "pheno-merged-image"}]},
            "sp-ops:label_kind": "biological",
        },
        "well",
        translation=[0.0, 0.0, 0.0, 15600.0, 15600.0],
    )
    write_multiscale(
        merged / "overlay",
        rng.integers(0, 255, (16, 16, 4), dtype=np.uint8),
        YXC,
        [1.0, 1.0, 1.0],
        {"labels": {"source": [{"id": "pheno-merged-image"}]}, "sp-ops:label_kind": "overlay"},
        "well",
    )


def _raw_plate(plate: Path) -> None:
    well_attrs = {"well": {"row": {"id": "A"}, "column": {"id": "1"}}}
    acquisitions = [{"id": "iss-c1", "name": "ISS cycle 1"}, {"id": "iss-c2", "name": "ISS cycle 2"}, {"id": "pheno", "name": "phenotyping"}]
    write_collection(
        plate,
        "plate1_raw",
        [node("collection", "A/1", well_attrs)],
        {"sp-ops:plate": {"id": "plate1"}, "sp-ops:stage": "raw", "plate": {"rows": [{"id": "A"}], "columns": [{"id": "1"}], "acquisitions": acquisitions}},
    )
    well = plate / "A" / "1"
    write_collection(well, "A/1", [node("collection", "iss"), node("collection", "pheno")], well_attrs)
    rng = np.random.default_rng(1)

    iss = well / "iss"
    write_collection(iss, "iss", [node("collection", "tiles")], {"sp-ops:modality": "iss"})
    write_collection(iss / "tiles", "tiles", [node("collection", "tile0", {"sp-ops:tile": {"index": 0}})], {"sp-ops:tiles": {}})
    tile = iss / "tiles" / "tile0"
    rounds = []
    for index, cycle in enumerate((1, 2)):
        rounds.append(node("collection", f"round{index}", {"acquisition": {"id": f"iss-c{cycle}"}, "sp-ops:axis": {"name": "round", "index": index, "value": cycle}}))
    write_collection(tile, "tile0", rounds, {"sp-ops:tile": {"index": 0}})
    channels = [("DAPI", "nuclear"), ("Cy3", "base")]
    for round_node in rounds:
        round_dir = tile / round_node["name"]
        channel_nodes = []
        for index, (name, role) in enumerate(channels):
            attrs = {"sp-ops:axis": {"name": "c", "index": index}, "sp-ops:channels": [{"name": name, "role": role}]}
            channel_nodes.append(node("multiscale", f"channel{index}", attrs))
            write_multiscale(round_dir / f"channel{index}", rng.integers(0, 4000, (16, 16), dtype=np.uint16), YX, [1.3, 1.3], attrs, f"iss-{round_node['name']}-c{index}")
        write_collection(round_dir, round_node["name"], channel_nodes, round_node["attributes"])

    pheno = well / "pheno"
    write_collection(pheno, "pheno", [node("collection", "tiles")], {"sp-ops:modality": "pheno", "acquisition": {"id": "pheno"}})
    write_collection(pheno / "tiles", "tiles", [node("collection", "tile0", {"sp-ops:tile": {"index": 0}})], {"sp-ops:tiles": {}})
    attrs = {"sp-ops:axis": {"name": "c", "index": 0}, "sp-ops:channels": [{"name": "AF750", "role": "stain"}]}
    write_collection(pheno / "tiles" / "tile0", "tile0", [node("multiscale", "channel0", attrs)], {"sp-ops:tile": {"index": 0}})
    write_multiscale(pheno / "tiles" / "tile0" / "channel0", rng.integers(0, 4000, (2, 16, 16), dtype=np.uint16), ZYX, [1.5, 0.325, 0.325], attrs, "pheno-c0")


def build_synthetic_screen(root: Path) -> SyntheticScreen:
    """Write the screen under ``root`` and return the paths a test needs."""
    plate_processed = root / "plate1_processed"
    plate_raw = root / "plate1_raw"
    write_collection(
        root,
        "screen",
        [
            node("collection", "plate1_processed", {"sp-ops:plate": {"id": "plate1"}, "sp-ops:stage": "processed"}),
            node("collection", "plate1_raw", {"sp-ops:plate": {"id": "plate1"}, "sp-ops:stage": "raw"}),
        ],
        {"sp-ops:spec": {"version": SPEC_VERSION}},
    )
    _processed_plate(plate_processed)
    _raw_plate(plate_raw)
    merged = plate_processed / "A" / "1" / "pheno" / "merged"
    raw_tile = plate_raw / "A" / "1" / "iss" / "tiles" / "tile0"
    return SyntheticScreen(
        root=root,
        plate_processed=plate_processed,
        well=plate_processed / "A" / "1",
        modality=plate_processed / "A" / "1" / "pheno",
        merged=merged,
        image=merged / "image",
        labels=merged / "cells",
        overlay=merged / "overlay",
        plate_raw=plate_raw,
        raw_tile=raw_tile,
        raw_round=raw_tile / "round0",
        raw_channel_yx=raw_tile / "round0" / "channel0",
        raw_channel_zyx=plate_raw / "A" / "1" / "pheno" / "tiles" / "tile0" / "channel0",
    )
