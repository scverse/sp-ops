# Design decisions

This page records the twelve design decisions behind the sp-ops specification for optical pooled screening (OPS) data. It fixes the running example, settles each open question, and lists every extension identifier the specification introduces. Every other page follows the names, numbers, and rules given here. When a page and this page disagree, this page wins and the page is wrong.

Statements on this page fall into three status categories. Normative requirements of this specification use MUST, SHOULD, and MAY in the sense of RFC 2119. Existing behaviour is what released software and released standards do today, namely Open Microscopy Environment Next-Generation File Format (OME-NGFF) 0.5 high-content screening (HCS) metadata, spatialdata v0.8.0, and the ngio table specifications. Proposals depend on unreleased work and carry a "Status" note or an inline "(proposed)" tag. The unreleased dependencies are OME-NGFF request for comments 8 (RFC-8, collections, status D1), RFC-5 (coordinate transformations, status S4), hierarchical SpatialData (an experimental branch), and element relationships (two hackathon prototypes). Other acronyms used below are in situ sequencing (ISS), sequencing by synthesis (SBS), field of view (FOV), quality control (QC), application programming interface (API), and 4′,6-diamidino-2-phenylindole (DAPI), the nuclear stain of the running example. The three status categories are defined once on the [overview page](overview.md#every-statement-is-normative-existing-behaviour-or-a-proposal).

## Running example

Every page uses one dataset. Real values come from two sources. The scallops pipeline layout gives the well name, the ISS cycle set, the `t` folder labels, and the parquet and label names. The audit of a public Biohub OPS submission gives the well set, the pixel size, the label dtypes, the stitched array shape, and the library size. Everything else is illustrative and exists only to make shapes concrete. The plate identifier of the audited submission is withheld because this repository is public.

:::{admonition} Status of the `t` values
:class: warning
The scallops layout stores per-cycle affine transforms under `iss-transforms-t0/A1/t=2` to `t=10`, and the registered store is named `iss-registered-t0.zarr`. The set `2, 3, 4, 5, 7, 8, 9, 10` equals the cycle set minus cycle 1. The values may therefore be cycle indices relative to a reference cycle rather than fixation timepoints. This specification follows the draft and treats them as fixation timepoints. Pages MUST call the `t` values "folder labels from the scallops layout", not measured timepoints, until the scallops authors confirm their meaning.
:::

### Plate, wells, tiles, timepoints, and cycles

| Item | Value | Status |
| --- | --- | --- |
| Store name | `ops_plate.zarr` | illustrative; the real identifier is withheld |
| Plate name in metadata | `ops_plate` | illustrative |
| Rows and columns | row `A`; columns `1`, `2`, `3` | real (audit) |
| Wells | `A/1`, `A/2`, `A/3` | real (audit); `A/1` is the scallops well `A1` |
| Profile | `tiled` | illustrative; the real submission is `stitched` with one field per well, shown in the [stitched profile example](#stitched-profile-example) of D2 |
| Tiles per well | `f0`, `f1`, `f2`, `f3` in a 2 by 2 grid | illustrative |
| Fixation timepoints `t` | `2, 3, 4, 5, 7, 8, 9, 10` | folder labels (scallops); see the warning above |
| ISS cycles `r` | `1, 2, 3, 4, 5, 7, 8, 9, 10` (no cycle 6) | real (scallops `A1-1.ome.tiff` to `A1-10.ome.tiff`) |
| Phenotypic rounds per `t` | one, named `pheno` | draft |
| Acquisition identifiers | `iss-t<t>-r<r>` and `pheno-t<t>`; `merged-t<t>` only in the stitched profile example | this specification |
| Anchor acquisition per `t` | `iss-t<t>-r1` | default rule of this specification |

### Channels, images, and labels

| Item | Value | Status |
| --- | --- | --- |
| ISS channels | `DAPI, A, G, C, T`; roles `nuclear, base, base, base, base` | set from the draft; order is this specification's choice |
| Phenotypic channels | `DAPI, GFP, stain_3, stain_4, stain_5` | `DAPI` from the draft; `GFP` from the real label `gfp_seg`; the rest illustrative |
| Real stitched channel count | 6 | real (audit) |
| Tile image shape and dtype | `(5, 2048, 2048)` float32, three pyramid levels | illustrative size and levels; float32 is the real stitched dtype |
| Real stitched array | `[1, 6, 1, 104650, 105144]` float32, five pyramid levels | real (audit) |
| Pixel size | 0.325 micrometre per pixel | real (audit) |
| Label images | `nuclear_seg`, `cell_seg`, int32 | real names and dtype (audit) |
| Other real labels | `gfp_seg`, `iss_gene_image`, `grid_overlay` | real (audit); shown only in the [stitched profile example](#stitched-profile-example) of D2 |
| Objects in one 2048 by 2048 window | 828 nuclei, 859 cells | real (audit) |
| Spot images | `spots/max` `(4, 2048, 2048)`, `spots/std` `(1, 2048, 2048)` | names from scallops `A1-max`, `A1-std`; shapes illustrative |

### Points, shapes, tables, and coordinate systems

| Item | Value | Status |
| --- | --- | --- |
| Points | `spots/peaks`, `bases` per tile and timepoint | names from scallops `A1-peaks.parquet` and `reads/bases/A1.parquet` |
| `bases` columns | `x`, `y`, `read`, `r`, `base`, `cell_label`; shape `(612340, 6)` per (tile, `t`) | columns from D11; the example omits the SHOULD intensity columns because the sources do not name them; row count illustrative |
| `spots/peaks` columns | `x`, `y`, `read`; shape `(70112, 3)` per (tile, `t`) | columns from D11; `cell_label` is absent because the `spots/peaks` to `cell_seg` edge is `suggested`, not `computed` (D9); row count illustrative |
| Shapes | `tiles`, `footprints` per well; `cell_bbox` per tile and timepoint; `wells` at the plate root | `cell_bbox` from scallops `cell/A1-objects.parquet`; the rest this specification |
| Tables per well | `images`, `fov_features`, `cells`, `reads` | this specification; `reads` from scallops `reads/reads/A1.parquet` |
| Tables at the plate root | `well_features`, `library` | `library` columns `barcode`, `perturbation_id`, `role`, `control_type` are real (OPS standard) |
| Library size | 4211 single guide RNAs (sgRNAs) over 1052 `perturbation_id` | real (audit) |
| `perturbation_id` examples | `AARS1`, `ADSS2`, `GET3` | real current gene symbols (audit) |
| Retired symbols in the real cell table | `AARS`, `ADSS`, `ASNA1` | real (audit); 32 such orphans per dataset |
| CellProfiler feature count | 1400 | illustrative |
| Read join column | `read`, uint64 | real (scallops) |
| Coordinate systems | `A/1/f0/t2` (one per tile and `t`), `A/1` (well), `plate` (optional) | this specification |
| Registration affine values | see D5 | illustrative |

### Derived counts

```text
acquisitions per plate      80      8 timepoints x (9 ISS cycles + 1 phenotypic round)
acquisition image elements  320     4 tiles x 80 acquisitions, per well
registered frames per well  32      4 tiles x 8 timepoints
elements per (tile, t)      17      9 iss/r<k>, pheno, spots/max, spots/std, spots/peaks,
                                    bases, nuclear_seg, cell_seg, cell_bbox
elements per well           550     4 x 8 x 17 + tiles, footprints, images, fov_features, cells, reads
elements per plate          1653    3 x 550 + wells, well_features, library
cells per well              27488   32 frames x 859 cells (859 reused as an average)
```

### Hierarchical element paths

The full list for well `A/1`, tile `f0`, timepoint `t2`. The other seven timepoints, three tiles, and two wells repeat the pattern. Types are spatialdata models.

```text
library                        table    plate root, condition_table
well_features                  table    plate root, feature_table (MAY)
wells                          shapes   plate root, one rectangle per well (MAY)
A/1/tiles                      shapes   4 rows, one per tile
A/1/footprints                 shapes   320 rows, one per acquisition image element
A/1/images                     table    320 rows, condition_table, annotates footprints
A/1/fov_features               table    320 rows, feature_table, annotates footprints (MAY)
A/1/cells                      table    27488 rows, feature_table, annotates every cell_seg
A/1/reads                      table    generic_table, one row per read
A/1/f0/t2/iss/r1               image    (5, 2048, 2048), reference image for this frame
A/1/f0/t2/iss/r2               image
A/1/f0/t2/iss/r3               image
A/1/f0/t2/iss/r4               image
A/1/f0/t2/iss/r5               image
A/1/f0/t2/iss/r7               image
A/1/f0/t2/iss/r8               image
A/1/f0/t2/iss/r9               image
A/1/f0/t2/iss/r10              image
A/1/f0/t2/pheno                image    (5, 2048, 2048)
A/1/f0/t2/spots/max            image    (4, 2048, 2048), derived
A/1/f0/t2/spots/std            image    (1, 2048, 2048), derived
A/1/f0/t2/spots/peaks          points
A/1/f0/t2/bases                points
A/1/f0/t2/nuclear_seg          labels   (2048, 2048) int32
A/1/f0/t2/cell_seg             labels   (2048, 2048) int32
A/1/f0/t2/cell_bbox            shapes   859 rectangles, index equals the label value
A/1/f0/t2/reg/iss/r1           image    resampled product (MAY), see D6
```

## Decisions

### D1. The extension prefix is `sp-ops`, with nine attribute keys and three node types

#### Decision

The extension prefix is `sp-ops`. Every non-core attribute key and node type introduced by this specification MUST be spelled `sp-ops:<key>`. The specification introduces no path type and no coordinate transformation type. The complete list is the [extension key registry](#extension-key-registry) at the end of this page.

The nine attribute keys are `sp-ops:spec`, `sp-ops:acquisitions`, `sp-ops:tile`, `sp-ops:tileLayout`, `sp-ops:timepoint`, `sp-ops:registration`, `sp-ops:channels`, `sp-ops:table`, and `sp-ops:relationships`. The three node types are `sp-ops:shapes`, `sp-ops:points`, and `sp-ops:table`. Each node type maps onto one spatialdata model, namely `ShapesModel`, `PointsModel`, and `TableModel`. Images and label images use the core RFC-8 `multiscale` node type with the core `labels` attribute.

`sp-ops:acquisitions` on the plate is the single source of truth for what each acquisition is. Each entry carries the core acquisition `id`, `kind` (`iss`, `pheno`, or `merged`, defined in D2), `t`, `r` (null for `pheno` and `merged`), and `anchor` (boolean). Image nodes carry only the core `acquisition` reference. There is no per-image copy of `kind`, `t`, or `r`.

`sp-ops:channels` on an image is an array of objects `{"name", "role", "base"}`. `role` MUST be one of `nuclear`, `base`, `stain`, `other`. `base` MUST be present only when `role` is `base` and MUST be one of `A`, `C`, `G`, `T`. Channel names are the depositor's names. `sp-ops:channels` is authoritative for channel identity; the `c` coordinate of the spatialdata image MUST carry the same names in the same order. When a store also carries other channel-name metadata, such as the `channels_metadata` sibling key found in the audited store, a validator SHOULD warn on disagreement. The channels of one acquisition MUST include exactly one channel with `role: "nuclear"`, because that channel anchors the registration (D5). When the channels are separate elements (D4 rule 3), exactly one of those elements carries it. Derived images such as `spots/max` MAY have none.

Where the keys live depends on the layout. In an OME-NGFF 0.5 store, prefixed keys sit in the Zarr group `attributes` object as siblings of `ome`. The audited store already does this with `channels_metadata`. In an RFC-8 document they sit inside the node's `attributes` object (proposed). The spelling is identical in both places.

#### Rationale

- RFC-8 reserves unprefixed identifiers for the core and lets prefixed identifiers be introduced without an RFC. Its own examples use project names as prefixes (`fractal:well`, `mobie:grid`, `neuroglancer:shader`, `webknossos:settings`). A reader who sees `sp-ops:tile` can find this specification.
- Structured channel roles keep depositor names. Reserved names would force a depositor whose nuclear stain is Hoechst to rename it, and cannot describe the real six-channel stitched store.
- One plate-level acquisition array mirrors how RFC-8 splits acquisition definitions (plate) from membership (node), and removes a drift risk between per-image copies.
- Every element is a Zarr group written by spatialdata, so the core `zarr` path type reaches every node.

#### Rejected alternatives

- Prefix `scverse`. Other scverse projects would need the same prefix for their own keys, and a reader cannot find the defining specification from the prefix alone.
- Prefix `ops`. It names a technique, and several OPS pipelines exist.
- Prefix `ome`. RFC-8 reserves it for official extensions.
- A `sp-ops:acquisition` key inside core `Acquisition` objects. RFC-8 lists only `id` and `name` for that interface with no "additional keys MAY" clause, and its `fractal:well` example describes a sibling prefixed key, not injection.
- Channel roles by reserved names (`DAPI` MUST be the anchor). Not extensible and wrong for depositors with other nuclear stains.
- A `sp-ops:parquet` path type. spatialdata writes shapes and points inside Zarr groups, so it is never needed.

#### Depends on

RFC-8 for node types and for prefixed keys inside `attributes`. None for prefixed sibling keys in a 0.5 store, which is a normative rule of this specification resting on the observed behaviour of the audited store.

#### Example

Image group attributes in the 0.5 layout. Core keys are under `ome`; extension keys are siblings.

```json
{
  "zarr_format": 3,
  "node_type": "group",
  "attributes": {
    "ome": {
      "version": "0.5",
      "multiscales": [ { "axes": [ {"name": "c", "type": "channel"},
                                   {"name": "y", "type": "space", "unit": "micrometer"},
                                   {"name": "x", "type": "space", "unit": "micrometer"} ],
                         "datasets": [ { "path": "0",
                                         "coordinateTransformations": [ {"type": "scale", "scale": [1.0, 0.325, 0.325]} ] } ] } ]
    },
    "sp-ops:tile": {"index": 0},
    "sp-ops:channels": [
      {"name": "DAPI", "role": "nuclear"},
      {"name": "A", "role": "base", "base": "A"},
      {"name": "G", "role": "base", "base": "G"},
      {"name": "C", "role": "base", "base": "C"},
      {"name": "T", "role": "base", "base": "T"}
    ]
  }
}
```

### D2. Plates and wells stay valid OME-NGFF 0.5; the RFC-8 view is a sidecar

#### Decision

An acquisition is one pass of the microscope over the plate that produces one image per tile. For OPS it is the triple (kind, `t`, `r`). An ISS acquisition is one cycle `r` at one fixation timepoint `t`. A phenotypic acquisition is the phenotypic round at one `t`. The core acquisition name MUST be `iss-t<t>-r<r>` or `pheno-t<t>`. Registered or resampled images stored next to their source acquisitions are derived nodes, not acquisitions (D6).

The one exception is the third kind, `merged`. A `merged` acquisition is one stitched image per well whose channels were assembled after registration from the ISS cycles and the phenotypic round of one `t`. Its name MUST be `merged-t<t>`, its `r` MUST be null, and its channels follow D1, so ISS-derived channels carry `role: "other"`. The kind exists because a 0.5 well needs a `well.images[].acquisition` for every image, and the audited Biohub store has exactly one such merged image per well. The scallops layout describes the same product as the `stitch` output, "pheno + iss image". A writer MUST NOT use `merged` when the raw acquisitions are stored; it then stores the product under `reg/` (D6).

Two profiles exist. A writer MUST use the `tiled` profile when a well has more than one tile. A writer MUST use the `stitched` profile when each acquisition yields one image per well. The profile is declared in `sp-ops:spec.profile`.

Mapping (a), OME-NGFF 0.5 HCS metadata as it exists today. This is existing behaviour plus the following rules.

1. The plate group carries `ome.plate` with `rows`, `columns`, `wells`, `name`, `field_count`, and `acquisitions`. There MUST be one `acquisitions` entry per (kind, `t`, `r`) triple, with `name` equal to the acquisition name above. `maximumfieldcount` MUST equal the number of `well.images` entries that the acquisition contributes to one well. That is the number of tiles per well when its channels are stacked, and tiles times channels when its channels are separate elements (D4 rule 3). Acquisition ids SHOULD run from 0 in order of `t`, then the ISS cycles by `r`, then the phenotypic round. In the running example `iss-t2-r1` is 0 and `pheno-t2` is 9.
2. `field_count` MUST equal the largest number of `well.images` entries in any well. In the 0.5 example, two acquisitions with `maximumfieldcount` 2 give `field_count` 4 and a well with four images. The running example therefore has `field_count` 320 and `maximumfieldcount` 4.
3. The well group carries `ome.well.images`, one entry per image, with `path` and the integer `acquisition`. Because `path` MUST NOT contain `/`, the image is a direct child of the well, named by the flattening rule of D10. The name is `<tile>-t<t>-iss-r<r>` or `<tile>-t<t>-pheno` in the `tiled` profile (`f0-t2-iss-r1`) and `t<t>-iss-r<r>`, `t<t>-pheno`, or `t<t>-merged` in the `stitched` profile. A `stitched` well with exactly one acquisition MAY name its image `0`, which is the real Biohub store (see the [stitched profile example](#stitched-profile-example)).
4. Labels live at `<image>/labels/<name>` under the image they were computed from, as 0.5 requires.
5. Points, shapes, tables, derived images (`spots/max`, `spots/std`), and resampled images (`reg/`, D6) have no home in 0.5 HCS metadata. They are extra groups in the well or plate, named by the flattening rule of D10. They are not `well.images` entries, so `field_count` counts acquisition images only, and a 0.5 reader does not see them. OME-NGFF 0.5 does not forbid extra groups. The audited submission passed the OPS validator with images only; extra groups have not been tested against it.

Mapping (b), RFC-8 collections (proposed). A 0.5 `zarr.json` cannot also be an RFC-8 node, because both live under one `ome` key and 0.5 requires `"version": "0.5"` while an RFC-8 root node carries its own version. The RFC-8 view is therefore written as standalone JSON documents named `collection.json`, one at the plate root and one at each well root, using the RFC-8 path type `json`. The plate document references each well document by path. The well document inlines the tile collections (`sp-ops:tile`), each tile inlines one collection per `t` (`sp-ops:timepoint`), and each `t` collection lists its images, labels, points, shapes, and tables. This is the RFC-8 tall layout applied by tile, then by `t`. In the `stitched` profile the tile level is omitted; a well with one acquisition MAY list its image as a direct child (the RFC-8 wide layout). When RFC-8 is released, the same node objects MAY move into the `zarr.json` of nested Zarr groups (the collections layout of D10), and the sidecars become unnecessary.

Relationship between the two views. The 0.5 metadata is authoritative for rows, columns, wells, acquisitions, and image paths. The sidecar MUST agree with it, and a validator MUST report any disagreement.

#### Rationale

- The OPS data standard v0.1.0 pins OME-NGFF 0.5 for the image store, and the real submission is a valid 0.5 HCS plate. Breaking that to gain RFC-8 shape would make every submission invalid.
- The 0.5 rule that `well.images[].path` MUST NOT contain `/` is the one hard constraint. It forces a flat well and rules out tile folders in the 0.5 layout.
- The (kind, `t`, `r`) triple is what `well.images[].acquisition` needs to distinguish two cycles of one tile.
- Tall by tile keeps everything that shares one registration in one sub-collection. RFC-8 warns that the wide layout "can become cluttered when there are multiple acquisitions", and a well here has eighty.
- Inlining tile and `t` collections in the well document keeps the number of metadata requests small. RFC-8 notes that assembling a collection costs one request per path-referenced node.

#### Rejected alternatives

- Co-hosting `ome.plate` and an RFC-8 collection node in one `zarr.json`. Two `ome.version` values cannot coexist; neither a 0.5 reader nor an RFC-8 reader would accept the group.
- Tall by acquisition (the RFC's own tall example). It splits the images of one tile across eighty sub-collections and leaves the registration scene without a home.
- Acquisition equals `t` only, or `r` only. The first cannot separate two cycles of one tile; the second ignores that different `t` are different fixed cells.
- Tile folders (`A/1/f0/t2/iss/r1`) in the 0.5 layout. Invalid `well.images` paths.
- `field_count` equal to the number of tiles. Contradicts the 0.5 example, in which `field_count` counts all images in a well.

#### Depends on

None for mapping (a). RFC-8 for mapping (b); RFC-5 for the `scene` objects the well document carries (D5).

#### Example

Directory tree of the 0.5 layout, `tiled` profile. Only tile `f0` at `t2` is expanded.

```text
ops_plate.zarr/
├── zarr.json                        # ome.plate (0.5); sp-ops:spec, sp-ops:acquisitions, sp-ops:relationships
├── collection.json                  # (proposed) RFC-8 plate collection, references A/1/collection.json ...
├── library/                         # table, condition_table: barcode, perturbation_id, role, control_type
├── well_features/                   # table, feature_table, one row per well (MAY)
├── wells/                           # shapes, one rectangle per well in the plate frame (MAY)
└── A/
    ├── 1/
    │   ├── zarr.json                # ome.well.images: 320 entries; sp-ops:relationships
    │   ├── collection.json          # (proposed) RFC-8 well collection with tile and t collections, scenes
    │   ├── tiles/                   # shapes, 4 rows
    │   ├── footprints/              # shapes, 320 rows, well frame
    │   ├── images/                  # table, 320 rows, annotates footprints
    │   ├── fov_features/            # table, 320 rows, annotates footprints (MAY)
    │   ├── cells/                   # table, annotates every cell_seg in the well
    │   ├── reads/                   # table, one row per read
    │   ├── f0-t2-iss-r1/            # ome.multiscales (c, y, x); sp-ops:tile, sp-ops:channels
    │   ├── f0-t2-iss-r2/
    │   ├── ...                      # f0-t2-iss-r3 ... f0-t2-iss-r10 (no r6)
    │   ├── f0-t2-pheno/
    │   │   ├── zarr.json
    │   │   ├── 0/ 1/ 2/             # pyramid levels
    │   │   └── labels/
    │   │       ├── zarr.json        # ome.labels: ["nuclear_seg", "cell_seg"]
    │   │       ├── nuclear_seg/
    │   │       └── cell_seg/
    │   ├── f0-t2-spots-max/         # derived image
    │   ├── f0-t2-spots-std/
    │   ├── f0-t2-spots-peaks/       # points: x, y, read
    │   ├── f0-t2-bases/             # points: x, y, read, r, base, cell_label
    │   ├── f0-t2-cell_bbox/         # shapes
    │   ├── ...                      # f0-t3-... to f0-t10-...
    │   └── ...                      # f1-..., f2-..., f3-...
    ├── 2/
    └── 3/
```

Plate `zarr.json` in the 0.5 layout. Acquisition ids run from 0 to 79; the three shown are the first two cycles and the phenotypic round of `t2`.

```json
{
  "zarr_format": 3,
  "node_type": "group",
  "attributes": {
    "ome": {
      "version": "0.5",
      "plate": {
        "name": "ops_plate",
        "rows": [{"name": "A"}],
        "columns": [{"name": "1"}, {"name": "2"}, {"name": "3"}],
        "wells": [
          {"path": "A/1", "rowIndex": 0, "columnIndex": 0},
          {"path": "A/2", "rowIndex": 0, "columnIndex": 1},
          {"path": "A/3", "rowIndex": 0, "columnIndex": 2}
        ],
        "field_count": 320,
        "acquisitions": [
          {"id": 0, "name": "iss-t2-r1", "maximumfieldcount": 4},
          {"id": 1, "name": "iss-t2-r2", "maximumfieldcount": 4},
          {"id": 9, "name": "pheno-t2", "maximumfieldcount": 4}
        ]
      }
    },
    "sp-ops:spec": {"version": "0.1.0-draft", "profile": "tiled"},
    "sp-ops:acquisitions": [
      {"id": 0, "kind": "iss", "t": 2, "r": 1, "anchor": true},
      {"id": 1, "kind": "iss", "t": 2, "r": 2, "anchor": false},
      {"id": 9, "kind": "pheno", "t": 2, "r": null, "anchor": false}
    ]
  }
}
```

Well `A/1/zarr.json` in the 0.5 layout.

```json
{
  "zarr_format": 3,
  "node_type": "group",
  "attributes": {
    "ome": {
      "version": "0.5",
      "well": {
        "images": [
          {"path": "f0-t2-iss-r1", "acquisition": 0},
          {"path": "f0-t2-iss-r2", "acquisition": 1},
          {"path": "f0-t2-pheno", "acquisition": 9},
          {"path": "f1-t2-iss-r1", "acquisition": 0}
        ]
      }
    }
  }
}
```

:::{admonition} Status
:class: note
The next block depends on RFC-8 (status D1). `"0.x"` is the placeholder version RFC-8 uses in its own examples. In RFC-8 documents the acquisition, row, and column ids are strings, so `sp-ops:acquisitions[].id` carries the string id there and the integer id in the 0.5 `zarr.json`.
:::

Plate `collection.json` (proposed), stored next to the plate `zarr.json`.

```json
{
  "ome": {
    "version": "0.x",
    "type": "collection",
    "id": "plate",
    "name": "ops_plate",
    "attributes": {
      "plate": {
        "rows": [{"id": "A", "name": "A"}],
        "columns": [{"id": "1", "name": "1"}, {"id": "2", "name": "2"}, {"id": "3", "name": "3"}],
        "acquisitions": [
          {"id": "iss-t2-r1", "name": "ISS cycle 1, t=2"},
          {"id": "iss-t2-r2", "name": "ISS cycle 2, t=2"},
          {"id": "pheno-t2", "name": "phenotypic round, t=2"}
        ]
      },
      "sp-ops:spec": {"version": "0.1.0-draft", "profile": "tiled"},
      "sp-ops:acquisitions": [
        {"id": "iss-t2-r1", "kind": "iss", "t": 2, "r": 1, "anchor": true},
        {"id": "iss-t2-r2", "kind": "iss", "t": 2, "r": 2, "anchor": false},
        {"id": "pheno-t2", "kind": "pheno", "t": 2, "r": null, "anchor": false}
      ]
    },
    "nodes": [
      {"type": "collection", "id": "A-1", "name": "A/1", "path": {"type": "json", "path": "./A/1/collection.json"}},
      {"type": "collection", "id": "A-2", "name": "A/2", "path": {"type": "json", "path": "./A/2/collection.json"}},
      {"type": "collection", "id": "A-3", "name": "A/3", "path": {"type": "json", "path": "./A/3/collection.json"}},
      {"type": "sp-ops:table", "id": "library", "name": "library", "path": {"type": "zarr", "path": "./library"},
       "attributes": {"sp-ops:table": {"type": "condition_table", "tableVersion": "1", "granularity": "perturbation"}}},
      {"type": "sp-ops:shapes", "id": "wells", "name": "wells", "path": {"type": "zarr", "path": "./wells"}},
      {"type": "sp-ops:table", "id": "well_features", "name": "well_features", "path": {"type": "zarr", "path": "./well_features"},
       "attributes": {"sp-ops:table": {"type": "feature_table", "tableVersion": "1", "granularity": "well",
                                       "region": {"id": "wells"}}}}
    ]
  }
}
```

The well document is shown under D3 and D5.

#### Stitched profile example

The audited Biohub store is the `stitched` profile with one `merged` acquisition per well. Real values from the audit are the well set, the image name `0`, the array shape and dtype, the five pyramid levels, the pixel size, the label names and dtype, `field_count` 1, and the plate-level `channels_metadata` key. The audited array carries length-one `t` and `z` axes; a conformant writer stores it as `(c, y, x)`, that is `(6, 104650, 105144)` (D4). Everything else below is this specification or illustrative. The [hierarchy page](hierarchy.md) carries the full example.

```text
ops_plate.zarr/                          # real store shape; the identifier is withheld
├── zarr.json                            # ome.plate (0.5): row A, columns 1-3, field_count 1; channels_metadata (real);
│                                        # sp-ops:spec profile stitched, sp-ops:acquisitions (this specification)
├── collection.json                      # (proposed) RFC-8 plate collection, wide layout, plate scene (D5)
├── library/                             # table, condition_table (this specification; absent in the audited store)
└── A/
    ├── 1/
    │   ├── zarr.json                    # ome.well.images: [{"path": "0", "acquisition": 0}]
    │   ├── collection.json              # (proposed) RFC-8 well collection, one t collection, well scene
    │   └── 0/                           # the one merged image; element A/1/0 (D10 rule 6)
    │       ├── zarr.json                # ome.multiscales (c, y, x) at 0.325 um/px; sp-ops:channels, 6 entries
    │       ├── 0/ 1/ 2/ 3/ 4/           # five pyramid levels; level 0 is (6, 104650, 105144) float32 (real)
    │       └── labels/
    │           ├── zarr.json            # ome.labels: nuclear_seg, cell_seg, gfp_seg, iss_gene_image, grid_overlay, ...
    │           ├── nuclear_seg/         # int32, five levels; element A/1/nuclear_seg
    │           ├── cell_seg/            # element A/1/cell_seg
    │           ├── gfp_seg/
    │           ├── iss_gene_image/
    │           └── grid_overlay/
    ├── 2/                               # same shape as A/1
    └── 3/
```

Plate `zarr.json` attributes, 0.5 layout. The acquisition `t` is illustrative; the audit did not record it.

```json
{
  "ome": {
    "version": "0.5",
    "plate": {
      "name": "ops_plate",
      "rows": [{"name": "A"}],
      "columns": [{"name": "1"}, {"name": "2"}, {"name": "3"}],
      "wells": [
        {"path": "A/1", "rowIndex": 0, "columnIndex": 0},
        {"path": "A/2", "rowIndex": 0, "columnIndex": 1},
        {"path": "A/3", "rowIndex": 0, "columnIndex": 2}
      ],
      "field_count": 1,
      "acquisitions": [{"id": 0, "name": "merged-t2", "maximumfieldcount": 1}]
    }
  },
  "sp-ops:spec": {"version": "0.1.0-draft", "profile": "stitched"},
  "sp-ops:acquisitions": [{"id": 0, "kind": "merged", "t": 2, "r": null, "anchor": true}]
}
```

Well `A/1/zarr.json` attributes. 0.5 lets a well omit `acquisition` when the plate has one acquisition; this specification writes it (rule 3).

```json
{
  "ome": {"version": "0.5", "well": {"images": [{"path": "0", "acquisition": 0}]}}
}
```

Image `A/1/0/zarr.json`, extension key only. The channel names are illustrative because the audit did not record the contents of `channels_metadata`. The five phenotypic names are those of the running example; the sixth channel is ISS-derived and carries `role: "other"`.

```json
"sp-ops:channels": [
  {"name": "DAPI", "role": "nuclear"},
  {"name": "GFP", "role": "stain"},
  {"name": "stain_3", "role": "stain"},
  {"name": "stain_4", "role": "stain"},
  {"name": "stain_5", "role": "stain"},
  {"name": "iss_max", "role": "other"}
]
```

The image element is `A/1/0`, its labels are `A/1/nuclear_seg` and `A/1/cell_seg`, and its registered frame is `A/1/t2`, taken from the `t` of its acquisition entry (D5, D10). A `stitched` store that keeps its raw acquisitions instead names its images `t2-iss-r1` to `t2-pheno` and uses `kind` `iss` and `pheno` as in the `tiled` profile; the D10 mapping table lists both forms.

### D3. A tile is a collection of per-timepoint collections, and the layout is a shapes element

#### Decision

A tile is one stage position in one well, imaged across every acquisition. In the RFC-8 view it is a `collection` node marked with `sp-ops:tile` (proposed). In the hierarchical SpatialData view it is a name prefix, so `sdata["A/1/f0"]` is the tile (proposed). In the 0.5 layout it is the leading component of the flattened image name (`f0-t2-iss-r1`) and the `sp-ops:tile` attribute on each image group.

A tile contains one collection per fixation timepoint `t`. Each `t` collection holds the images, labels, points, shapes, and tables that describe the same fixed cells. In the running example these are the ISS cycles, the phenotypic image, the spot images and peaks, the base calls, the two label images, and the cell bounding boxes. Tables that describe cells or images across the whole well live at the well level (D4, D7).

Every well in the `tiled` profile MUST contain a shapes element named `tiles`, referenced from the well collection by `sp-ops:tileLayout` (proposed). The referenced node MUST be a child of the well collection. Its schema is normative.

| Column | Type | Requirement | Meaning |
| --- | --- | --- | --- |
| index | integer, unique | MUST | equals `sp-ops:tile.index` of the tile collection |
| `geometry` | Polygon, axis-aligned rectangle | MUST | the nominal tile extent in the well coordinate system, in micrometres |
| `tile` | string | MUST | equals the tile path component, `f0` |
| `grid_row`, `grid_col` | integer | SHOULD | position in the acquisition grid, zero-based |
| `stage_x`, `stage_y` | float, micrometre | MAY | raw stage coordinates as reported by the microscope |
| `n_timepoints` | integer | MAY | number of `t` collections under the tile |

`tiles` has exactly one row per tile, never one per acquisition. Per-acquisition stage jitter lives in the registration transformations (D5), not in duplicate layout rows. The element carries an identity transformation to the well coordinate system (D5). On disk it is a spatialdata shapes group. spatialdata v0.8.0 writes the geometry as `shapes.parquet` inside the group, readable with `geopandas.read_parquet`, with group attributes `encoding-type: "ngff:shapes"`, `axes`, `coordinateTransformations`, and `spatialdata_attrs` (existing behaviour, probe-verified).

Every well MUST also contain a shapes element named `footprints` with one axis-aligned rectangle per acquisition image element in the well, expressed in the well coordinate system. Its index is the integer `image_id`. The rectangle is the bounding box of the registered image extent. `footprints` is the region that the `images` and `fov_features` tables annotate (D4, D7), and it is the geometry from which D6 computes resampling boxes.

An ngio `roi_table` with the six required columns `x_micrometer`, `y_micrometer`, `z_micrometer`, `len_x_micrometer`, `len_y_micrometer`, `len_z_micrometer`, and index `FieldIndex` MAY be derived from `tiles` for Fractal tooling. The shapes element is authoritative.

#### Rationale

- The draft says each tile "is a hierarchical container of several images, labels, points, shapes". A collection per tile, with a collection per `t` inside, is that container.
- The draft asks for "a geoparquet file (SpatialData shapes) to describe the tile layout". A per-well shapes element with one row per tile is that file, and spatialdata can query it (`bounding_box_query`, `polygon_query`).
- spatialdata v0.8.0 accepts a table whose region is an image but `join_spatialelement_table` then raises `Element type Image2DModel not supported for join operation` (probe-verified). A shapes region can be joined. `footprints` stands in for the images.
- Footprints turn the registration result into geometry, so the intersection and union of D6 are shapely operations that read no pixels.

#### Rejected alternatives

- Tiles as 0.5 `well.images` entries only. A tile is a group of images plus derived data, which 0.5 cannot express.
- Forbidding points, shapes, and tables inside a tile. Contradicts the draft.
- An ngio `roi_table` as the primary layout. It duplicates geometry as number columns that spatialdata cannot query spatially.
- One `tiles` row per (tile, acquisition). Redundant geometry and a mixed instance key.
- Footprints per tile or per `t`. The per-well `images` table would then split into many tables.

#### Depends on

RFC-8 for the tile collection and `sp-ops:tileLayout`. Hierarchical SpatialData for `sdata["A/1/f0"]`. None for the `tiles` and `footprints` schemas.

#### Example

Tile layout rows for well `A/1`. Tiles are 2048 pixels at 0.325 micrometre, so 665.6 micrometres wide; the 599.0 micrometre step gives an overlap. Both numbers are illustrative.

```text
index  tile  grid_row  grid_col  geometry
0      f0    0         0         POLYGON ((0 0, 665.6 0, 665.6 665.6, 0 665.6, 0 0))
1      f1    0         1         POLYGON ((599.0 0, 1264.6 0, 1264.6 665.6, 599.0 665.6, 599.0 0))
2      f2    1         0         POLYGON ((0 599.0, 665.6 599.0, 665.6 1264.6, 0 1264.6, 0 599.0))
3      f3    1         1         POLYGON ((599.0 599.0, 1264.6 599.0, 1264.6 1264.6, 599.0 1264.6, 599.0 599.0))
```

Well `A/1/collection.json` (proposed), nodes only. The `scene` and `sp-ops:relationships` attributes are shown under D5 and D9. Node ids are the hierarchical names with `/` replaced by `-` (D10). References to rows, columns, and acquisitions cross into the plate document, so they carry a `path` (D5).

```json
{
  "ome": {
    "version": "0.x",
    "type": "collection",
    "id": "A-1",
    "name": "A/1",
    "attributes": {
      "well": {"row": {"id": "A", "path": {"type": "json", "path": "../../collection.json"}},
               "column": {"id": "1", "path": {"type": "json", "path": "../../collection.json"}}},
      "sp-ops:tileLayout": {"id": "A-1-tiles"}
    },
    "nodes": [
      {"type": "sp-ops:shapes", "id": "A-1-tiles", "name": "tiles", "path": {"type": "zarr", "path": "./tiles"}},
      {"type": "sp-ops:shapes", "id": "A-1-footprints", "name": "footprints", "path": {"type": "zarr", "path": "./footprints"}},
      {"type": "sp-ops:table", "id": "A-1-images", "name": "images", "path": {"type": "zarr", "path": "./images"},
       "attributes": {"sp-ops:table": {"type": "condition_table", "tableVersion": "1", "granularity": "image",
                                       "region": {"id": "A-1-footprints"}}}},
      {"type": "sp-ops:table", "id": "A-1-cells", "name": "cells", "path": {"type": "zarr", "path": "./cells"},
       "attributes": {"sp-ops:table": {"type": "feature_table", "tableVersion": "1", "granularity": "cell"}}},
      {"type": "sp-ops:table", "id": "A-1-reads", "name": "reads", "path": {"type": "zarr", "path": "./reads"},
       "attributes": {"sp-ops:table": {"type": "generic_table", "tableVersion": "1", "granularity": "read"}}},
      {"type": "collection", "id": "A-1-f0", "name": "f0",
       "attributes": {"sp-ops:tile": {"index": 0}},
       "nodes": [
         {"type": "collection", "id": "A-1-f0-t2", "name": "t2",
          "attributes": {"sp-ops:timepoint": {"index": 2}},
          "nodes": [
            {"type": "collection", "id": "A-1-f0-t2-iss", "name": "iss", "nodes": [
              {"type": "multiscale", "id": "A-1-f0-t2-iss-r1", "name": "r1",
               "path": {"type": "zarr", "path": "./f0-t2-iss-r1"},
               "attributes": {"acquisition": {"id": "iss-t2-r1", "path": {"type": "json", "path": "../../collection.json"}}}},
              {"type": "multiscale", "id": "A-1-f0-t2-iss-r2", "name": "r2",
               "path": {"type": "zarr", "path": "./f0-t2-iss-r2"},
               "attributes": {"acquisition": {"id": "iss-t2-r2", "path": {"type": "json", "path": "../../collection.json"}}}}
            ]},
            {"type": "multiscale", "id": "A-1-f0-t2-pheno", "name": "pheno",
             "path": {"type": "zarr", "path": "./f0-t2-pheno"},
             "attributes": {"acquisition": {"id": "pheno-t2", "path": {"type": "json", "path": "../../collection.json"}}}},
            {"type": "multiscale", "id": "A-1-f0-t2-cell_seg", "name": "cell_seg",
             "path": {"type": "zarr", "path": "./f0-t2-pheno/labels/cell_seg"},
             "attributes": {"labels": {"source": [{"id": "A-1-f0-t2-pheno"}]}}},
            {"type": "sp-ops:points", "id": "A-1-f0-t2-bases", "name": "bases",
             "path": {"type": "zarr", "path": "./f0-t2-bases"}},
            {"type": "sp-ops:shapes", "id": "A-1-f0-t2-cell_bbox", "name": "cell_bbox",
             "path": {"type": "zarr", "path": "./f0-t2-cell_bbox"}}
          ]}
       ]}
    ]
  }
}
```

### D4. Timepoints and cycles are separate elements; only aligned channels are stacked

#### Decision

The rule is mechanical. A varying quantity MUST be stored as a tensor axis only when it is the channel axis `c` and every plane along it shares one pixel grid. In every other case each value MUST be a separate image element, and the `images` table records the value per element.

1. Fixation timepoint `t` MUST be a separate element per value. Different `t` are different fixed cells and there is no alignment to express.
2. ISS cycle `r` MUST be a separate element per value. Cycles are separate microscope passes and are unaligned until registration. After registration they share a coordinate system (D5), not an array.
3. Channels `c` within one acquisition SHOULD be stacked as `(c, y, x)` when the protocol yields co-registered channels. When channels need registration, each channel MUST be its own `(1, y, x)` element named `<acquisition>/<channel>` until resampled, and MAY be stacked afterwards.
4. The phenotypic round follows the same rule with `r` absent. It is one `(c, y, x)` element per (tile, `t`), or one element per channel when channels are unaligned.

Existing behaviour this rests on. spatialdata `Image2DModel` has dims `(c, y, x)` and `Image3DModel` has dims `(c, z, y, x)`; there is no `t` or `r` axis. RFC-5 multiscales metadata requires two or three `space` axes, at most one `time` axis, and at most one `channel` or custom axis. `r` and `c` therefore cannot both be axes of one on-disk image. A `(t, y, x)` image with a length-one `t` axis is legal in NGFF but not representable in spatialdata, so this specification forbids it.

The annotating table is `images`, one per well, with one row per acquisition image element in the well (raw and resampled). It is an ngio `condition_table` and annotates `footprints` (D3). Derived spot images are not rows. Required `obs` columns:

| Column | Type | Meaning |
| --- | --- | --- |
| `region` | string | `region_key`; the footprints element, `A/1/footprints` |
| `image_id` | integer | `instance_key`; the footprint rectangle for this image |
| `element` | string | element name relative to the well, `f0/t2/iss/r2` |
| `tile` | integer | equals `tiles` index |
| `acquisition` | string | core acquisition id in RFC-8 form, `iss-t2-r2`; a resampled element carries the id of its source image |
| `kind` | string | `iss`, `pheno`, or `merged` (D2) |
| `t` | integer | fixation timepoint |
| `r` | integer, nullable | ISS cycle; null for `pheno` and `merged` |
| `c` | string, nullable | channel name when the element holds exactly one channel; null for a stack |
| `channel_aligned` | boolean | true when `c` is a tensor axis of the element |
| `registered` | boolean | true when the element carries a transformation into the registered frame |
| `anchor` | boolean | true for the reference image of this (tile, `t`) |
| `resample_rule` | string, nullable | `contained` or `containing` for resampled elements (D6) |
| `resample_um_per_px` | float, nullable | set when a resampled grid differs from the anchor pixel size |

`images` has no `var` and an `X` of shape `(n_images, 0)`. It is the tabular mirror of `well.images`, `sp-ops:acquisitions`, `sp-ops:tile`, and `sp-ops:channels`. The JSON is authoritative. A validator MUST report any disagreement between the table and the JSON, and MUST check that every `element` value names an existing element.

#### Rationale

- The rule follows from the spatialdata models and the RFC-5 axis rules, so a reader never guesses whether a five-channel array is five stains or five cycles.
- Separate images per cycle are what the scallops pipeline produces (`A1-1.ome.tiff` to `A1-10.ome.tiff`). Cycle 6 is absent in the real data; a table tolerates gaps, a dense axis does not.
- Annotating `footprints` makes `images` a regular spatialdata table. `join_spatialelement_table` and `filter_by_table_query` work in v0.8.0 today, which is what the draft's "table annotating the images" asks for. A table linked only by a name string cannot be followed by any spatialdata API.
- One table per well is what an analyst filters when doing FOV QC.

#### Rejected alternatives

- `(r, y, x)` tensors with a length-one `r` axis, as the draft sketches. Not representable in spatialdata and not admitted next to `c` by RFC-5.
- Folding cycles into `c` (45 channels named `r1_DAPI`, `r1_A`, and so on) as the stored form. Loses the one-element-per-acquisition mapping that both HCS metadata dialects need. It is allowed as a derived product (D6).
- One `images` table per tile or per `t`. The tile-wide and well-wide views disappear, and the count of tables multiplies.
- Extra plate-level `acquisitions` and `channels` tables. A third copy of facts already in JSON and in `images`.

#### Depends on

None for the rule and the table. Hierarchical SpatialData for names containing `/`; the v0.8.0 fallback is the flattened name (D10).

#### Example

Rows of `images.obs` for tile `f0` (first rows).

```text
image_id  region          element         tile  acquisition  kind   t  r     c     channel_aligned  registered  anchor
0         A/1/footprints  f0/t2/iss/r1    0     iss-t2-r1    iss    2  1     null  true             false       true
1         A/1/footprints  f0/t2/iss/r2    0     iss-t2-r2    iss    2  2     null  true             true        false
8         A/1/footprints  f0/t2/iss/r10   0     iss-t2-r10   iss    2  10    null  true             true        false
9         A/1/footprints  f0/t2/pheno     0     pheno-t2     pheno  2  null  null  true             true        false
10        A/1/footprints  f0/t3/iss/r1    0     iss-t3-r1    iss    3  1     null  true             false       true
```

Unaligned phenotypic channels, same table.

```text
image_id  region          element            tile  acquisition  kind   t  r     c     channel_aligned  registered  anchor
9         A/1/footprints  f0/t2/pheno/DAPI   0     pheno-t2     pheno  2  null  DAPI  false            true        false
10        A/1/footprints  f0/t2/pheno/GFP    0     pheno-t2     pheno  2  null  GFP   false            true        false
```

Building and using the table with spatialdata v0.8.0 names. Element names with `/` are hierarchical SpatialData (proposed).

```python
import anndata as ad
import pandas as pd
from spatialdata import join_spatialelement_table
from spatialdata.models import TableModel

obs = pd.DataFrame({
    "region": "A/1/footprints",
    "image_id": [0, 1, 9],
    "element": ["f0/t2/iss/r1", "f0/t2/iss/r2", "f0/t2/pheno"],
    "tile": [0, 0, 0],
    "acquisition": ["iss-t2-r1", "iss-t2-r2", "pheno-t2"],
    "kind": ["iss", "iss", "pheno"],
    "t": [2, 2, 2],
    "r": pd.array([1, 2, None], dtype="Int64"),
    "c": pd.array([None, None, None], dtype="string"),
    "channel_aligned": [True, True, True],
    "registered": [False, True, True],
    "anchor": [True, False, False],
})
images = TableModel.parse(
    ad.AnnData(obs=obs), region="A/1/footprints", region_key="region", instance_key="image_id"
)
images.uns["sp-ops"] = {"table_type": "condition_table", "table_version": "1", "granularity": "image"}

_, joined = join_spatialelement_table(
    sdata=sdata, spatial_element_names="A/1/footprints", table_name="A/1/images", how="inner"
)
rows = joined.obs.query("tile == 0 and t == 2 and kind == 'iss'").sort_values("r")
cycles = {int(row.r): sdata[f"A/1/{row.element}"] for row in rows.itertuples()}   # proposed API
cycles[1].coords["c"].values                                                       # ['DAPI', 'A', 'G', 'C', 'T']
```

### D5. Cycles are registered to the DAPI channel of the first ISS cycle at each timepoint

#### Decision

Coordinate system names are hierarchical strings in memory. RFC-8 ids MUST match `[a-zA-Z0-9-_.]+`, so on disk `/` becomes `-`.

| Level | spatialdata name | RFC-8 id | Axes | Meaning |
| --- | --- | --- | --- | --- |
| image | none in memory | `intrinsic`, per multiscale | `c`, `y`, `x` | pixel grid scaled to micrometres by the multiscale `scale` |
| tile at one `t` | `A/1/f0/t2` | `A-1-f0-t2` | `y`, `x`, micrometre | the registered frame; every element under `A/1/f0/t2/` is aligned here |
| well | `A/1` | `A-1` | `y`, `x`, micrometre | tile frames placed by the tile layout |
| plate | `plate` | `plate` | `y`, `x`, micrometre | well frames placed by the well layout; OPTIONAL |

In the `stitched` profile the tile component is omitted (D10 rule 6), so the registered frame is `A/1/t2` with RFC-8 id `A-1-t2`. There is no separate tile-level frame. All `t` frames of one tile map to the well by the same translation, so a tile frame would add a coordinate system without adding information. The well frame is agnostic of `t`. A coordinate in `A/1` locates an object on the plate; it does not imply that cells from different fixation timepoints are aligned. Cross-timepoint registration is undefined by this specification.

Registration anchor. Within one (tile, `t`), the anchor channel is the channel with `role: "nuclear"` in `sp-ops:channels`, DAPI in the running example. The reference image is the acquisition whose `sp-ops:acquisitions` entry has `anchor: true` for that `t`. Exactly one acquisition per `t` MUST have `anchor: true`; when no entry has it, the default is the ISS acquisition with the lowest `r` at that `t`. A `merged` acquisition (D2) is already registered. It maps into the registered frame by a pure scale, and it is the anchor when it is the only acquisition at its `t`. `sp-ops:registration` on the `t` collection MUST name `anchorChannel` and MAY name a `reference` image that overrides the plate-level choice for that tile. The reference image maps into the registered frame by a pure scale. Every other acquisition image at that `t` carries its scale followed by an affine estimated from anchor channel to anchor channel. Labels and derived images computed in the registered frame carry a pure scale. Points and shapes computed there carry an identity. Labels computed on the raw pixel grid of an image carry that image's transformation. When the channels of an acquisition are separate elements (D4 rule 3), the element that holds the nuclear channel is registered as above. Every other channel element of that acquisition carries the same affine composed with a channel-to-nuclear correction that the writer estimates. The estimation method is not specified.

Storage on disk.

- The pixel-to-micrometre scale lives in the multiscale `datasets[].coordinateTransformations` (0.5, existing behaviour).
- In memory and in spatialdata's own on-disk element metadata, registration affines are element transformations keyed by coordinate system name (existing behaviour). spatialdata v0.8.0 writes them as `coordinateTransformations` with `input` and `output` objects keyed by `name` (probe-verified for shapes). This copy is authoritative until RFC-5 and RFC-8 are released.
- The RFC-8 sidecar (proposed) repeats the same edges as an RFC-5 `scene` on the `t` collection, tile placement on the well scene, and well placement on the plate scene. The image-to-frame edge is a `byDimension` with integer `input_axes: [1, 2]` and `output_axes: [0, 1]` wrapping a 2 by 3 `affine`, or an `identity` for the reference image. A 2 by 4 `affine` whose first column is zero is the permitted compact form of the same edge; RFC-5 allows affines from N inputs to M outputs. Cross-document references carry both `id` and `path`. A validator SHOULD check that the sidecar and the spatialdata copy agree.
- RFC-5 core `scene` references use `{path, name}`; RFC-8 replaces `name` with `id`. This specification writes the RFC-8 dialect. 0.5 images do not declare a named coordinate system, so a sidecar reader synthesises `intrinsic` from the image `axes` and `scale`.
- Points and shapes have no RFC-5 coordinate system of their own, so the scene does not list them. Their placement is spatialdata element metadata (existing behaviour).

In memory (spatialdata v0.8.0) transformations live on elements, never between coordinate systems. The reader composes, for every element, one transformation per ancestor frame. `get_transformation_between_coordinate_systems(sdata, "A/1/f0/t2", "A/1")` recovers the tile translation because spatialdata builds a networkx graph over elements and coordinate systems.

#### Rationale

- The registered frame is the only place where pixel alignment holds, and it is exactly the scope of one RFC-5 scene. Naming it after the prefix makes the scope visible in the repr.
- DAPI is present in every ISS cycle and in the phenotypic round, so it is the only channel that can anchor both registrations. The scallops layout stores per-cycle affines toward one reference.
- A 2D registered frame keeps labels, points, and shapes two-dimensional. A frame with a `c` axis would force a 3-vector translation onto 2D elements, which RFC-5 forbids because translation inputs and outputs must have equal dimensionality.
- A per-(tile, `t`) frame stops viewers from overlaying two timepoints as if aligned.

#### Rejected alternatives

- A registered frame with axes (`c`, `y`, `x`). See above.
- One frame per acquisition image (ten per (tile, `t`)). Bloats the repr for no analytical gain.
- A tile frame between `t` and well. Redundant.
- The phenotypic DAPI as the fixed default reference. Base calling needs cycles aligned first; a depositor MAY still choose it with `anchor: true` or `sp-ops:registration.reference`.
- Registering every cycle directly into the well frame. Readers could not tell which elements are pixel-aligned.

#### Depends on

None for the in-memory graph and the spatialdata on-disk copy. RFC-5 and RFC-8 for the `scene` in the sidecar.

#### Example

The `t2` collection inside `A/1/collection.json` (proposed; affine values illustrative).

```json
{
  "type": "collection",
  "id": "A-1-f0-t2",
  "name": "t2",
  "attributes": {
    "sp-ops:timepoint": {"index": 2},
    "sp-ops:registration": {"anchorChannel": "DAPI", "reference": {"id": "A-1-f0-t2-iss-r1"}},
    "scene": {
      "coordinateSystems": [
        {"id": "A-1-f0-t2", "name": "A/1/f0/t2",
         "axes": [{"name": "y", "type": "space", "unit": "micrometer"},
                  {"name": "x", "type": "space", "unit": "micrometer"}]}
      ],
      "coordinateTransformations": [
        {"type": "byDimension",
         "input": {"id": "intrinsic", "path": {"type": "zarr", "path": "./f0-t2-iss-r1"}},
         "output": {"id": "A-1-f0-t2"},
         "transformations": [
           {"input_axes": [1, 2], "output_axes": [0, 1], "transformation": {"type": "identity"}}
         ]},
        {"type": "byDimension",
         "input": {"id": "intrinsic", "path": {"type": "zarr", "path": "./f0-t2-iss-r2"}},
         "output": {"id": "A-1-f0-t2"},
         "transformations": [
           {"input_axes": [1, 2], "output_axes": [0, 1],
            "transformation": {"type": "affine",
                               "affine": [[1.0002, -0.0004, 1.95], [0.0004, 1.0002, -0.65]]}}
         ]},
        {"type": "byDimension",
         "input": {"id": "intrinsic", "path": {"type": "zarr", "path": "./f0-t2-pheno"}},
         "output": {"id": "A-1-f0-t2"},
         "transformations": [
           {"input_axes": [1, 2], "output_axes": [0, 1],
            "transformation": {"type": "affine",
                               "affine": [[0.9998, 0.0011, -3.25], [-0.0011, 0.9998, 4.55]]}}
         ]}
      ]
    }
  },
  "nodes": []
}
```

Well scene in the same document. One translation per (tile, `t`) frame, values from `tiles`.

```json
"scene": {
  "coordinateSystems": [
    {"id": "A-1", "name": "A/1",
     "axes": [{"name": "y", "type": "space", "unit": "micrometer"},
              {"name": "x", "type": "space", "unit": "micrometer"}]}
  ],
  "coordinateTransformations": [
    {"type": "translation", "translation": [0.0, 0.0], "input": {"id": "A-1-f0-t2"}, "output": {"id": "A-1"}},
    {"type": "translation", "translation": [0.0, 599.0], "input": {"id": "A-1-f1-t2"}, "output": {"id": "A-1"}}
  ]
}
```

Plate scene in the plate `collection.json` (proposed), as an attribute next to `plate` and `sp-ops:spec` in the D2 plate document. It defines the OPTIONAL coordinate system `plate` and one `translation` per well, from the well frame `A-1` to `plate`. Each well frame is defined in its own well document, so every `input` is a cross-document reference and MUST carry both `id` and `path` (RFC-8 `Reference` with `path`). The translation is `[y, x]` in micrometres, with input and output dimensionality equal to the array length as RFC-5 requires. The values are illustrative; they exceed the 34 millimetre width of the real stitched well image, so the wells do not overlap.

```json
"scene": {
  "coordinateSystems": [
    {"id": "plate", "name": "plate",
     "axes": [{"name": "y", "type": "space", "unit": "micrometer"},
              {"name": "x", "type": "space", "unit": "micrometer"}]}
  ],
  "coordinateTransformations": [
    {"type": "translation", "translation": [0.0, 0.0],
     "input": {"id": "A-1", "path": {"type": "json", "path": "./A/1/collection.json"}}, "output": {"id": "plate"}},
    {"type": "translation", "translation": [0.0, 40000.0],
     "input": {"id": "A-2", "path": {"type": "json", "path": "./A/2/collection.json"}}, "output": {"id": "plate"}},
    {"type": "translation", "translation": [0.0, 80000.0],
     "input": {"id": "A-3", "path": {"type": "json", "path": "./A/3/collection.json"}}, "output": {"id": "plate"}}
  ]
}
```

In memory. `set_transformation`, `get_transformation`, and `get_transformation_between_coordinate_systems` are v0.8.0 names; the constructors `Affine(matrix, input_axes, output_axes)`, `Scale(scale, axes)`, `Translation(translation, axes)`, and `Sequence(transformations)` were probe-verified against v0.8.0.

```python
from spatialdata.transformations import (
    Affine, Scale, Sequence, Translation,
    get_transformation, get_transformation_between_coordinate_systems, set_transformation,
)

px = Scale([0.325, 0.325], axes=("y", "x"))
reg = Affine(
    [[1.0002, -0.0004, 1.95], [0.0004, 1.0002, -0.65], [0, 0, 1]],
    input_axes=("y", "x"), output_axes=("y", "x"),
)
to_well = Translation([0.0, 0.0], axes=("y", "x"))

r1 = sdata["A/1/f0/t2/iss/r1"]                                            # proposed API
r2 = sdata["A/1/f0/t2/iss/r2"]
set_transformation(r1, px, to_coordinate_system="A/1/f0/t2")
set_transformation(r2, Sequence([px, reg]), to_coordinate_system="A/1/f0/t2")
set_transformation(r2, Sequence([px, reg, to_well]), to_coordinate_system="A/1")

get_transformation(sdata["A/1/f0/t2/pheno"], to_coordinate_system="A/1/f0/t2")
get_transformation_between_coordinate_systems(sdata, "A/1/f0/t2", "A/1")   # the tile translation
```

Transformation graph. On disk the edges between frames are scene edges; in memory they are composed onto each element.

```{mermaid}
graph LR
  subgraph T2 ["A/1/f0/t2 (registered frame)"]
    R1["iss/r1 (reference)"] -- "scale" --> CS2["cs A/1/f0/t2"]
    R2["iss/r2"] -- "scale, affine DAPI to DAPI" --> CS2
    R10["iss/r10"] -- "scale, affine" --> CS2
    PH["pheno"] -- "scale, affine" --> CS2
    SEG["cell_seg, nuclear_seg"] -- "scale" --> CS2
    PTS["bases, spots/peaks, cell_bbox"] -- "identity" --> CS2
  end
  CS2 -- "translation from tiles row f0" --> W["cs A/1"]
  CS3["cs A/1/f0/t3"] -- "same translation" --> W
  CSF1["cs A/1/f1/t2"] -- "translation from tiles row f1" --> W
  FP["footprints, tiles"] -- "identity" --> W
  W -- "translation from wells row A/1" --> P["cs plate (optional)"]
```

### D6. Resampling uses the largest contained box by default

#### Decision

Two rules are defined for the common area after registration, both computed in the registered frame from `footprints`.

| Rule | Definition | Use |
| --- | --- | --- |
| `contained` (default, SHOULD) | the intersection of the footprints of every image being resampled | base calling; every output pixel has a value from every cycle |
| `containing` (MAY) | the union of those footprints | display; pixels outside a cycle's footprint are fill values |

A writer that stores resampled images MUST record the rule in the `images` column `resample_rule` and MUST set `registered` to true. It MUST also set `resample_um_per_px` when the output grid is not the anchor's pixel size. Labels MUST be resampled with nearest-neighbour semantics. Raw acquisition images remain canonical and MUST be kept. Resampled products MAY be stored under `<t>/reg/`, for example `A/1/f0/t2/reg/iss/r2`, with an identity transformation to the registered frame.

`spatialdata.transform` with an explicit `transformation` requires `maintain_positioning=True` in v0.8.0; without it the call raises (probe-verified). `spatialdata.rasterize` (existing behaviour) expresses the operation with four arguments. `axes` is `("y", "x")`. `min_coordinate` and `max_coordinate` give the box in `target_coordinate_system`, which is also the output coordinate system. `target_unit_to_pixels` is `1 / 0.325` pixels per micrometre, so the output keeps the native pixel size. Exactly one of `target_unit_to_pixels`, `target_width`, `target_height`, `target_depth` may be given. Passing a SpatialData returns a SpatialData of single-scale images and labels whose names gain the suffix `_rasterized_images` (probe-verified). A writer MUST rename the outputs before storing them under `reg/`.

A stacked product whose `c` axis enumerates every (cycle, channel) pair MAY be built with `Image2DModel.parse(..., c_coords=...)` and stored as `<t>/reg/iss_stack`, with `c` names `r<k>_<channel>`. This is the draft's `(r, y, x)` tensor in the only form spatialdata admits.

#### Rationale

- Base calling reads the same pixel across all cycles. With the intersection every pixel is defined in every cycle; with the union some pixels are fill values that downstream code must mask.
- Footprints hold the registered extents as geometry, so the box is a shapely operation and no pixels are read to choose it.
- `rasterize` is the one public spatialdata function that resamples into a named coordinate system with an explicit box and resolution.

#### Rejected alternatives

- Union as the default. Requires a fill value and a validity mask per cycle.
- Resampling into the well frame directly. Valid, but ties the product to the tile layout instead of to the registration.
- Persisting only the resampled stack. Re-registration becomes impossible.

#### Depends on

None for `rasterize`. Hierarchical SpatialData for the sub-view call `sdata["A/1/f0/t2/iss"]`; in v0.8.0 the same call is made once per flattened element name.

#### Example

```python
import shapely
from spatialdata import join_spatialelement_table, rasterize, transform
from spatialdata.transformations import get_transformation_between_coordinate_systems

_, images = join_spatialelement_table(
    sdata=sdata, spatial_element_names="A/1/footprints", table_name="A/1/images", how="inner"
)
ids = images.obs.query("tile == 0 and t == 2 and kind == 'iss'")["image_id"].to_list()

to_t2 = get_transformation_between_coordinate_systems(sdata, "A/1", "A/1/f0/t2")
fp = transform(sdata["A/1/footprints"].loc[ids], transformation=to_t2, maintain_positioning=True)   # footprints in the registered frame

box = shapely.intersection_all(fp.geometry.values)                        # contained rule
xmin, ymin, xmax, ymax = box.bounds
# containing rule: xmin, ymin, xmax, ymax = fp.total_bounds

registered = rasterize(
    sdata["A/1/f0/t2/iss"],                                                # sub-view, proposed API
    axes=("y", "x"),
    min_coordinate=[ymin, xmin],
    max_coordinate=[ymax, xmax],
    target_coordinate_system="A/1/f0/t2",
    target_unit_to_pixels=1 / 0.325,
)
list(registered.images)            # ['r1_rasterized_images', ..., 'r10_rasterized_images']
```

Building the optional stack in memory.

```python
import xarray as xr
from spatialdata.models import Image2DModel
from spatialdata.transformations import get_transformation

cycles = [1, 2, 3, 4, 5, 7, 8, 9, 10]
arrays = [registered.images[f"r{k}_rasterized_images"] for k in cycles]
stack = Image2DModel.parse(
    xr.concat(arrays, dim="c").data,
    dims=("c", "y", "x"),
    c_coords=[f"r{k}_{ch}" for k in cycles for ch in ("DAPI", "A", "G", "C", "T")],
    transformations={"A/1/f0/t2": get_transformation(arrays[0], to_coordinate_system="A/1/f0/t2")},
)
```

The phenotypic round is resampled with the same call on `sdata["A/1/f0/t2/pheno"]`, or on each single-channel element when its channels are unaligned.

### D7. Cell features annotate the labels, FOV features annotate the footprints, well features annotate the wells

#### Decision

| Granularity | Element | Annotates (`region`) | `region_key` | `instance_key` | ngio type |
| --- | --- | --- | --- | --- | --- |
| cell | `A/1/cells`, one per well | list of every `cell_seg` labels element in the well | `region` | `label` | `feature_table` |
| image (FOV) | `A/1/fov_features`, one per well (MAY) | `A/1/footprints` | `region` | `image_id` | `feature_table` |
| well | `well_features` at the plate root (MAY) | `wells` shapes at the plate root | `region` | `well_id` | `feature_table` |

Cell table. `obs` MUST contain `region`, `label` (integer, the label pixel value), `cell_uid` (string), `tile` (integer), and `t` (integer). `cell_uid` MUST be unique across the aggregation and SHOULD have the form `<row><col>_<tile>_t<t>_<label>`, for example `A1_f0_t2_812`; a writer with several plates in one aggregation prefixes the plate name. `obs` SHOULD contain `perturbation_id`, `barcode`, `n_reads`, and `qc_pass` once assigned (D11). `var` index holds the CellProfiler feature names and SHOULD carry the compartment prefix (`cell_AreaShape_Area`) so that names stay unique across compartments. `X` MUST be numeric and SHOULD be float32; a `categorical` feature is stored as integer codes, and a non-numeric `metadata` value belongs in `obs`. `var` MUST carry `compartment` (`cell`, `cytosol`, `nuclei`, the scallops feature folders) and `feature_type` (`measurement`, `categorical`, `metadata`, the ngio feature table vocabulary). `X` holds the values. `obsp` MAY hold spatial neighbour graphs for cell to cell relations. `obsm["spatial"]` MAY hold cell centroids in the well coordinate system for legacy tools; the labels and `cell_bbox` are authoritative geometry. A `nuclei` table with the same schema annotating `nuclear_seg` MAY be added when nuclear and cell label values do not match one to one.

FOV table. `obs` MUST contain `region` and `image_id`, and SHOULD contain `qc_pass` (boolean), the same name used on `cells` and `reads`. `var` names per-image QC metrics such as focus, background, and signal to noise; the names are not fixed. `X` holds the values, one row per camera image.

Well table. `obs` MUST contain `region`, `well_id` (integer, the `wells` shapes index), `well` (string, `A/1`), `n_tiles`, and `n_cells`. `X` holds well-level metrics such as stitching residuals and seeding uniformity. `wells` has an integer index, columns `well`, `row`, `column`, and a rectangle per well in the `plate` frame.

Relation to the OPS data standard v0.1.0 (existing). `cell_data.parquet` has one row per cell with `cell_uid` and `perturbation_id`. It is the concatenation over wells of `cells.obs` joined with `cells.X`; `cell_uid` and `perturbation_id` are carried unchanged. `feature_definitions.csv` corresponds to `var`. A validator MUST check that every non-null `perturbation_id` in `cells` exists in `library`. The audited submission fails this check on 32 retired gene symbols per dataset (`AARS` for `AARS1`).

#### Rationale

- Labels are what CellProfiler measures, so the label value is the exact instance key and the join to pixels is exact. spatialdata accepts a list as `region`, so one table covers every `cell_seg` in a well. In v0.8.0 `join_spatialelement_table` against a labels element returns no table for `how="inner"` and the matching rows for `how="left"` (probe-verified). Labels joins on every page therefore use `how="left"`.
- One cell table per well mirrors the scallops output (`features/cell/A1.parquet`) and is the unit that pseudobulk aggregation consumes. Per-(tile, `t`) tables would give 32 per well and force a concatenation before any well-level step.
- FOV QC is a property of one camera image, so the per-image grain is right and a per-tile summary is a `groupby` away.
- Typing features in `var` lets downstream tools pick measurement columns without guessing from dtypes, which is the stated purpose of the ngio vocabulary.

#### Rejected alternatives

- Cell features annotating `cell_bbox` shapes. Boxes are derived and may be absent; labels are always there.
- One cell table per (tile, `t`). See above.
- A fixed `cell_uid` format as MUST. The OPS standard requires only global uniqueness, and an exporter must not rewrite submitter ids.
- A well table without a region. Not addressable by any spatialdata query.

#### Depends on

None.

#### Example

```python
import anndata as ad
import numpy as np
import pandas as pd
from spatialdata import join_spatialelement_table
from spatialdata.models import TableModel

regions = [f"A/1/{tile}/t{t}/cell_seg" for tile in ("f0", "f1", "f2", "f3") for t in (2, 3, 4, 5, 7, 8, 9, 10)]
obs = pd.DataFrame({
    "region": ["A/1/f0/t2/cell_seg", "A/1/f0/t2/cell_seg"],
    "label": [812, 813],
    "cell_uid": ["A1_f0_t2_812", "A1_f0_t2_813"],
    "tile": [0, 0],
    "t": [2, 2],
    "perturbation_id": pd.array(["AARS1", None], dtype="string"),
    "barcode": pd.array(["GCTAGCTAGCTAGCTAGCTA", None], dtype="string"),   # illustrative
})
var = pd.DataFrame(
    {"compartment": ["cell", "nuclei"], "feature_type": ["measurement", "measurement"]},
    index=["cell_AreaShape_Area", "nuclei_Intensity_MeanIntensity_DAPI"],
)
cells = TableModel.parse(
    ad.AnnData(X=np.array([[812.0, 143.2], [655.0, 151.9]], dtype="float32"), obs=obs, var=var),
    region=regions, region_key="region", instance_key="label",
)
cells.uns["sp-ops"] = {"table_type": "feature_table", "table_version": "1", "granularity": "cell"}

elements, table = join_spatialelement_table(                              # how="left": v0.8.0 returns no table
    sdata=sdata, spatial_element_names="A/1/f0/t2/cell_seg", table_name="A/1/cells", how="left"   # for how="inner" on labels
)

cells = sdata["A/1/cells"]                                              # proposed API
cell_data = cells.obs[["cell_uid", "perturbation_id"]].join(cells.to_df())
cell_data.to_parquet("cell_data.parquet")
```

### D8. Table types use the ngio vocabulary under one namespaced dictionary

#### Decision

Every table MUST declare its type with one of the five ngio strings `generic_table`, `roi_table`, `masking_roi_table`, `feature_table`, `condition_table`. The declaration lives in two mirrored places.

- In memory, `adata.uns["sp-ops"]` is a dictionary with `table_type` (MUST), `table_version` (MUST, `"1"`), and `granularity` (MUST). spatialdata writes and reads `uns` unchanged, so this survives a round trip today.
- On disk in the RFC-8 view, the node attribute `sp-ops:table` carries `type`, `tableVersion`, `granularity`, and an OPTIONAL `region` reference that mirrors `spatialdata_attrs.region` (proposed).

`spatialdata_attrs` is not extended. It stays exactly `region`, `region_key`, `instance_key` as `TableModel` defines them. Allowed `granularity` values are `cell`, `image`, `well`, `read`, `perturbation`.

| Table | `table_type` | `granularity` |
| --- | --- | --- |
| `A/1/images` | `condition_table` | `image` |
| `A/1/fov_features` | `feature_table` | `image` |
| `A/1/cells` | `feature_table` | `cell` |
| `A/1/reads` | `generic_table` | `read` |
| `well_features` | `feature_table` | `well` |
| `library` | `condition_table` | `perturbation` |

Compatibility rules. When ngio's own `type` attribute is present on a table group it MUST agree with `sp-ops:table.type`. A writer MUST NOT emit a partial set of ngio group attributes (`type`, `table_version`, `backend`, `index_key`) unless it writes a full ngio `tables` group with the `tables` list. A validator MUST warn on `generic_table`. Widening `feature_table` to a shapes region (`fov_features`, `well_features`) is a spatialdata capability and a departure from ngio, whose feature tables name a label image.

#### Rationale

- ngio has documented the five types and Fractal recognises four of them on read, so reusing the strings costs nothing and buys interoperability.
- A single namespaced `uns` key is a plain string. anndata serialises `uns` keys as Zarr node names, and a colon in a node name is illegal on Windows paths, so `uns["sp-ops:table_type"]` would break portability.
- Keeping `spatialdata_attrs` untouched avoids a change to `TableModel` validation that this specification does not control.

#### Rejected alternatives

- `spatialdata_attrs.table_type`. Needs an upstream spatialdata change with unverified pass-through.
- `uns["sp-ops:table_type"]`. Colon in a Zarr node name; see above.
- ngio's group attributes verbatim without a `tables` group. Partial compatibility would mislead ngio readers.
- OPS-specific type names (`acquisition_table`, `barcode_table`). The ngio vocabulary already covers them.

#### Depends on

None for `uns`. RFC-8 for the node attribute.

#### Example

```python
sdata["A/1/cells"].uns["sp-ops"]
# {'table_type': 'feature_table', 'table_version': '1', 'granularity': 'cell'}
```

```json
{"type": "sp-ops:table", "id": "A-1-cells", "name": "cells",
 "path": {"type": "zarr", "path": "./cells"},
 "attributes": {"sp-ops:table": {"type": "feature_table", "tableVersion": "1", "granularity": "cell"}}}
```

### D9. Relationships are an edge list stored on the lowest node that contains both endpoints

:::{admonition} Status
:class: note
This decision depends on the element relationships prototypes from the Padua hackathon (`spatialdata_elements_graph`) and the Venice hackathon (`element_relationships`, `sjoin_suggestions`). Neither is released. `sdata.attrs` exists in spatialdata v0.8.0 and is where both prototypes store their graph. The `query` and `check_relationships` names come from the Venice `query.py` sketch, whose README marks the code as unverified.
:::

#### Decision

`sp-ops:relationships` is an object `{"version": "0.1", "edges": [...]}`. Every edge has the same shape. The field names `from`, `to`, `method`, `params`, `how`, `left_on`, `right_on`, `predicate`, and `distance` come from the Padua prototype. The join vocabulary `index`, `value`, and `<column name>` comes from the Venice `join_strategy`.

| Field | Type | Requirement | Values |
| --- | --- | --- | --- |
| `from` | string | MUST | element name relative to the node carrying the attribute |
| `to` | string | MUST | element name, same convention; one element, never an array |
| `method` | string | MUST | `join` (by key) or `sjoin` (spatial) |
| `params.how` | string | MUST | `left`, `inner`, `right` |
| `params.left_on` | array of strings | MUST for `join` | each entry is `index`, `value` (label pixel value), `name` (the element's own name), or a column name on `from` |
| `params.right_on` | array of strings | MUST for `join` | same vocabulary on `to`; same length as `left_on` |
| `params.predicate` | string | MUST for `sjoin` | `within`, `intersects`, `contains`, `dwithin` |
| `params.distance` | number | MUST when predicate is `dwithin` | in units of `target_coordinate_system` |
| `params.target_coordinate_system` | string | MUST for `sjoin` | the frame in which the predicate is evaluated |
| `params.result_column` | string | SHOULD for `sjoin` | column on `from` that stores the matched `to` instance once computed |
| `status` | string | MUST | `computed` (the result is stored) or `suggested` (not yet computed) |
| `cardinality` | string | SHOULD | `1:1`, `1:n`, `n:1`, `n:m`, `unknown` |
| `description` | string | MAY | free text |

Semantics. An `sjoin` whose `to` is a labels element means pixel lookup of the label value at each `from` geometry, and admits only `within`. An `sjoin` between shapes or points elements is a geopandas spatial join. `left_on` and `right_on` are lists so that composite keys work. Annotations that `spatialdata_attrs` already expresses (a table annotating labels or shapes) MUST NOT be repeated as edges; the reader adds them to the in-memory graph.

Storage. Each edge is stored on the lowest collection whose subtree contains both endpoints, with names relative to that collection. Edges inside one (tile, `t`) sit on the `t` collection; edges between a (tile, `t`) element and a well-level table sit on the well; edges that reach `library` sit on the plate. In the 0.5 layout the Zarr group attributes of the plate and well carry `sp-ops:relationships` and the sidecar carries the `t`-level edges; names use the hierarchical form in both. When no sidecar is written, the well group carries the `t`-level edges with well-relative names. In memory the merged list is `sdata.attrs["sp-ops"]["relationships"]` with names relative to the object's root.

Query API (proposed).

```python
from spatialdata.relationships import check_relationships, query   # proposed API

check_relationships(sdata)                     # per edge: cardinality, coverage, order, missing ids
linked = query(sdata, "A/1/f0/t2/cell_seg", depth="all", ids=[812, 813])
linked["A/1/cells"]                            # AnnData rows for the two cells
linked["A/1/f0/t2/cell_bbox"]                  # their bounding boxes
linked["A/1/f0/t2/bases"]                      # base calls inside them, via result_column cell_label
linked["A/1/reads"]                            # reads assembled from those bases
```

#### Rationale

- An edge list carries a key join and a spatial join with a predicate in one shape. The Venice groups cannot express a spatial join or a directed join with different column names.
- A predicate without a frame is undefined in a store with a hundred coordinate systems, so `target_coordinate_system` is required.
- `status` keeps the Venice distinction between computed joins and suggestions without a second attribute.
- Storing on the lowest common node keeps a well document self-contained, so `SpatialData.read("ops_plate.zarr/A/1")` sees valid names without a prefix-stripping rule.

#### Rejected alternatives

- Venice groups only. No spatial joins and no direction.
- Padua's full pandas parameter set (`suffixes`, `indicator`, `lsuffix`, `rsuffix`). Implementation details of one library.
- Wildcards in element names and array-valued `to`. No precedent in either prototype.
- A separate `method: name` for the `images` table. The `element` column of `images` is validated by name (D4), so no edge is needed.
- Plate-root-only storage. A well opened on its own would lose its joins.

#### Depends on

The relationships proposal. RFC-8 for storage on collection nodes; in the 0.5 layout the plate and well group attributes need nothing unreleased.

#### Example

Edges on the `t2` collection (names relative to `A/1/f0/t2`).

```json
"sp-ops:relationships": {
  "version": "0.1",
  "edges": [
    {"from": "cell_bbox", "to": "cell_seg", "method": "join",
     "params": {"how": "inner", "left_on": ["index"], "right_on": ["value"]},
     "status": "computed", "cardinality": "1:1"},
    {"from": "bases", "to": "cell_seg", "method": "sjoin",
     "params": {"how": "left", "predicate": "within", "target_coordinate_system": "A/1/f0/t2",
                "result_column": "cell_label"},
     "status": "computed", "cardinality": "n:1"},
    {"from": "spots/peaks", "to": "cell_seg", "method": "sjoin",
     "params": {"how": "left", "predicate": "within", "target_coordinate_system": "A/1/f0/t2",
                "result_column": "cell_label"},
     "status": "suggested"}
  ]
}
```

Edges on the well (names relative to `A/1`) and on the plate.

```json
"sp-ops:relationships": {
  "version": "0.1",
  "edges": [
    {"from": "f0/t2/bases", "to": "reads", "method": "join",
     "params": {"how": "inner", "left_on": ["read"], "right_on": ["read"]},
     "status": "computed", "cardinality": "n:1"},
    {"from": "f0/t2/spots/peaks", "to": "reads", "method": "join",
     "params": {"how": "left", "left_on": ["read"], "right_on": ["read"]},
     "status": "computed", "cardinality": "1:1"}
  ]
}
```

```json
"sp-ops:relationships": {
  "version": "0.1",
  "edges": [
    {"from": "A/1/cells", "to": "library", "method": "join",
     "params": {"how": "left", "left_on": ["barcode"], "right_on": ["barcode"]},
     "status": "computed", "cardinality": "n:1"},
    {"from": "A/1/reads", "to": "library", "method": "join",
     "params": {"how": "left", "left_on": ["barcode"], "right_on": ["barcode"]},
     "status": "computed", "cardinality": "n:1"}
  ]
}
```

```{mermaid}
graph LR
  subgraph T2 ["A/1/f0/t2"]
    CB["cell_bbox (shapes)"] -- "join index = value" --> CS["cell_seg (labels)"]
    BA["bases (points)"] -- "sjoin within, result cell_label" --> CS
    PK["spots/peaks (points)"] -. "sjoin within (suggested)" .-> CS
  end
  subgraph W ["A/1"]
    CF["cells (table)"] -- "region, instance_key label" --> CS
    IM["images (table)"] -- "region, instance_key image_id" --> FP["footprints (shapes)"]
    FV["fov_features (table)"] -- "region" --> FP
    BA -- "join read = read" --> RD["reads (table)"]
    PK -- "join read = read" --> RD
  end
  CF -- "join barcode = barcode" --> LIB["library (table, plate root)"]
  RD -- "join barcode = barcode" --> LIB
  WF["well_features (table)"] -- "region, instance_key well_id" --> WL["wells (shapes, plate root)"]
```

### D10. Element names are the on-disk paths, and a hyphen flattens them for v0.8.0

:::{admonition} Status
:class: note
Names containing `/`, the `elements=` constructor, `sdata["A/1"]` sub-views, and the tree repr come from the experimental hierarchical SpatialData branch. None is released. spatialdata v0.8.0 rejects `/` with `Name must contain only alphanumeric characters, underscores, dots and hyphens` (probe-verified). Three gaps in the branch were verified in its source. `__getitem__` builds the sub-view as `SpatialData(elements=sub_elements)` without `attrs`, so relationships vanish in a sub-view. Table `region` values are not rewritten when a prefix is stripped. Coordinate system names containing `/` are unverified. The repr lists every coordinate system, 100 for the running example. These are upstream requests, not text of this specification.
:::

#### Decision

The path scheme.

```text
<row>/<col>/<tile>/<t>/iss/r<k>          images that vary by cycle       A/1/f0/t2/iss/r2
<row>/<col>/<tile>/<t>/<item>            everything else at one t        A/1/f0/t2/pheno, .../cell_seg
<row>/<col>/<tile>/<t>/reg/<...>         resampled products (MAY)        A/1/f0/t2/reg/iss/r2
<row>/<col>/<item>                       well-level                      A/1/tiles, A/1/cells
<item>                                   plate-level                     library, wells, well_features
```

Rules.

1. An element name is the path of its Zarr group relative to the store root in the collections layout (proposed). In the 0.5 layout the reader derives the name from the flattened path by rule 2 and rule 4.
2. Every path component MUST match `[A-Za-z0-9_]+`. The hyphen is reserved for flattening. Replacing `/` by `-` below the well gives the 0.5 image path (D2), the RFC-8 node id, the RFC-8 coordinate system id, and a valid v0.8.0 element name. Replacing `-` by `/` reverses it. Rows and columns are alphanumeric by the 0.5 plate rules, so the well prefix is never ambiguous.
3. No element name MUST be a prefix of another element name. Labels are siblings of their source image (`A/1/f0/t2/cell_seg`), never children. Every element is therefore a leaf for the branch's recursive scan for `spatialdata_attrs.element_type`.
4. In the 0.5 layout, a label stored at `<image>/labels/<name>` is named `<parent of image>/<name>` in the hierarchical view, and the RFC-8 sidecar references it by its nested path. This is the one place where the on-disk path and the element name differ, and it is forced by the 0.5 requirement that labels nest under their image. When the source image is itself a channel element (`pheno/DAPI`, D4 rule 3), the label is named under the acquisition, `A/1/f0/t2/pheno/nuclear_seg`. The fixed label names of rule 7 therefore sit at `<t>/` only for stacked acquisitions.
5. Names MUST NOT carry a type suffix such as `_image` or `_table`. The type lives in `spatialdata_attrs.element_type` and in the RFC-8 node `type`.
6. Fixed component names are `t<index>` for fixation timepoints, `iss`, `pheno`, and `merged` for modalities, `r<index>` for cycles, `spots` for spot detection outputs, and `reg` for resampled products. Tile names are writer-defined; the running example uses `f0` to `f3`. In the `stitched` profile the tile level is omitted (`A/1/t2/pheno`). A `stitched` well with exactly one acquisition MAY name its image `0` (D2 rule 3). Its element is then `A/1/0`, and its labels are `A/1/nuclear_seg` and `A/1/cell_seg` by rule 4.
7. Fixed item names are `tiles`, `footprints`, `images`, `fov_features`, `cells`, `reads`, `pheno`, `nuclear_seg`, `cell_seg`, `cell_bbox`, `bases`, `spots/max`, `spots/std`, `spots/peaks`, `wells`, `well_features`, `library`. Additional items MAY be added, for example `cytosol_seg` or `nuclei`.

Mapping between the 0.5 layout and hierarchical names for well `A/1`.

| 0.5 path under `A/1/` | Hierarchical name | v0.8.0 flat name |
| --- | --- | --- |
| `f0-t2-iss-r2` | `A/1/f0/t2/iss/r2` | `A-1-f0-t2-iss-r2` |
| `f0-t2-pheno` | `A/1/f0/t2/pheno` | `A-1-f0-t2-pheno` |
| `f0-t2-pheno/labels/cell_seg` | `A/1/f0/t2/cell_seg` | `A-1-f0-t2-cell_seg` |
| `f0-t2-spots-peaks` | `A/1/f0/t2/spots/peaks` | `A-1-f0-t2-spots-peaks` |
| `tiles` | `A/1/tiles` | `A-1-tiles` |
| `t2-iss-r2` (`stitched` profile) | `A/1/t2/iss/r2` | `A-1-t2-iss-r2` |
| `t2-pheno` (`stitched` profile) | `A/1/t2/pheno` | `A-1-t2-pheno` |
| `0` (`stitched` profile, one `merged` acquisition, the real store) | `A/1/0` | `A-1-0` |
| `0/labels/cell_seg` (same store) | `A/1/cell_seg` | `A-1-cell_seg` |

#### Rationale

- `t` sits above modality because a fixation timepoint is one population of cells. Segmentation, spots, reads, and features belong to that population, not to a modality. `sdata["A/1/f0/t2"]` is therefore one analysable unit and one RFC-5 scene.
- One rule (`/` to `-`) serves four purposes, so there is no mapping table to maintain.
- The branch's `__getitem__` returns an exact match before a prefix view, so a name that prefixes another name would shadow the sub-view. Rule 3 prevents that.
- `r` is the draft's own letter for rounds; spelling cycles with `c` would collide with the channel axis.

#### Rejected alternatives

- Modality above `t` (`A/1/f0/iss/t2/r1`), as the draft sketches folders. Labels and tables would have no natural home, and one registration scene would span two sibling collections.
- Flattening with `_`. Collides with `cell_seg` and `nuclear_seg` and is not reversible.
- Encoding `t` and `r` in one component (`t2_r1`). Loses the per-`t` sub-view.
- Nested labels (`.../pheno/labels/cell_seg`) as element names. Violates rule 3 and can never be reached as a sub-view of `pheno`.

#### Depends on

Hierarchical SpatialData. The flattened names are valid in v0.8.0 today.

#### Example

```python
from spatialdata import SpatialData

sdata = SpatialData.read("ops_plate.zarr")              # hierarchical branch, proposed API
well = sdata["A/1"]                                       # sub-view: keys 'tiles', 'cells', 'f0/t2/iss/r1', ...
t2 = well["f0"]["t2"]                                     # same as sdata["A/1/f0/t2"]
t2.images.keys()                                          # 'iss/r1', ..., 'iss/r10', 'pheno', 'spots/max', 'spots/std'
sdata["A/1/f0/t2/iss/r2"] is t2["iss/r2"]                 # True
partial = SpatialData.read("ops_plate.zarr/A/1")          # partial read of one well
```

Repr of the well sub-view. The format follows `_gen_repr` on the branch, which groups by the first path component only, so `t2/iss/r1` appears flat inside `f0/`. Only the first timepoint of the first tile is listed; a real repr prints every element.

```text
SpatialData object at /data/ops_plate.zarr/A/1
├── cells: [Table] AnnData (27488, 1400)
├── footprints: [Shapes] GeoDataFrame (320, 1)
├── fov_features: [Table] AnnData (320, 12)
├── images: [Table] AnnData (320, 0)
├── reads: [Table] AnnData (1203456, 0)
├── tiles: [Shapes] GeoDataFrame (4, 4)
├── f0/ (136 elements)
│   ├── t2/bases: [Points2D] DataFrame (612340, 6)
│   ├── t2/cell_bbox: [Shapes] GeoDataFrame (859, 1)
│   ├── t2/cell_seg: [Labels2D] DataTree[yx] (2048, 2048), (1024, 1024), (512, 512)
│   ├── t2/iss/r1: [Image2D] DataTree[cyx] (5, 2048, 2048), (5, 1024, 1024), (5, 512, 512)
│   ├── t2/iss/r2: [Image2D] DataTree[cyx] (5, 2048, 2048), (5, 1024, 1024), (5, 512, 512)
│   ├── t2/iss/r10: [Image2D] DataTree[cyx] (5, 2048, 2048), (5, 1024, 1024), (5, 512, 512)
│   ├── t2/nuclear_seg: [Labels2D] DataTree[yx] (2048, 2048), (1024, 1024), (512, 512)
│   ├── t2/pheno: [Image2D] DataTree[cyx] (5, 2048, 2048), (5, 1024, 1024), (5, 512, 512)
│   ├── t2/spots/max: [Image2D] DataArray[cyx] (4, 2048, 2048)
│   ├── t2/spots/peaks: [Points2D] DataFrame (70112, 3)
│   └── t2/spots/std: [Image2D] DataArray[cyx] (1, 2048, 2048)
├── f1/ (136 elements)
├── f2/ (136 elements)
└── f3/ (136 elements)
with coordinate systems:
    ▸ 'A/1', with elements:
        f0/t2/bases, f0/t2/cell_bbox, f0/t2/cell_seg, f0/t2/iss/r1, f0/t2/iss/r2, f0/t2/iss/r10, f0/t2/nuclear_seg, f0/t2/pheno, f0/t2/spots/max, f0/t2/spots/peaks, f0/t2/spots/std, footprints, tiles
    ▸ 'A/1/f0/t2', with elements:
        f0/t2/bases, f0/t2/cell_bbox, f0/t2/cell_seg, f0/t2/iss/r1, f0/t2/iss/r2, f0/t2/iss/r10, f0/t2/nuclear_seg, f0/t2/pheno, f0/t2/spots/max, f0/t2/spots/peaks, f0/t2/spots/std
    ▸ 'plate', with elements:
        f0/t2/bases, f0/t2/cell_bbox, f0/t2/cell_seg, f0/t2/iss/r1, f0/t2/iss/r2, f0/t2/iss/r10, f0/t2/nuclear_seg, f0/t2/pheno, f0/t2/spots/max, f0/t2/spots/peaks, f0/t2/spots/std, footprints, tiles
```

Row counts in the repr are illustrative except the 859 cells; the 4 tiles and the 320 images follow from the illustrative 2 by 2 grid. Every element under a `t` collection carries one transformation per ancestor frame (D5), so the `'A/1'` and `'plate'` listings hold every element of the well, including `spots/max`, `spots/std`, and `spots/peaks`, while a `t` frame lists only the elements of that (tile, `t`). The branch prints an element under every coordinate system in its transformation dictionary (verified in `_gen_repr`).

### D11. Bases are points, bounding boxes are shapes, reads and features are tables

#### Decision

| Component in the draft | Scallops source | Element | Model | Join keys |
| --- | --- | --- | --- | --- |
| barcodes parquet with QC | `reads/reads/A1.parquet` (sequence, no location) | `A/1/reads` | table, `generic_table` | `read` (uint64) to `bases` and `spots/peaks`; `barcode` to `library` |
| base calls with locations | `reads/bases/A1.parquet` ("contains the locations") | `A/1/f0/t2/bases` | points | `read`; `cell_label` from the spatial join |
| spot detection peaks | `spot-detect.zarr/points/A1-peaks.parquet` | `A/1/f0/t2/spots/peaks` | points | `read` (SHOULD); `cell_label` |
| segmentation bounding boxes | `features/cell/A1-objects.parquet` | `A/1/f0/t2/cell_bbox` | shapes | index equals the `cell_seg` label value |
| CellProfiler features | `features/{cell,cytosol,nuclei}/A1.parquet` and `merge/A1.parquet` | `A/1/cells` | table, `feature_table` (D7) | `label` with `region`; `barcode` and `perturbation_id` to `library` |
| perturbation library | `perturbation_library.csv` (OPS standard) | `library` at the plate root | table, `condition_table` | `barcode` (unique), `perturbation_id` |

Reads table. `obs` MUST contain `read` (uint64, unique), `tile`, and `t`. It SHOULD contain `sequence`, `barcode` (nullable), `perturbation_id` (nullable), `quality`, and `qc_pass` (boolean). `qc_pass` MUST be present when any read-level QC was applied. A validator MUST check that every non-null `perturbation_id` in `reads` exists in `library`, the check D7 applies to `cells`. A read has no single location in the scallops output, so `reads` is a table. Its geometry is reached through `bases` (one location per cycle) or through `spots/peaks` (one peak per read, shared across cycles) by the `read` column.

Bases points. Columns MUST include `x`, `y`, `read`, `r` (cycle), and `base`; they SHOULD include one intensity column per base channel and `cell_label` (integer, `0` for unassigned) once the spatial join is computed. Coordinates are in the registered frame `A/1/f0/t2`. The running example carries `x`, `y`, `read`, `r`, `base`, and `cell_label`, six columns, and omits the intensity columns because the sources do not name them.

Spot peaks. `spots/peaks` columns MUST include `x` and `y` in the registered frame; they SHOULD include `read` (one peak per read, shared across cycles) and `cell_label` once the spatial join is computed. In the running example the `spots/peaks` to `cell_seg` edge is `suggested` (D9), so the element carries `x`, `y`, and `read`, three columns.

Bounding boxes. `cell_bbox` MUST have an integer index equal to the label value and a Polygon `geometry` in the registered frame. Other columns of `-objects.parquet` MAY be carried through unchanged. When `-objects.parquet` is absent the boxes MAY be derived from the labels with spatialdata `to_polygons`. A `nuclei_bbox` element from `nuclei/A1-objects.parquet` MAY be added.

Library. Columns are the OPS standard fields `barcode`, `perturbation_id`, `role` (`targeting` or `control`), and `control_type` (`non-targeting` or `intergenic`, present only when `role` is `control`, per OPS rules V-10 and V-11). Other columns of `perturbation_library.csv` MAY be carried through unchanged. The scallops `merge/A1.parquet` (perturbation per cell and the guides it came from) is not a separate element; its result is the `barcode` and `perturbation_id` columns of `cells.obs`. A writer MAY keep the evidence as `A/1/cell_calls` (`generic_table`, one row per (cell, barcode) with read counts).

Every join above MUST appear as an edge in `sp-ops:relationships` (D9), except the `cells` to `cell_seg` annotation, which `spatialdata_attrs` already declares.

#### Rationale

- Points for anything with a location per row, shapes for anything with a geometry per row, tables for everything else. This is the spatialdata model boundary applied without exceptions.
- The scallops layout says `reads` "contains the string called sequence" and joins to `bases`, which "contains the locations", through the uint64 `read`. Making `reads` a points element would require inventing one location per read.
- Putting `barcode` and `perturbation_id` on the cell table makes the OPS `cell_data.parquet` export a concatenation (D7).
- Per-(tile, `t`) points live in one registered frame, so a spatial join against `cell_seg` needs no per-row frame selection.

#### Rejected alternatives

- `reads` as points. See above.
- `cell_bbox` as an ngio `masking_roi_table`. Same geometry, but no `polygon_query` and no viewer overlay in spatialdata.
- A well-level `cells` shapes element. `cell_bbox` per (tile, `t`) plus (`region`, `label`) suffices.
- The library once per well. The OPS standard ships one library per aggregation, and the audited submission uses the same library for all 88 datasets.

#### Depends on

None for the models. The relationships proposal for the edges.

#### Example

```python
import dask.dataframe as dd
import geopandas as gpd
import pandas as pd
from spatialdata.models import PointsModel, ShapesModel

bases = PointsModel.parse(
    dd.from_pandas(pd.read_parquet("ops/reads/bases/A1.parquet"), npartitions=1),
    coordinates={"x": "x", "y": "y"},
)
cell_bbox = ShapesModel.parse(gpd.read_parquet("ops/features/cell/A1-objects.parquet").set_index("label"))
sdata["A/1/f0/t2/bases"] = bases                 # proposed API
sdata["A/1/f0/t2/cell_bbox"] = cell_bbox

# follow one read to its cell with v0.8.0 operations only
reads = sdata["A/1/reads"].obs
one_read = reads.loc[reads["barcode"] == "ACGTACGTAC"].iloc[0]["read"]      # illustrative barcode
bases_df = sdata["A/1/f0/t2/bases"].compute()
labels = bases_df.loc[bases_df["read"] == one_read, "cell_label"].unique()
cells = sdata["A/1/cells"]
cells[cells.obs["label"].isin(labels)].obs[["cell_uid", "barcode", "perturbation_id"]]
```

Assigning a perturbation per cell by the most frequent barcode among its reads, after the `bases` to `cell_seg` edge has filled `cell_label`.

```python
library = sdata["library"].obs.set_index("barcode")["perturbation_id"]
joined = bases_df.merge(reads[["read", "barcode"]], on="read", how="inner")
joined["perturbation_id"] = joined["barcode"].map(library)
per_cell = joined[joined["cell_label"] > 0].groupby("cell_label")["perturbation_id"].agg(lambda s: s.mode().iat[0])
```

### D12. The running example uses real names where the sources have them

#### Decision

The tables in the [running example](#running-example) are the single source for every page. Real values are taken from the scallops layout and the Biohub submission audit. Illustrative values exist only to make shapes concrete and MUST be labelled as such wherever a page prints them. The plate identifier and the bucket path of the audited submission MUST NOT appear in the published pages. If the author confirms the identifier is publishable, `ops_plate` is replaced by it on this page only, and other pages follow.

The canonical channel order is `DAPI, A, G, C, T` for ISS and `DAPI, GFP, stain_3, stain_4, stain_5` for the phenotypic round. The order is a choice of this specification; `sp-ops:channels` is authoritative over position, and a depositor MAY use fewer than four base channels.

#### Rationale

- Real numbers keep the example honest about scale: a stitched well is `(6, 104650, 105144)` float32 at 0.325 micrometre, 650 GB of pixels, and a 2048 by 2048 window holds 859 cells.
- Real names (`nuclear_seg`, `cell_seg`, `A1-peaks.parquet`, `read`) let a page writer check a claim against the sources.
- Real gene symbols (`AARS1` against retired `AARS`) motivate the validator rule of D7.

#### Rejected alternatives

- Printing the real plate identifier. Forbidden by the repository owner's policy for public repositories.
- Using the real six-channel stitched image as the tile example. It hides the tile and cycle structure the specification exists to describe.
- Channel order `A, G, C, T, DAPI` as the draft lists it. Either order is valid; DAPI first keeps the anchor channel at index 0 in every acquisition.

#### Depends on

None.

#### Example

See the [running example](#running-example) tables and the D2 directory tree.

## Extension key registry

All identifiers below are proposals of this specification. They are the complete extension surface; nothing else is added.

| Identifier | Kind | Applies to | Type | Required | Meaning |
| --- | --- | --- | --- | --- | --- |
| `sp-ops:spec` | attribute key | plate group (0.5) or plate node (RFC-8) | `{"version": string, "profile": "tiled" or "stitched"}` | MUST | version of this specification the store follows and the profile |
| `sp-ops:acquisitions` | attribute key | plate group or plate node | array of `{"id", "kind", "t", "r", "anchor"}`; `kind` in `iss`, `pheno`, `merged`; `r` null unless `kind` is `iss` | MUST | what each core acquisition is; `id` matches the core id of the same document |
| `sp-ops:tile` | attribute key | tile collection (RFC-8) or image group (0.5) | `{"index": integer}` | MUST in the `tiled` profile | the tile a node belongs to; equals `tiles` index |
| `sp-ops:tileLayout` | attribute key | well collection | RFC-8 `Reference` | MUST in the `tiled` profile | the `sp-ops:shapes` node holding the tile layout |
| `sp-ops:timepoint` | attribute key | `t` collection | `{"index": integer}`; MAY add `"time": number, "unit": string`, and `unit` MUST accompany `time` | MUST | the fixation timepoint of the collection |
| `sp-ops:registration` | attribute key | `t` collection | `{"anchorChannel": string, "reference": Reference}` | SHOULD (`anchorChannel` MUST when present) | the channel used for registration and an optional per-tile override of the reference image |
| `sp-ops:channels` | attribute key | image group or multiscale node | array of `{"name", "role", "base"}`; `role` in `nuclear`, `base`, `stain`, `other`; exactly one `nuclear` channel per acquisition | MUST | channel identity and role, authoritative over position |
| `sp-ops:table` | attribute key | table node | `{"type", "tableVersion", "granularity", "region"}` | MUST on every table node | ngio table type, version, row unit, and optional region reference |
| `sp-ops:relationships` | attribute key | plate and well groups (0.5); any collection node (RFC-8) | `{"version": string, "edges": array}` | SHOULD | join and spatial join edges between elements |
| `sp-ops:shapes` | node type | collection nodes | leaf node with `id` and `path`, no `nodes` | as needed | a spatialdata `ShapesModel` element (GeoParquet inside a Zarr group) |
| `sp-ops:points` | node type | collection nodes | leaf node with `id` and `path`, no `nodes` | as needed | a spatialdata `PointsModel` element |
| `sp-ops:table` | node type | collection nodes | leaf node with `id` and `path`, no `nodes` | as needed | a spatialdata `TableModel` element (AnnData) |
| path types | none | | | | every element is a Zarr group, so the core `zarr` and `json` path types suffice |
| coordinate transformation types | none | | | | RFC-5 `identity`, `scale`, `translation`, `affine`, `byDimension` cover registration and stitching |

## Sources

- [OME-NGFF RFC-8: Collections and Extensibility](https://ngff.openmicroscopy.org/rfc/8/index.html#high-content-screening-hcs-metadata): Node, Collection, Path, Reference, scene, labels, HCS plate, well, and acquisition attributes, wide and tall examples, extension naming, performance note; status D1.
- [OME-NGFF RFC index](https://ngff.openmicroscopy.org/rfc/index.html): entry point for RFC-5 (coordinate systems, transformation types including `affine`, `translation`, `byDimension`, scene storage, multiscales axis rules; status S4, version 0.6.dev3).
- [OME-NGFF dev specification, plate metadata](https://ngff.openmicroscopy.org/specifications/dev/index.html#plate-metadata): `acquisitions`, `columns`, `rows`, `wells`, `field_count`, `name`, with the two-acquisition example.
- [OME-NGFF dev specification, well metadata](https://ngff.openmicroscopy.org/specifications/dev/index.html#well-metadata): `well.images[].path` and `acquisition`, path character rules.
- [OME-NGFF 0.5](https://ngff.openmicroscopy.org/0.5/) and its [HCS layout](https://ngff.openmicroscopy.org/0.5/#hcs-layout): the released version the OPS data standard requires.
- [scallops and Biohub OPS layout (HackMD)](https://hackmd.io/@D9GB-ZDcTQyFd7U5aMmk5g/r18soYBuzx): real pipeline output names, cycles, `t=` folders, features, merge, segment, spot-detect, reads and bases joined by `read`.
- Chan Zuckerberg Initiative (CZI) OPS data standard v0.1.0 (draft) and the conformance check of a public Biohub submission. They supply `cell_data.parquet` (`cell_uid`, `perturbation_id`), `perturbation_library.csv` (`barcode`, `perturbation_id`, `role`, `control_type`), rules V-10 and V-11, the OME-NGFF 0.5 HCS requirement, and the audited store facts. No public URL appears in the source material.
- [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119.txt): the meaning of MUST, SHOULD, and MAY.
- [spatialdata documentation](https://spatialdata.scverse.org/en/stable/): v0.8.0 public API used here, `rasterize`, `transform`, `get_extent`, `set_transformation`, `get_transformation`, `get_transformation_between_coordinate_systems`, `join_spatialelement_table`, `filter_by_table_query`, `TableModel.parse`, `to_polygons`, models.
- [spatialdata tables tutorial](https://spatialdata.scverse.org/en/stable/tutorials/notebooks/notebooks/examples/tables.html): the `region`, `region_key`, `instance_key` annotation model.
- [Hierarchical SpatialData slides](https://raw.githubusercontent.com/LucaMarconato/spatialdata/refs/heads/vibecoded-experiment/hierarchical-spatialdata/slides-hierarchical-spatialdata.html): `/` in element names, sub-views, `elements=` constructor, tree repr, flat Zarr layout with `element_type`.
- [ngio table specifications](https://biovisioncenter.github.io/ngio/stable/table_specs/overview/): `generic_table`, `roi_table`, `masking_roi_table`, `feature_table`, `condition_table`, feature type vocabulary, table group attributes.
- [Padua hackathon issue 6](https://github.com/scverse/2026_04_hackathon_padua/issues/6) and its [scverse project view](https://github.com/orgs/scverse/projects/70/views/1?reload=1&pane=issue&itemId=169148807&issue=scverse%7C2026_04_hackathon_padua%7C6): the `spatialdata_elements_graph` prototype with `from`, `to`, `method`, `params`.
- [Venice hackathon relationships prototype](https://github.com/BiocCodingCollaborations/VeniceHackathon2026/tree/main/interoperability/relationships): `element_relationships`, `join_strategy` values, `sjoin_suggestions`, `query()` and `check_relationships()` sketches.
- [anndata documentation](https://anndata.readthedocs.io): `obs`, `var`, `uns`, `obsm`, `obsp`, `to_df`.
