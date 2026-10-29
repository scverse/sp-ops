"""biohub_example: a merged-only submission, written as one `processed` plate.

The delivery is an OME-NGFF 0.5 HCS plate plus loose Parquet, CSV and YAML
sidecars: one stitched image and a stack of segmentations per well, no tiles and
no raw data. It is the complement of experimentC, which exercises `raw` and
nothing else.

Two corrections to the source metadata make this a rewrite rather than a
relabelling:

* All twelve label groups declare 0.65 um per pixel; they are written at 0.325.
  The source's own ``op_units_correction`` note records that the image was
  corrected from 0.65 to 0.325 and the labels were not. That the labels sit on
  the image grid is confirmed twice: the tail of every ``cell_uid`` in the
  excerpt is a ``cell_seg`` pixel value, and membrane_prediction is enriched
  2.6x on cell_seg boundaries at 1:1 but flat under a 2x reading.
* Axes are squeezed and lowercased from the source's ``T, C, Z, Y, X`` with
  singleton T and Z to ``(c, y, x)`` for the image and ``(y, x)`` for labels.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable

import numpy as np
import pandas as pd
import zarr

from ..converter import ScreenConverter
from ..rfc8 import (acquisitions, edge, labels_source, node, relationships,
                    set_ome, well_attribute)

log = logging.getLogger("spops")

STAGE = "processed"
WELL_ROW, WELL_COLUMNS = "A", ["1", "2", "3"]
DATA_WELL = "1"                  # the only well the delivered excerpt has pixels for
CROP_OFFSET_UM = 15600.0         # the excerpt's origin in the well frame
ISS_CYCLES = list(range(1, 11))  # experimental_metadata.yaml: iss.cycles = 10

# channels_metadata on the source plate, in array order. `role` is this
# specification's four-value vocabulary; it cannot express label-free or
# predicted, so two label-free and two predicted channels land on the nearest
# fit. See Q20.
CHANNELS = [
    ("Phase2D", "other"),
    ("Focus3D", "other"),
    ("GFP", "stain"),
    ("mCherry", "stain"),
    ("nuclei_prediction", "nuclear"),
    ("membrane_prediction", "other"),
]
RGBA = [{"name": c, "role": "other"} for c in ("R", "G", "B", "A")]

# The eleven compartments that are not the cell, for the suggested membership
# edges. Nothing records compartment membership, so only a spatial join
# recovers it. See Q23.
SUBCELLULAR = [
    "nuclear_seg", "gfp_seg", "mcherry_seg", "nucleoli_phase2d_seg",
    "nucleoli_focus3d_seg", "phase2d_tubular_seg", "focus3d_tubular_seg",
    "phase2d_vesicular_seg", "phase2d_vesicular_dark_seg",
    "focus3d_vesicular_seg", "focus3d_vesicular_dark_seg",
]

IMAGE_ID = "pheno-merged-image"


class BiohubConverter(ScreenConverter):
    name = "biohub_example"
    plate_id = "Biohub_OPS0001"
    pixel_size_um = 0.325          # corrected; the label groups declare 0.65
    cs_id = "merged"
    max_chunk = 1024
    shard_factor = 2048

    # ------------------------------------------------------------------- load

    def load(self) -> None:
        d = self.sources["dataset"]
        self.src = zarr.open_group(store=str(d / "Biohub_OPS0001.zarr"), mode="r")
        self.sidecar = d / "Biohub_OPS0001"
        self.label_root = f"{WELL_ROW}/{DATA_WELL}/0/labels"

        # The only classification that matches the pixels: a segmentation carries
        # an `ome` attribute, an RGBA rendering does not. The source's own
        # `ome.labels` (12) disagrees with a sibling `labels` key (13) and with
        # 15 groups on disk, so neither declared list is read.
        self.seg_labels, self.overlays = [], []
        for name in sorted(self.src[self.label_root].group_keys()):
            attrs = dict(self.src[f"{self.label_root}/{name}"].attrs)
            (self.seg_labels if "ome" in attrs else self.overlays).append(name)
        log.info("source: %d label images, %d RGBA overlays",
                 len(self.seg_labels), len(self.overlays))

        self.n_levels = len(
            self.src[f"{WELL_ROW}/{DATA_WELL}/0"].attrs["ome"]["multiscales"][0]["datasets"])

    def _levels(self, path: str, squeeze_c: bool) -> list[np.ndarray]:
        """Read a source pyramid, dropping the singleton T and Z axes."""
        out = []
        for i in range(self.n_levels):
            a = np.asarray(self.src[f"{path}/{i}"])[0, :, 0]   # (T,C,Z,Y,X) -> (C,Y,X)
            out.append(a[0] if squeeze_c else a)
        return out

    def _rgba(self, name: str) -> np.ndarray:
        """A rendering, not a label: RGBA, channel last in the source, and
        transposed here because the axis order is fixed. See Q29."""
        return np.asarray(self.src[f"{self.label_root}/{name}/0"]).transpose(2, 0, 1)

    # --------------------------------------------------------- screen and plate

    def write_screen_elements(self, root: zarr.Group) -> Iterable[dict]:
        lib = pd.read_csv(self.sidecar / "metadata" / "perturbation_library.csv",
                          dtype=str)
        obs = lib.set_index("barcode", drop=False)
        for c in ("role", "control_type", "gene_symbol", "perturbation_id",
                  "protospacer_adjacent_motif"):
            obs[c] = obs[c].fillna("").astype("category")
        yield self._table(root, "library", obs)

        # feature_definitions.csv defines 2935 features, but no table in this
        # dataset holds their values. There is no slot for a feature dictionary
        # without a matrix, so it is written as a screen level table. See Q24.
        fd = pd.read_csv(self.sidecar / "metadata" / "feature_definitions.csv",
                         dtype=str)
        fd_obs = fd.set_index("feature_id", drop=False).fillna("")
        for c in ("feature_type", "compartment", "channel", "unit", "software",
                  "version"):
            fd_obs[c] = fd_obs[c].astype("category")
        yield self._table(root, "feature_definitions", fd_obs)
        log.info("library: %d guides | feature_definitions: %d features",
                 len(obs), len(fd_obs))

    def _table(self, parent: zarr.Group, name: str, obs: pd.DataFrame) -> dict:
        # This dataset has no list valued columns, and coercing its object
        # columns would change the on-disk encoding for no reason.
        return self.table(parent, name, obs, stringify=False,
                          clear_index_name=False, element_id=name)

    def screen_attributes(self) -> dict:
        return {"sp-ops:relationships": relationships([
            edge(f"plate1_{STAGE}/cells", "library",
                 on={"left": "barcode", "right": "barcode"}, cardinality="n:1"),
        ])}

    def write_plates(self) -> Iterable[dict]:
        yield self.plate(
            f"plate1_{STAGE}", stage=STAGE, rows=[WELL_ROW],
            # All three wells are declared; only A/1 has pixels to hold.
            columns=WELL_COLUMNS,
            acquisitions=acquisitions(ISS_CYCLES, pheno_first=True),
            edges=[edge("cells",
                        f"{WELL_ROW}/{DATA_WELL}/pheno/merged/cell_seg",
                        on={"left": "label", "right": "value"}, cardinality="1:1")],
            children=self._plate_children)

    def _plate_children(self, plate: zarr.Group) -> list[dict]:
        # One merged table for the whole plate: cell_data.parquet covers all
        # three wells while the excerpt carries pixels for one, so a per-well
        # table would strand two thirds of the rows. `label` is derived by
        # splitting `cell_uid`, which has no label column of its own. See Q22.
        cells = pd.read_parquet(self.sidecar / "cell_data.parquet")
        cells["label"] = cells["cell_uid"].str.rsplit("_", n=1).str[-1].astype(np.int64)
        cells["well"] = cells["well_row"] + "/" + cells["well_col"].astype(str)
        cells["modality"] = "pheno"
        cells["site"] = cells["tile"]
        obs = cells.set_index("cell_uid", drop=False)
        for c in ("plate", "well_row", "well", "modality", "barcode",
                  "perturbation_id"):
            obs[c] = obs[c].astype("category")
        cells_node = self._table(plate, "cells", obs)
        log.info("cells: %d barcode-assigned cells over %d wells, %d source tiles",
                 len(obs), obs.well.nunique(), obs.site.nunique())

        return [cells_node, self._write_well(plate)]

    # ------------------------------------------------------------------- well

    def _write_well(self, plate: zarr.Group) -> dict:
        """Written without the `well()` helper.

        The well's `scene` needs one transform per merged element, so the names
        of the children are an input to the well's own attributes. `collection()`
        computes children before attributes, not after, so this level is spelled
        out instead.
        """
        self._merged_names: list[str] = []
        self._iss_names: list[str] = []
        group = self.group(plate, f"{WELL_ROW}/{DATA_WELL}")
        pheno_node = self.modality(group, "pheno", acquisition="pheno",
                                   children=self._pheno_children)
        iss_node = self.modality(group, "iss", children=self._iss_children)

        # Every merged element sits on one grid, offset from the well origin by
        # the excerpt's crop. The spatial part only, as the specification's
        # examples do.
        transforms = [
            {"type": "translation",
             "translation": [CROP_OFFSET_UM, CROP_OFFSET_UM],
             "input": {"id": self.cs_id,
                       "path": {"type": "zarr", "path": f"{prefix}/{n}"}},
             "output": {"id": "well"}}
            for prefix, names in (("./pheno/merged", self._merged_names),
                                  ("./iss/merged", self._iss_names))
            for n in names
        ]
        # There is no cell_label column anywhere, so compartment membership is a
        # spatial join a reader would have to compute: status "suggested".
        edges = [edge(f"pheno/merged/{n}", "pheno/merged/cell_seg",
                      method="sjoin", on={"predicate": "within"},
                      status="suggested")
                 for n in SUBCELLULAR if n in self.seg_labels]

        attrs = dict(well_attribute(WELL_ROW, DATA_WELL))
        attrs["scene"] = {
            "coordinateSystems": [{"id": "well", "axes": [
                {"name": "y", "type": "space", "unit": "micrometer"},
                {"name": "x", "type": "space", "unit": "micrometer"}]}],
            "coordinateTransformations": transforms,
        }
        attrs["sp-ops:relationships"] = relationships(edges)
        set_ome(group, "collection", f"{WELL_ROW}/{DATA_WELL}",
                attributes=attrs, nodes=[pheno_node, iss_node])
        log.info("well %s/%s: %d transforms, %d suggested membership edges",
                 WELL_ROW, DATA_WELL, len(transforms), len(edges))

        return node("collection", f"{WELL_ROW}/{DATA_WELL}",
                    f"./{WELL_ROW}/{DATA_WELL}",
                    attributes=well_attribute(WELL_ROW, DATA_WELL))

    def _pheno_children(self, pheno: zarr.Group) -> list[dict]:
        return [self.merged(pheno, source=[], children=self._pheno_merged)]

    def _pheno_merged(self, merged: zarr.Group) -> list[dict]:
        levels = self._levels(f"{WELL_ROW}/{DATA_WELL}/0", squeeze_c=False)
        nodes = [self.image(
            merged, "image", pyramid=levels, axis_names=["c", "y", "x"],
            attributes={"sp-ops:channels": [{"name": n, "role": r}
                                            for n, r in CHANNELS]},
            element_id=IMAGE_ID)]
        log.info("pheno/merged/image: %s %s, %d levels",
                 levels[0].shape, levels[0].dtype, self.n_levels)

        for name in self.seg_labels:
            nodes.append(self.labels(
                merged, name,
                pyramid=self._levels(f"{self.label_root}/{name}", squeeze_c=True),
                axis_names=["y", "x"], attributes=labels_source(IMAGE_ID)))
        log.info("pheno/merged: %d label images written at %s um/px "
                 "(source declared 0.65)", len(self.seg_labels), self.pixel_size_um)

        for name in self.overlays:
            if name.startswith("iss_"):
                continue
            nodes.append(self.image(
                merged, name, pyramid=[self._rgba(name)],
                axis_names=["c", "y", "x"],
                attributes={"sp-ops:channels": RGBA}))

        self._merged_names = [n["name"] for n in nodes]
        return nodes

    def _iss_children(self, iss: zarr.Group) -> list[dict]:
        return [self.merged(iss, source=[], children=self._iss_merged)]

    def _iss_merged(self, merged: zarr.Group) -> list[dict]:
        # Only two RGBA renderings survive of ten declared ISS cycles: no
        # per-cycle image, no reads, no peaks.
        nodes = [self.image(merged, name, pyramid=[self._rgba(name)],
                            axis_names=["c", "y", "x"],
                            attributes={"sp-ops:channels": RGBA})
                 for name in self.overlays if name.startswith("iss_")]
        self._iss_names = [n["name"] for n in nodes]
        log.info("iss/merged: %d RGBA overlays, no image, no reads", len(nodes))
        return nodes
