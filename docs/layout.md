# Layout

One screen is one OME-Zarr store whose root is an [RFC-8](https://ngff.openmicroscopy.org/rfc/8/index.html) `collection` node. Its children are plate collections, each carrying the RFC-8 `plate` attribute. A plate collection describes one physical plate at one processing stage, so the same physical plate MAY appear several times, for example as `plate1_raw` and `plate1_processed`. Plate collections MAY live inside the screen store or be referenced by path from another store. Below the plate the hierarchy is fixed:

```text
screen → plate (one per physical plate and stage) → well → modality → tiles → tile → [round →] channel
                                                                     └──────→ merged
```

| Level | Names used in the examples | What the level holds | Requirement |
| --- | --- | --- | --- |
| screen | the store root | plate collections and screen-wide tables such as the library | MUST |
| plate | `plate1_raw`, `plate1_intermediate`, `plate1_processed` | one physical plate at one stage: as acquired, pipeline intermediates, or analysis-ready | MUST have at least one per physical plate; `raw` SHOULD, `intermediate` MAY, `processed` MAY |
| well | `A/1` | one well, RFC-8 `well` attribute | MUST have at least one per plate collection |
| modality | `iss`, `pheno` | in situ sequencing (ISS) or phenotyping; each has its own tile grid | MUST have at least one per well |
| tiles | `tiles` | the tile layout and one collection per field of view | MUST in `raw`; MAY in `processed` |
| tile | `tile0`, `tile1`, ... | one field of view | MUST have at least one under `tiles` |
| merged | `merged` | the stitched well image and what was computed on it | MAY; a processed modality MUST have `tiles` or `merged` or both |
| round | `round0`, `round1`, ... | one imaging pass; present in `raw` only when the modality has more than one round | MUST in `raw` when the modality has more than one round |
| channel | `channel0`, `channel1`, ... | one wavelength; present only in `raw`, where channels are not yet aligned | MUST in `raw` |

The requirements follow the two real datasets behind this specification. The scallops pipeline keeps raw tiles, intermediates, and processed outputs, and everything downstream can be regenerated from the raw tiles, so `raw` is a SHOULD. The public Biohub submission holds only a stitched image and labels per well, no tiles and no raw data, and is still a usable store, so `processed`, `tiles`, and `merged` are each a MAY with the constraint that at least one image level exists.

Names carry no meaning. A reader identifies each level from the node's attributes (`plate`, `well`, `acquisition` from RFC-8; `sp-ops:plate`, `sp-ops:stage`, `sp-ops:modality`, `sp-ops:tiles`, `sp-ops:tile`, `sp-ops:merged`, `sp-ops:axis` from this specification, see [](extension.md)). The names above are the recommended defaults. Tables are processed data and MAY be split or merged and stored at other levels than shown, see [](features.md#merged-and-split-tables).

## Directory tree

The running example is a screen with one plate, wells `A/1`, `A/2`, `A/3`, nine ISS rounds whose cycle labels are 1 to 10 without 6, and one phenotyping round. The ISS grid has four tiles per well and the phenotyping grid sixteen, because the two modalities were imaged at different magnifications.

```text
screen.zarr/
├── zarr.json                      # collection; sp-ops:spec
├── library                        # table: barcode → perturbation, one row per guide
├── plate1_raw/                    # collection; plate; sp-ops:plate "plate1"; sp-ops:stage "raw"
│   └── A/1/                       # collection; well {row A, column 1}
│       ├── iss/                   # collection; sp-ops:modality "iss"
│       │   └── tiles/             # collection; sp-ops:tiles
│       │       ├── layout         # shapes: one polygon per tile, in the well frame
│       │       ├── tile0/         # collection; sp-ops:tile {"index": 0}
│       │       │   ├── round0/    # collection; acquisition iss-c1; sp-ops:axis {round, index 0, value 1}
│       │       │   │   ├── channel0   # multiscale (y, x); sp-ops:axis {c, index 0}; sp-ops:channels [DAPI]
│       │       │   │   ├── channel1   # A
│       │       │   │   ├── channel2   # G
│       │       │   │   ├── channel3   # C
│       │       │   │   └── channel4   # T
│       │       │   ├── round1/    # acquisition iss-c2, same shape
│       │       │   └── ... round8/    # acquisition iss-c10
│       │       └── tile1/ ... tile3/
│       └── pheno/                 # collection; sp-ops:modality "pheno"; acquisition pheno
│           └── tiles/
│               ├── layout
│               └── tile0/ ... tile15/
│                   ├── channel0   # multiscale (y, x) DAPI
│                   └── channel1 ... channel4
├── plate1_intermediate/           # collection; plate; sp-ops:stage "intermediate"; contents tool-defined
│   └── A/1/iss/tiles/tile0/...    # e.g. illumination_corrected, log_filtered, std, max
└── plate1_processed/              # collection; plate; sp-ops:stage "processed"
    ├── wells                      # shapes: one polygon per well (optional)
    └── A/1/
        ├── iss/
        │   ├── tiles/
        │   │   ├── layout
        │   │   ├── tile_features  # table: one row per ISS tile
        │   │   ├── tile0/
        │   │   │   ├── image      # multiscale (round, c, y, x); registered across rounds and channels
        │   │   │   └── peaks      # points: candidate spots
        │   │   └── tile1/ ... tile3/
        │   └── merged/            # collection; sp-ops:merged
        │       ├── image          # multiscale (round, c, y, x); stitched, well frame
        │       └── reads          # points: decoded barcode reads
        └── pheno/
            ├── tiles/
            │   ├── layout
            │   ├── tile_features  # table: one row per phenotyping tile
            │   └── tile0/ ... tile15/
            │       └── image      # multiscale (c, y, x)
            └── merged/
                ├── image          # multiscale (c, y, x); registered to iss/merged/image
                ├── nuclei         # labels (y, x)
                ├── cells          # labels (y, x)
                ├── cytosol        # labels (y, x)
                ├── nuclei_features    # table: one row per nucleus label, with cell_label
                └── cells_features     # table: one row per cell label
```

## Screen and plates

The root `zarr.json` holds the screen collection. Each plate collection declares its rows, columns, and acquisitions. One acquisition is one imaging pass, so ISS contributes one acquisition per round and phenotyping one per round (one, in the example). Plate collections of the same physical plate declare the same acquisitions, so a processed image can reference them without opening the raw plate.

```json
{
  "zarr_format": 3,
  "node_type": "group",
  "attributes": {
    "ome": {
      "version": "0.x",
      "type": "collection",
      "name": "screen",
      "attributes": {"sp-ops:spec": {"version": "0.2.0-draft"}},
      "nodes": [
        {"type": "sp-ops:table", "name": "library", "path": {"type": "zarr", "path": "./library"}},
        {"type": "collection", "name": "plate1_raw", "path": {"type": "zarr", "path": "./plate1_raw"},
         "attributes": {"sp-ops:plate": {"id": "plate1"}, "sp-ops:stage": "raw"}},
        {"type": "collection", "name": "plate1_intermediate", "path": {"type": "zarr", "path": "./plate1_intermediate"},
         "attributes": {"sp-ops:plate": {"id": "plate1"}, "sp-ops:stage": "intermediate"}},
        {"type": "collection", "name": "plate1_processed", "path": {"type": "zarr", "path": "./plate1_processed"},
         "attributes": {"sp-ops:plate": {"id": "plate1"}, "sp-ops:stage": "processed"}}
      ]
    }
  }
}
```

A plate collection, abbreviated:

```json
{
  "type": "collection",
  "name": "plate1_raw",
  "attributes": {
    "sp-ops:plate": {"id": "plate1"},
    "sp-ops:stage": "raw",
    "plate": {
      "rows": [{"id": "A"}],
      "columns": [{"id": "1"}, {"id": "2"}, {"id": "3"}],
      "acquisitions": [
        {"id": "iss-c1", "name": "ISS cycle 1"},
        {"id": "iss-c2", "name": "ISS cycle 2"},
        {"id": "iss-c10", "name": "ISS cycle 10"},
        {"id": "pheno", "name": "phenotyping"}
      ]
    }
  },
  "nodes": [
    {"type": "collection", "name": "A/1", "path": {"type": "zarr", "path": "./A/1"},
     "attributes": {"well": {"row": {"id": "A"}, "column": {"id": "1"}}}}
  ]
}
```

A plate collection MAY omit wells it has no data for. The stages `raw`, `intermediate`, `processed` are recommendations; a screen MAY include any subset of them, or other stages, as long as each plate collection declares `sp-ops:stage`.

## Modalities, tiles, and merged images

A modality collection has two children. `tiles/` holds the `layout` shapes element and one `tile<i>` collection per field of view. `merged/` holds the stitched image and everything computed on it. The two are kept apart because a tile image is a few thousand pixels on a side and a merged image is a few hundred thousand, so they need different chunking, sharding, and pyramid depth, and a viewer opens one or the other. The ISS and phenotyping grids are independent: they may differ in tile count, size, and overlap.

`layout` has one polygon per tile in the well coordinate system and a `tile` column holding the tile index.

```json
{"type": "collection", "name": "iss", "path": {"type": "zarr", "path": "./iss"},
 "attributes": {"sp-ops:modality": "iss"}}
```

```json
{"type": "collection", "name": "tiles", "path": {"type": "zarr", "path": "./tiles"},
 "attributes": {"sp-ops:tiles": {"layout": {"id": "layout"}}}}
```

```json
{"type": "collection", "name": "tile0", "path": {"type": "zarr", "path": "./tile0"},
 "attributes": {"sp-ops:tile": {"index": 0}}}
```

```json
{"type": "collection", "name": "merged", "path": {"type": "zarr", "path": "./merged"},
 "attributes": {"sp-ops:merged": {"source": [{"id": "tile0"}, {"id": "tile1"}, {"id": "tile2"}, {"id": "tile3"}]}}}
```

## Rounds and channels in `raw`

A raw tile holds one collection per round when the modality has several rounds, and one multiscale per channel. Each channel image has its own coordinate system, because channels are not assumed to be aligned at acquisition. The round index and its acquisition label are metadata, not part of the name:

```json
{
  "type": "collection",
  "name": "round0",
  "path": {"type": "zarr", "path": "./round0"},
  "attributes": {
    "acquisition": {"id": "iss-c1"},
    "sp-ops:axis": {"name": "round", "index": 0, "value": 1}
  }
}
```

```json
{
  "type": "multiscale",
  "name": "channel0",
  "path": {"type": "zarr", "path": "./channel0"},
  "attributes": {
    "sp-ops:axis": {"name": "c", "index": 0},
    "sp-ops:channels": [{"name": "DAPI", "role": "nuclear"}],
    "coordinateSystems": [{"id": "px", "axes": [{"name": "y", "type": "space", "unit": "micrometer"}, {"name": "x", "type": "space", "unit": "micrometer"}]}]
  }
}
```

A raw channel array keeps the axes the instrument produced. A phenotyping channel acquired as a z-stack is `(z, y, x)`; its processed counterpart is `(y, x)` after projection or reconstruction.

## Images in `processed`

A processed tile or merged collection holds one `image` per modality with aligned channels and, for multi-round modalities, registered rounds stacked along `round`. Array axes are drawn from `round, t, c, z, y, x` in that fixed order, and an axis of length one is omitted. The common shapes are:

| Data | Axes |
| --- | --- |
| ISS tile or merged image | `(round, c, y, x)` |
| Phenotyping image, one round | `(c, y, x)` |
| Phenotyping with several staining rounds | `(round, c, y, x)` |
| Phenotyping live imaging | `(t, c, y, x)` or `(t, y, x)` |
| Phenotyping with z | `(c, z, y, x)` |

`round` and `t` are distinct. `round` is a repeated imaging pass over the same fixed cells. `t` is elapsed time in a live acquisition.

Rounds are always stacked, so that a reader gets one array per modality. Provenance is kept per slice: `sp-ops:rounds` lists, for every index along `round`, the acquisition it came from, which is what a batch-effect analysis needs. `sp-ops:channels` names every channel and gives it a role (`nuclear`, `base`, `stain`, `other`). When channel identity differs between rounds, as with successive antibody stains, `sp-ops:channels` is one array per round, and a round with fewer channels than the others is padded with entries whose `name` is `null`. `sp-ops:registration` names the anchor channel and the reference image.

```json
{
  "type": "multiscale",
  "name": "image",
  "path": {"type": "zarr", "path": "./image"},
  "attributes": {
    "sp-ops:rounds": [
      {"index": 0, "acquisition": {"id": "iss-c1"}},
      {"index": 1, "acquisition": {"id": "iss-c2"}},
      {"index": 8, "acquisition": {"id": "iss-c10"}}
    ],
    "sp-ops:channels": [
      {"name": "DAPI", "role": "nuclear"},
      {"name": "A", "role": "base"}, {"name": "G", "role": "base"},
      {"name": "C", "role": "base"}, {"name": "T", "role": "base"}
    ],
    "sp-ops:registration": {"anchor": "DAPI", "reference": {"id": "round0"}},
    "coordinateSystems": [{"id": "tile", "axes": [
      {"name": "round", "type": "array"}, {"name": "c", "type": "channel"},
      {"name": "y", "type": "space", "unit": "micrometer"}, {"name": "x", "type": "space", "unit": "micrometer"}]}]
  }
}
```

## Registration

Three registration steps produce the processed images. Each is a coordinate transformation between RFC-5 coordinate systems, stored in the `scene` attribute of the collection that contains both endpoints.

1. Channels within a round. Every raw channel of a round is aligned to the anchor channel. The result is one `(c, y, x)` slice.
2. Rounds within a tile. Each round's anchor channel is registered to the reference round (`round0` by default), and the transform is applied to all channels of that round. The rounds are resampled onto the reference round's grid and stacked along `round`.
3. Modalities within a well. The phenotyping merged image is registered to the ISS merged image through a channel both share. The two modalities are usually acquired at different magnifications, so this transform is an affine that includes a scale, and both merged images keep their native pixel size. Both then share the `well` coordinate system, whose unit is micrometres, and that is where cells segmented on phenotyping data receive ISS reads.

The anchor is the nuclear channel when one is present. It is not always present: phase or brightfield phenotyping has no nuclear stain, and some protocols omit DAPI from ISS cycles after the first. `sp-ops:registration` therefore names the anchor explicitly, and MAY name it per round when it differs.

Tile images map into the `well` frame by the stitching transform stored on the modality collection. Merged images are already in the `well` frame.

```json
"scene": {
  "coordinateSystems": [{"id": "well", "axes": [
    {"name": "y", "type": "space", "unit": "micrometer"},
    {"name": "x", "type": "space", "unit": "micrometer"}]}],
  "coordinateTransformations": [
    {"type": "affine", "affine": [[1, 0, 0], [0, 1, 0]],
     "input": {"id": "tile", "path": {"type": "zarr", "path": "./tiles/tile0/image"}},
     "output": {"id": "well"}},
    {"type": "affine", "affine": [[1, 0, 0], [0, 1, 2048]],
     "input": {"id": "tile", "path": {"type": "zarr", "path": "./tiles/tile1/image"}},
     "output": {"id": "well"}}
  ]
}
```

The affine values are illustrative. This is a `byDimension` transform in practice, because `round` and `c` pass through unchanged; the example shows the spatial part only.

```{mermaid}
flowchart LR
  c0["plate1_raw/.../round0/channel0..4"] -->|"1. channel alignment"| r0["round0 slice"]
  c1["plate1_raw/.../round1/channel0..4"] -->|"1."| r1["round1 slice"]
  r0 -->|"2. round registration, reference round0"| img["plate1_processed/.../iss/tiles/tile0/image (round, c, y, x)"]
  r1 -->|"2."| img
  img -->|"stitching"| issm["iss/merged/image, well frame"]
  ph["plate1_processed/.../pheno/tiles/tile0..15/image"] -->|"stitching"| phm["pheno/merged/image"]
  phm -->|"3. modality registration, with scale"| issm
```

## Reading the store with SpatialData

The whole store, or any sub-collection, opens as one hierarchical `SpatialData` object whose element names are the Zarr paths. Every leaf group carries `spatialdata_attrs.element_type`, so the reader finds elements by recursion and needs no fixed `images/`, `labels/` layout.

```text
SpatialData object
├── library: [Table] AnnData (4211, 0)
├── plate1_raw/  (A/1, A/2, A/3)
├── plate1_intermediate/  (A/1, A/2, A/3)
└── plate1_processed/
    ├── wells: [Shapes] GeoDataFrame (3, 2)
    └── A/1/
        ├── iss/
        │   ├── tiles/
        │   │   ├── layout: [Shapes] GeoDataFrame (4, 2)
        │   │   ├── tile_features: [Table] AnnData (4, 4)
        │   │   ├── tile0/
        │   │   │   ├── image: [Image] DataArray[round,c,y,x] (9, 5, 2048, 2048)
        │   │   │   └── peaks: [Points] DataFrame (70112, 3)
        │   │   └── tile1/ ... tile3/
        │   └── merged/
        │       ├── image: [Image] DataArray[round,c,y,x] (9, 5, 4096, 4096)
        │       └── reads: [Points] DataFrame (612340, 5)
        └── pheno/
            ├── tiles/
            │   ├── layout: [Shapes] GeoDataFrame (16, 2)
            │   ├── tile_features: [Table] AnnData (16, 4)
            │   └── tile0/ ... tile15/
            └── merged/
                ├── image: [Image] DataArray[cyx] (5, 8192, 8192)
                ├── nuclei: [Labels2D] DataArray[yx] (8192, 8192)
                ├── cells: [Labels2D] DataArray[yx] (8192, 8192)
                ├── cytosol: [Labels2D] DataArray[yx] (8192, 8192)
                ├── nuclei_features: [Table] AnnData (28102, 1400)
                └── cells_features: [Table] AnnData (27488, 1400)
with coordinate systems:
    ▸ 'plate1_processed/A/1/well', with elements: iss/merged/image, pheno/merged/image, nuclei, cells, cytosol, reads, layout
    ▸ 'plate1_processed/A/1/iss/tiles/tile0', with elements: iss/tiles/tile0/image, iss/tiles/tile0/peaks
```

```python
import spatialdata as sd

sdata = sd.read_zarr("screen.zarr")
well = sdata["plate1_processed/A/1"]                # sub-view, prefix stripped
iss = well["iss/merged/image"]                      # DataArray (round, c, y, x)
dapi_round0 = iss.sel(round=0, c="DAPI")

raw_tile = sdata["plate1_raw/A/1/iss/tiles/tile0"]
channels = [raw_tile[f"round0/channel{i}"] for i in range(5)]   # unaligned, own coordinate systems
aligned = sd.rasterize(channels, target_coordinate_system="plate1_processed/A/1/iss/tiles/tile0")
```

The axis names `round` and `t`, the `sel` by channel name, and the hierarchical reader are assumptions listed in [](design-decisions.md#assumptions).
