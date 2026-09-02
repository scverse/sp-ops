# Plates, wells, and acquisitions

This page specifies the top of an sp-ops store for optical pooled screening (OPS) data. It defines the four levels plate, well row, well column, and acquisition. It then gives three views of the same running example plate `ops_plate.zarr`. The first is the on-disk layout as an Open Microscopy Environment Next-Generation File Format (OME-NGFF) 0.5 high-content screening (HCS) plate. The second is the planned request for comments 8 (RFC-8) collection view. The third is the hierarchical SpatialData view. A separate section shows the `stitched` profile of the audited Biohub store, which holds one merged image per well. The names and counts come from the [running example](design-decisions.md#running-example) in the design record.

## The hierarchy is plate, well row, well column, acquisition

An OPS plate is imaged many times. Each pass of the microscope over the plate is one acquisition. In OPS an acquisition is the triple (kind, `t`, `r`). `kind` is `iss` for an in situ sequencing (ISS) cycle, `pheno` for a phenotypic round, or `merged` for one stitched image per well assembled after registration ([design record D2](design-decisions.md#d2-plates-and-wells-stay-valid-ome-ngff-05-the-rfc-8-view-is-a-sidecar)). `t` is a fixation timepoint. `r` is the ISS cycle and is `null` for `pheno` and `merged`. The `t` values are folder labels from the scallops layout, not measured timepoints (see the [design record warning](design-decisions.md#running-example)).

```{mermaid}
graph TD
  P["Plate ops_plate"] --> R["Row A"]
  R --> W1["Well A/1"]
  R --> W2["Well A/2"]
  R --> W3["Well A/3"]
  W1 --> Q1["Acquisition iss-t2-r1"]
  W1 --> Q2["Acquisition iss-t2-r2"]
  W1 --> Q3["Acquisition pheno-t2"]
  W1 --> Q4["77 more acquisitions"]
  Q1 --> I0["image f0-t2-iss-r1"]
  Q1 --> I1["image f1-t2-iss-r1"]
  Q1 --> I2["image f2-t2-iss-r1"]
  Q1 --> I3["image f3-t2-iss-r1"]
```

Each level holds a fixed set of things.

| Level | On disk | What it holds for OPS |
| --- | --- | --- |
| Plate | the store root group `ops_plate.zarr/` with `ome.plate` | the row, column, well, and acquisition lists; `sp-ops:spec`, `sp-ops:acquisitions`, and (SHOULD) `sp-ops:relationships`; the `library` table; optional `well_features` table and `wells` shapes |
| Well row | the folder `A/` | a Zarr group with no OME metadata of its own |
| Well column | the well group `A/1/` with `ome.well` | the list of images with their acquisition; `sp-ops:relationships` (SHOULD); the `tiles`, `footprints`, `images`, `fov_features`, `cells`, and `reads` elements; every image, label, point, and shape element of the well |
| Acquisition | one entry in `ome.plate.acquisitions`; one image per tile in each well | one microscope pass, identified by (kind, `t`, `r`); the images of one acquisition are unaligned with those of any other until registration |

The following rules of this specification apply at these levels. They restate the design record [D1](design-decisions.md#d1-the-extension-prefix-is-sp-ops-with-nine-attribute-keys-and-three-node-types) and [D2](design-decisions.md#d2-plates-and-wells-stay-valid-ome-ngff-05-the-rfc-8-view-is-a-sidecar).

1. The acquisition name MUST be `iss-t<t>-r<r>` for an ISS cycle, `pheno-t<t>` for a phenotypic round, and `merged-t<t>` for a `merged` acquisition. A writer MUST NOT use `merged` when the raw acquisitions are stored; it then stores the registered product under `reg/` ([design record D6](design-decisions.md#d6-resampling-uses-the-largest-contained-box-by-default)).
2. There MUST be one `ome.plate.acquisitions` entry per (kind, `t`, `r`) triple. Registered or resampled images are derived nodes, not acquisitions.
3. A writer MUST use the `tiled` profile when a well has more than one tile. It MUST use the `stitched` profile when each acquisition yields one image per well. The profile is declared in `sp-ops:spec.profile`. The [stitched profile section](#the-stitched-profile-of-the-audited-biohub-store) below shows the second profile.
4. `sp-ops:acquisitions` on the plate is the single source of truth for `kind` (`iss`, `pheno`, or `merged`), `t`, `r`, and `anchor` of every acquisition. Images carry only the acquisition reference.
5. The 0.5 metadata is authoritative for rows, columns, wells, acquisitions, and image paths. Any other view of the plate MUST agree with it.
6. Every `acquisitions` entry MUST set `maximumfieldcount` to the number of `ome.well.images` entries it contributes to one well, which is the number of tiles per well when its channels are stacked. `field_count` MUST equal the largest number of `ome.well.images` entries in any well.

The running example has one row, three columns, and four illustrative tiles per well in a 2 by 2 grid. The counts below follow from the acquisition rule and the [element list](design-decisions.md#hierarchical-element-paths) of the design record.

```text
ISS cycles r            1, 2, 3, 4, 5, 7, 8, 9, 10     (no cycle 6; real, scallops)
timepoints t            2, 3, 4, 5, 7, 8, 9, 10        (folder labels, scallops)
acquisitions            80 = 8 t x (9 ISS cycles + 1 phenotypic round)
images per well         320 = 4 tiles x 80 acquisitions
children of A/ (repr)   1650 = 3 wells x 550 elements per well
coordinate systems      100 = 96 (tile, t) frames + 3 well frames + plate
real row counts         859 cells in one window, 4211 library rows
illustrative counts     4 tiles and 320 images, which follow from the 2 by 2 tile grid
```

## On-disk layout follows the OME-NGFF plate and well specification

The plate and well groups carry OME-NGFF HCS metadata unchanged. This is existing behaviour. The tables below reproduce the wording of the [plate metadata](https://ngff.openmicroscopy.org/specifications/dev/index.html#plate-metadata) and [well metadata](https://ngff.openmicroscopy.org/specifications/dev/index.html#well-metadata) sections of the development specification (0.6rc0). Version 0.5 defines the same plate and well keys. The running example writes `"version": "0.5"` because the OPS data standard v0.1.0 requires OME-NGFF 0.5. The requirement column is the NGFF wording, not a rule of this specification.

Plate keys, all inside `ome.plate`.

| Key | NGFF requirement | NGFF semantics |
| --- | --- | --- |
| `rows` | MUST | "an array of JSON objects defining the rows of the plate"; each row MUST contain a `name` that "MUST contain only alphanumeric characters, MUST be case-sensitive, and MUST NOT be a duplicate of any other name in the rows array" |
| `columns` | MUST | "an array of JSON objects defining the columns of the plate"; each column MUST contain a `name` with the same character rules as rows |
| `wells` | MUST | "a list of JSON objects defining the wells of the plate"; each well MUST contain `path`, `rowIndex`, and `columnIndex`; the path "MUST consist of a name in the rows array, a file separator (/), and a name from the columns array, in that order"; the indices "MUST be 0-based" |
| `acquisitions` | MAY | "an array of JSON objects defining the acquisitions for a given plate to which wells can refer to"; each MUST contain an `id` that is "an unique integer identifier greater than or equal to 0"; each SHOULD contain `name` and `maximumfieldcount`; each MAY contain `description`, `starttime`, and `endtime` |
| `field_count` | SHOULD | "a positive integer defining the maximum number of fields per view across all wells" |
| `name` | SHOULD | "a string defining the name of the plate" |

Well keys, all inside `ome.well`.

| Key | NGFF requirement | NGFF semantics |
| --- | --- | --- |
| `images` | MUST | "an array of JSON objects specifying all fields of views for a given well" |
| `images[].path` | MUST | "a string specifying the path to the field of view"; it "MUST NOT be an empty string and MUST NOT contain / characters" and "MUST only use characters in the sets a-z, A-Z, 0-9, -, _, ." |
| `images[].acquisition` | MUST when the plate has multiple acquisitions | "an integer identifying the acquisition which MUST match one of the acquisition JSON objects defined in the plate metadata" |

Two consequences shape the layout. First, `images[].path` cannot contain `/`, so every image is a direct child of the well. The image name MUST be the flattened element path of [design record D10](design-decisions.md#d10-element-names-are-the-on-disk-paths-and-a-hyphen-flattens-them-for-v080). It is `<tile>-t<t>-iss-r<r>` for an ISS cycle and `<tile>-t<t>-pheno` for a phenotypic round, for example `f0-t2-iss-r1`. In the `stitched` profile the tile component is omitted, giving `t2-iss-r1`, `t2-pheno`, and `t2-merged`. A `stitched` well with exactly one acquisition MAY name its image `0`, which is what the audited Biohub store does (see the [stitched profile section](#the-stitched-profile-of-the-audited-biohub-store)). Second, `field_count` counts images, not tiles. In the NGFF example two acquisitions with `maximumfieldcount` 2 give `field_count` 4 and a well with four images. The running example therefore has `field_count` 320 and `maximumfieldcount` 4.

In the 0.5 layout the `sp-ops:*` attribute keys MUST sit in the group `attributes` object as siblings of `ome` (design record D1). The audited store already places its own sibling key (`channels_metadata`) there. Labels live at `<image>/labels/<name>` under the image they were computed from, as 0.5 requires. Points, shapes, and tables have no home in 0.5 HCS metadata. They are extra groups in the well or at the plate root, and OME-NGFF 0.5 does not forbid extra groups. The audited submission passed the OPS validator with images only; extra groups have not been tested against that validator (design record D2).

### Directory tree of the running example

The tree shows the `tiled` profile. Only tile `f0` at `t2` is expanded in well `A/1`. Every image folder is one `ome.well.images` entry. The two `collection.json` files are the proposed RFC-8 sidecars described in the next section.

```text
ops_plate.zarr/                          # plate
├── zarr.json                            # ome.plate (0.5); sp-ops:spec, sp-ops:acquisitions, sp-ops:relationships
├── collection.json                      # (proposed) RFC-8 plate collection
├── library/                             # table, condition_table: barcode, perturbation_id, role, control_type
├── well_features/                       # table, feature_table, one row per well (MAY)
├── wells/                               # shapes, one rectangle per well (MAY)
└── A/                                   # well row
    ├── zarr.json                        # Zarr group; the 0.5 plate and well metadata define no row-level keys
    ├── 1/                               # well column; the well A/1
    │   ├── zarr.json                    # ome.well.images: 320 entries; sp-ops:relationships
    │   ├── collection.json              # (proposed) RFC-8 well collection with tile and t collections
    │   ├── tiles/                       # shapes, 4 rows, the tile layout
    │   ├── footprints/                  # shapes, 320 rows, one per image
    │   ├── images/                      # table, 320 rows, annotates footprints
    │   ├── fov_features/                # table, 320 rows, annotates footprints (MAY)
    │   ├── cells/                       # table, annotates every cell_seg in the well
    │   ├── reads/                       # table, one row per read
    │   ├── f0-t2-iss-r1/                # acquisition 0, tile f0; ome.multiscales (c, y, x); sp-ops:tile, sp-ops:channels
    │   ├── f0-t2-iss-r2/                # acquisition 1
    │   ├── f0-t2-iss-r3/                # acquisition 2
    │   ├── ...                          # f0-t2-iss-r4, r5, r7, r8, r9, r10 (acquisitions 3 to 8)
    │   ├── f0-t2-pheno/                 # acquisition 9
    │   │   ├── zarr.json
    │   │   ├── 0/ 1/ 2/                 # pyramid levels
    │   │   └── labels/
    │   │       ├── zarr.json            # ome.labels: ["nuclear_seg", "cell_seg"]
    │   │       ├── nuclear_seg/         # int32
    │   │       └── cell_seg/            # int32
    │   ├── f0-t2-spots-max/             # derived image, not an acquisition
    │   ├── f0-t2-spots-std/
    │   ├── f0-t2-spots-peaks/           # points: x, y, read
    │   ├── f0-t2-bases/                 # points: x, y, read, r, base, cell_label
    │   ├── f0-t2-cell_bbox/             # shapes
    │   ├── ...                          # f0-t3-... to f0-t10-...
    │   ├── f1-t2-iss-r1/                # acquisition 0, tile f1
    │   └── ...                          # f1-..., f2-..., f3-...
    ├── 2/                               # the well A/2, same content
    └── 3/                               # the well A/3, same content
```

### Plate and well metadata of the running example

Plate `zarr.json`. Acquisition ids run from 0 to 79 in order of `t`, then ISS cycles by `r`, then the phenotypic round, the numbering D2 recommends. The store name is illustrative.

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
          {"id": 2, "name": "iss-t2-r3", "maximumfieldcount": 4},
          {"id": 3, "name": "iss-t2-r4", "maximumfieldcount": 4},
          {"id": 4, "name": "iss-t2-r5", "maximumfieldcount": 4},
          {"id": 5, "name": "iss-t2-r7", "maximumfieldcount": 4},
          {"id": 6, "name": "iss-t2-r8", "maximumfieldcount": 4},
          {"id": 7, "name": "iss-t2-r9", "maximumfieldcount": 4},
          {"id": 8, "name": "iss-t2-r10", "maximumfieldcount": 4},
          {"id": 9, "name": "pheno-t2", "maximumfieldcount": 4},
          {"id": 10, "name": "iss-t3-r1", "maximumfieldcount": 4}
          // ... ids 11 to 79 for t = 3, 4, 5, 7, 8, 9, 10
        ]
      }
    },
    "sp-ops:spec": {"version": "0.1.0-draft", "profile": "tiled"},
    "sp-ops:acquisitions": [
      {"id": 0, "kind": "iss", "t": 2, "r": 1, "anchor": true},
      {"id": 1, "kind": "iss", "t": 2, "r": 2, "anchor": false},
      {"id": 2, "kind": "iss", "t": 2, "r": 3, "anchor": false},
      // ... ids 3 to 8 for r = 4, 5, 7, 8, 9, 10 at t = 2
      {"id": 9, "kind": "pheno", "t": 2, "r": null, "anchor": false},
      {"id": 10, "kind": "iss", "t": 3, "r": 1, "anchor": true}
      // ... ids 11 to 79
    ]
  }
}
```

Well `A/1/zarr.json`. The list has one entry per image in the well, so 320 entries. The ten images of tile `f0` at `t2` and the first image of tile `f1` are shown.

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
          {"path": "f0-t2-iss-r3", "acquisition": 2},
          {"path": "f0-t2-iss-r4", "acquisition": 3},
          {"path": "f0-t2-iss-r5", "acquisition": 4},
          {"path": "f0-t2-iss-r7", "acquisition": 5},
          {"path": "f0-t2-iss-r8", "acquisition": 6},
          {"path": "f0-t2-iss-r9", "acquisition": 7},
          {"path": "f0-t2-iss-r10", "acquisition": 8},
          {"path": "f0-t2-pheno", "acquisition": 9},
          {"path": "f1-t2-iss-r1", "acquisition": 0}
          // ... 320 entries in total: 4 tiles x 80 acquisitions
        ]
      }
    }
  }
}
```

The derived groups `f0-t2-spots-max`, `f0-t2-spots-peaks`, and the others are not `images` entries. They are not acquisitions, and 0.5 HCS metadata has no list for them. The RFC-8 well document enumerates them as nodes, and the hierarchical SpatialData view lists them under the same `A/1/f0/t2/` prefix. The `images` table of the [fields of view page](fields-of-view.md) lists acquisition images only, raw or resampled. It has no row for derived spot images, points, or shapes ([design record D4](design-decisions.md#d4-timepoints-and-cycles-are-separate-elements-only-aligned-channels-are-stacked)).

### The stitched profile of the audited Biohub store

The audited Biohub submission is the `stitched` profile with one `merged` acquisition per well. It is the only real store behind the running example, so this section shows its layout with the keys this specification adds. The tiled example above stays the main one. The [stitched profile example](design-decisions.md#stitched-profile-example) of design record D2 records the same store.

`merged` is the third `kind` ([design record D2](design-decisions.md#d2-plates-and-wells-stay-valid-ome-ngff-05-the-rfc-8-view-is-a-sidecar)). A `merged` acquisition is one stitched image per well whose channels were assembled after registration from the ISS cycles and the phenotypic round of one `t`. Its name MUST be `merged-t<t>` and its `r` MUST be null. Its channels follow `sp-ops:channels`, so the ISS-derived channels carry `role: "other"`. A `merged` acquisition is already registered. It maps into the registered frame by a pure scale, and it is the anchor when it is the only acquisition at its `t` ([design record D5](design-decisions.md#d5-cycles-are-registered-to-the-dapi-channel-of-the-first-iss-cycle-at-each-timepoint)). A writer MUST NOT use `merged` when the raw acquisitions are stored; it then stores the product under `reg/` ([design record D6](design-decisions.md#d6-resampling-uses-the-largest-contained-box-by-default)). The kind exists because a 0.5 well needs a `well.images[].acquisition` for every image, and the audited store has exactly one merged image per well. The scallops layout calls the same product `stitch (pheno + iss image)`.

Real values from the audit are the well set, the image name `0`, the array shape and dtype, the five pyramid levels, the pixel size, the label names and dtype, `field_count` 1, and the plate-level `channels_metadata` key. The audited array is `[1, 6, 1, 104650, 105144]` float32 with length-one `t` and `z` axes. A conformant writer stores it as `(c, y, x)`, that is `(6, 104650, 105144)` ([design record D4](design-decisions.md#d4-timepoints-and-cycles-are-separate-elements-only-aligned-channels-are-stacked)). The `sp-ops` keys, the `collection.json` sidecars, the `library` table, the channel names, and the acquisition `t` are this specification or illustrative.

```text
ops_plate.zarr/                          # real store shape; the identifier is withheld
├── zarr.json                            # ome.plate (0.5): row A, columns 1-3, field_count 1; channels_metadata (real);
│                                        # sp-ops:spec profile stitched, sp-ops:acquisitions (this specification)
├── collection.json                      # (proposed) RFC-8 plate collection, wide layout, plate scene (D5)
├── library/                             # table, condition_table (this specification; absent in the audited store)
└── A/                                   # well row
    ├── 1/                               # the well A/1
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
    ├── 2/                               # the well A/2, same shape
    └── 3/                               # the well A/3, same shape
```

Plate `zarr.json`. One acquisition serves the whole plate, so `field_count` and `maximumfieldcount` are both 1 (rule 6). The single `sp-ops:acquisitions` entry assigns the merged image its kind. The acquisition `t` is illustrative; the audit did not record it.

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
        "field_count": 1,
        "acquisitions": [{"id": 0, "name": "merged-t2", "maximumfieldcount": 1}]
      }
    },
    // "channels_metadata": the depositor's own sibling key (real); the audit did not record its contents
    "sp-ops:spec": {"version": "0.1.0-draft", "profile": "stitched"},
    "sp-ops:acquisitions": [{"id": 0, "kind": "merged", "t": 2, "r": null, "anchor": true}]
  }
}
```

Well `A/1/zarr.json`. 0.5 lets a well omit `acquisition` when the plate has one acquisition; this specification writes it (D2 rule 3).

```json
{
  "zarr_format": 3,
  "node_type": "group",
  "attributes": {
    "ome": {"version": "0.5", "well": {"images": [{"path": "0", "acquisition": 0}]}}
  }
}
```

Image `A/1/0/zarr.json`, the extension key only. The channel names are illustrative because the audit did not record the contents of `channels_metadata`. The five phenotypic names are those of the running example. The sixth channel is ISS-derived and carries `role: "other"`.

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

In the hierarchical view the image element is `A/1/0` and its labels are `A/1/nuclear_seg` and `A/1/cell_seg` ([design record D10](design-decisions.md#d10-element-names-are-the-on-disk-paths-and-a-hyphen-flattens-them-for-v080) rule 6). The v0.8.0 flat names are `A-1-0` and `A-1-cell_seg`. The registered frame is `A/1/t2`, RFC-8 id `A-1-t2`, taken from the `t` of the acquisition entry (D5). A `stitched` store that keeps its raw acquisitions instead names its images `t2-iss-r1` to `t2-pheno`, uses `kind` `iss` and `pheno` as in the `tiled` profile, and reads them as `A/1/t2/iss/r1` to `A/1/t2/pheno`. The D10 mapping table lists both forms. In the RFC-8 view the tile level is omitted, and a well with one acquisition MAY use the wide layout (D2).

## RFC-8 collections describe the same plate as nodes

:::{admonition} Status
:class: note
Everything in this section depends on OME-NGFF RFC-8 (collections and extensibility), which is an early draft at status D1. Its HCS attributes may change before release. `"0.x"` is the placeholder version RFC-8 uses in its own examples. The `scene` attributes that RFC-8 borrows from RFC-5 (status S4) are described on the [ISS rounds page](iss-rounds.md).
:::

RFC-8 replaces the fixed plate and well dictionaries with a general node structure. Every metadata object is a `Node`. A `collection` node groups other nodes. Nodes are either inlined or referenced by a `Path`. The building blocks are listed below with the RFC-8 wording.

| Interface | Fields | RFC-8 rules |
| --- | --- | --- |
| `Node` | `type` (yes), `id` (no), `name` (yes), `attributes` (no) | `id` "MUST be a string that matches `[a-zA-Z0-9-_.]+`" and "MUST be unique within the JSON document"; `name` "MUST be unique within the enclosing collection" |
| `Collection` node | `type` = `"collection"`, `nodes` or `path`, `attributes` | "Either `nodes` or `path` MUST be present, but not both" |
| `Path` | `type` (yes), `path` (yes) | core types are `zarr` and `json`; for `zarr`, "Implementations MUST append `zarr.json` to the path"; relative paths "are interpreted relative to the json file describing the collection" |
| `Reference` | `id` (yes), `path` (no) | "For external references, the `path` field MUST be present" |

The HCS attributes of RFC-8 are `plate`, `well`, and `acquisition`. RFC-8 states that it "changes the HCS references from numeric IDs and names to string-based ID references". So an acquisition, a row, and a column each carry a string `id`, and other nodes point at them by `{"id": ...}`.

| Attribute | On which node | Fields and RFC-8 rules |
| --- | --- | --- |
| `plate` | the plate `collection` (MUST) | `rows` (yes) and `columns` (yes), arrays of `{id, name}` objects; `acquisitions` (no), an array of `{id, name}` objects; every `id` is a string matching `[a-zA-Z0-9-_.]+` |
| `well` | a well `collection` (MUST) | `row` (yes) and `column` (yes), each "a `Reference` to one of the rows [columns] listed in the `plate` attribute on the enclosing plate-level collection" |
| `acquisition` | a `multiscale` node or a `collection` sub-node | "a `Reference` to one of the acquisitions"; it "MAY be set on individual `multiscale` nodes within a well or on a `collection` sub-node grouping all images from a single acquisition" |

RFC-8 suggests two HCS layouts that "are not mutually exclusive". In the wide layout every image is a direct child of the well collection. In the tall layout images are grouped in sub-collections by acquisition. RFC-8 warns that the wide layout "can become cluttered when there are multiple acquisitions and derived nodes". A well in the running example has eighty acquisitions and many derived nodes.

This specification uses the tall layout applied by tile, then by `t` (proposed). A well collection contains one `collection` per tile marked with `sp-ops:tile`. Each tile collection contains one `collection` per `t` marked with `sp-ops:timepoint`. Inside each `t` collection the ISS cycles sit in one `collection` named `iss`. The phenotypic image, labels, points, shapes, and tables of the same fixed cells are direct children of the `t` collection. The `acquisition` reference sits on each `multiscale` node, which RFC-8 allows. In the `stitched` profile the tile level is omitted. A `stitched` well with exactly one acquisition MAY use the wide layout.

The 0.5 metadata and the RFC-8 view cannot share one `zarr.json`. Both live under the `ome` attribute, and 0.5 requires `"version": "0.5"` while an RFC-8 root node carries its own version. The RFC-8 view is therefore a standalone JSON document named `collection.json` (proposed). One sits at the plate root and one at each well root. The plate document reaches each well document through the RFC-8 path type `json`. The well document inlines its tile and `t` collections. The sidecar MUST agree with the 0.5 metadata, and a validator MUST report any disagreement. When RFC-8 is released, the same node objects MAY move into the `zarr.json` of nested Zarr groups and the sidecars become unnecessary.

The two dialects map onto each other by name.

| OME-NGFF 0.5 | RFC-8 (proposed) |
| --- | --- |
| `ome.plate.rows[].name` `"A"` | `plate.rows[]` `{"id": "A", "name": "A"}` |
| `ome.plate.columns[].name` `"1"` | `plate.columns[]` `{"id": "1", "name": "1"}` |
| `ome.plate.wells[]` `{"path": "A/1", ...}` | a `collection` node with `path` `./A/1/collection.json`; the referenced well document carries the `well` attribute, whose `row` and `column` references point back into the plate document |
| `ome.plate.acquisitions[].id` `0`, `name` `"iss-t2-r1"` | `plate.acquisitions[]` `{"id": "iss-t2-r1", ...}`; the string id equals the 0.5 name |
| `ome.well.images[]` `{"path": "f0-t2-iss-r1", "acquisition": 0}` | a `multiscale` node at `./f0-t2-iss-r1` with `"acquisition": {"id": "iss-t2-r1", ...}` inside the `f0`, `t2`, and `iss` collections |
| `<image>/labels/cell_seg` | a `multiscale` node at `./f0-t2-pheno/labels/cell_seg` with `"labels": {"source": [{"id": "A-1-f0-t2-pheno"}]}` |
| `sp-ops:acquisitions[].id` integer | `sp-ops:acquisitions[].id` string, equal to the acquisition id of the same document |

Node ids are the hierarchical element names with `/` replaced by `-`, so `A/1/f0/t2/iss/r1` becomes `A-1-f0-t2-iss-r1` ([design record D10](design-decisions.md#d10-element-names-are-the-on-disk-paths-and-a-hyphen-flattens-them-for-v080)). RFC-8 requires node ids and coordinate system ids each to be unique within one JSON document. The well document uses `A-1` and `A-1-f0-t2` both as node ids and, in its `scene`, as coordinate system ids (design record D5). Whether the two id spaces are shared is not stated in RFC-8 and is an open question for its authors.

### Plate collection of the running example

Plate `collection.json` (proposed), stored next to the plate `zarr.json`. Three of the eighty acquisitions are shown. The `scene` attribute defines the OPTIONAL coordinate system `plate` and one `translation` per well, from each well frame to `plate` ([design record D5](design-decisions.md#d5-cycles-are-registered-to-the-dapi-channel-of-the-first-iss-cycle-at-each-timepoint)). The well frames are defined in the well documents, so every `input` is a cross-document RFC-8 `Reference` and MUST carry both `id` and `path`. The translation is `[y, x]` in micrometres. The values are illustrative; they exceed the 34 millimetre width of the real stitched well image, so the wells do not overlap.

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
          // ... 80 acquisitions in total
        ]
      },
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
      },
      "sp-ops:spec": {"version": "0.1.0-draft", "profile": "tiled"},
      "sp-ops:acquisitions": [
        {"id": "iss-t2-r1", "kind": "iss", "t": 2, "r": 1, "anchor": true},
        {"id": "iss-t2-r2", "kind": "iss", "t": 2, "r": 2, "anchor": false},
        {"id": "pheno-t2", "kind": "pheno", "t": 2, "r": null, "anchor": false}
        // ... 80 entries in total
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

### Well collection of the running example

Well `A/1/collection.json` (proposed). Paths are relative to the well folder, so `./f0-t2-iss-r1` is the same image group that `ome.well.images` lists. The `scene` attribute of the `t2` collection and the `sp-ops:relationships` attribute are omitted here; the [ISS rounds page](iss-rounds.md) and the [joinable components page](joinable-components.md) show them. References to rows, columns, and acquisitions cross into the plate document. They therefore carry a `path` to it, as RFC-8 requires for external references (design record D5).

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
      {"type": "sp-ops:table", "id": "A-1-fov_features", "name": "fov_features", "path": {"type": "zarr", "path": "./fov_features"},
       "attributes": {"sp-ops:table": {"type": "feature_table", "tableVersion": "1", "granularity": "image",
                                       "region": {"id": "A-1-footprints"}}}},  // MAY
      {"type": "sp-ops:table", "id": "A-1-cells", "name": "cells", "path": {"type": "zarr", "path": "./cells"},
       "attributes": {"sp-ops:table": {"type": "feature_table", "tableVersion": "1", "granularity": "cell",
                                       "region": [{"id": "A-1-f0-t2-cell_seg"}]}}},  // ... one cell_seg per (tile, t)
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
              // ... r3, r4, r5, r7, r8, r9, r10
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
            // ... nuclear_seg, spots/max, spots/std, spots/peaks
          ]}
         // ... t3, t4, t5, t7, t8, t9, t10
       ]}
      // ... tiles f1, f2, f3
    ]
  }
}
```

Inlining the tile and `t` collections keeps the number of metadata requests small. RFC-8 notes that "Assembling a collection from path-referenced nodes requires one metadata request per node". A reader of the plate document therefore makes one request per well plus one per element it opens.

## The SpatialData view is a tree

:::{admonition} Status
:class: note
The tree view depends on hierarchical SpatialData, an experimental branch by Luca Marconato. Its slides state, of the application programming interface (API), "This represents an experimental phase. The API may evolve." It is not released. It allows `/` in element names, groups them in the repr, and returns a sub-view for a prefix. spatialdata v0.8.0 rejects `/` in a name. In v0.8.0 the same store is read with flattened names such as `A-1-f0-t2-iss-r1` and the current flat repr ([design record D10](design-decisions.md#d10-element-names-are-the-on-disk-paths-and-a-hyphen-flattens-them-for-v080)).
:::

In the hierarchical view an element name is its Zarr path relative to the store root in the collections layout (proposed). In the 0.5 layout shown above, the reader derives the name from the flattened path by two rules of [design record D10](design-decisions.md#d10-element-names-are-the-on-disk-paths-and-a-hyphen-flattens-them-for-v080). A `-` below the well becomes `/`, and a label at `<image>/labels/<name>` is named beside its image. So `A/1/f0-t2-iss-r1` is read as `A/1/f0/t2/iss/r1`, and `A/1/f0-t2-pheno/labels/cell_seg` as `A/1/f0/t2/cell_seg`. The branch reader alone, which scans for `spatialdata_attrs.element_type`, would name the element `A/1/f0-t2-iss-r1`. The repr follows `_gen_repr` on the branch. Flat elements (no `/`) come first. Grouped elements collapse under a `folder/ (N elements)` header, where the folder is the first path component only. Each element line reads `name: [Type] Class shape`. Image and label lines add the axis names after the class, for example `DataTree[cyx]`. A `DataTree` lists the shape of every pyramid level. The block `with coordinate systems:` lists every coordinate system and the elements that carry a transformation to it. Names sort in natural order, so `r10` follows `r9`, and `1/footprints` sorts after every `1/f<n>/...` element because `/f` is a prefix of `/footprints`.

At the plate level the first path component is the row, so every element of the three wells collapses under one `A/` header. The listing below is abbreviated. It shows the plate-level elements, then `cells` and tile `f0` at `t2` of well `A/1`. It continues with the remaining well-level elements of `A/1` and the first element of `A/2`. The elements of `A/1/f0/t3` to `A/1/f3/t10` sort between `1/f0/t2/spots/std` and `1/footprints` and are left out, as is the rest of `A/2` and `A/3`. A real repr prints every child of `A/` and every coordinate system. The totals are in the counts block above and in the [derived counts](design-decisions.md#derived-counts) of the design record. Row counts in the repr are illustrative except the 859 cells and the 4211 library rows; the 4 tiles and the 320 images follow from the illustrative 2 by 2 grid.

```text
SpatialData object at /data/ops_plate.zarr
├── library: [Table] AnnData (4211, 0)
├── well_features: [Table] AnnData (3, 8)
├── wells: [Shapes] GeoDataFrame (3, 4)
└── A/ (1650 elements)
    ├── 1/cells: [Table] AnnData (27488, 1400)
    ├── 1/f0/t2/bases: [Points2D] DataFrame (612340, 6)
    ├── 1/f0/t2/cell_bbox: [Shapes] GeoDataFrame (859, 1)
    ├── 1/f0/t2/cell_seg: [Labels2D] DataTree[yx] (2048, 2048), (1024, 1024), (512, 512)
    ├── 1/f0/t2/iss/r1: [Image2D] DataTree[cyx] (5, 2048, 2048), (5, 1024, 1024), (5, 512, 512)
    ├── 1/f0/t2/iss/r2: [Image2D] DataTree[cyx] (5, 2048, 2048), (5, 1024, 1024), (5, 512, 512)
    ├── 1/f0/t2/iss/r3: [Image2D] DataTree[cyx] (5, 2048, 2048), (5, 1024, 1024), (5, 512, 512)
    ├── 1/f0/t2/iss/r4: [Image2D] DataTree[cyx] (5, 2048, 2048), (5, 1024, 1024), (5, 512, 512)
    ├── 1/f0/t2/iss/r5: [Image2D] DataTree[cyx] (5, 2048, 2048), (5, 1024, 1024), (5, 512, 512)
    ├── 1/f0/t2/iss/r7: [Image2D] DataTree[cyx] (5, 2048, 2048), (5, 1024, 1024), (5, 512, 512)
    ├── 1/f0/t2/iss/r8: [Image2D] DataTree[cyx] (5, 2048, 2048), (5, 1024, 1024), (5, 512, 512)
    ├── 1/f0/t2/iss/r9: [Image2D] DataTree[cyx] (5, 2048, 2048), (5, 1024, 1024), (5, 512, 512)
    ├── 1/f0/t2/iss/r10: [Image2D] DataTree[cyx] (5, 2048, 2048), (5, 1024, 1024), (5, 512, 512)
    ├── 1/f0/t2/nuclear_seg: [Labels2D] DataTree[yx] (2048, 2048), (1024, 1024), (512, 512)
    ├── 1/f0/t2/pheno: [Image2D] DataTree[cyx] (5, 2048, 2048), (5, 1024, 1024), (5, 512, 512)
    ├── 1/f0/t2/spots/max: [Image2D] DataArray[cyx] (4, 2048, 2048)
    ├── 1/f0/t2/spots/peaks: [Points2D] DataFrame (70112, 3)
    ├── 1/f0/t2/spots/std: [Image2D] DataArray[cyx] (1, 2048, 2048)
    ├── 1/footprints: [Shapes] GeoDataFrame (320, 1)
    ├── 1/fov_features: [Table] AnnData (320, 12)
    ├── 1/images: [Table] AnnData (320, 0)
    ├── 1/reads: [Table] AnnData (1203456, 0)
    ├── 1/tiles: [Shapes] GeoDataFrame (4, 4)
    ├── 2/cells: [Table] AnnData (27488, 1400)
with coordinate systems:
    ▸ 'A/1', with elements:
        A/1/f0/t2/bases, A/1/f0/t2/cell_bbox, A/1/f0/t2/cell_seg, A/1/f0/t2/iss/r1, A/1/f0/t2/iss/r2, A/1/f0/t2/iss/r3, A/1/f0/t2/iss/r4, A/1/f0/t2/iss/r5, A/1/f0/t2/iss/r7, A/1/f0/t2/iss/r8, A/1/f0/t2/iss/r9, A/1/f0/t2/iss/r10, A/1/f0/t2/nuclear_seg, A/1/f0/t2/pheno, A/1/f0/t2/spots/max, A/1/f0/t2/spots/peaks, A/1/f0/t2/spots/std, A/1/footprints, A/1/tiles
    ▸ 'A/1/f0/t2', with elements:
        A/1/f0/t2/bases, A/1/f0/t2/cell_bbox, A/1/f0/t2/cell_seg, A/1/f0/t2/iss/r1, A/1/f0/t2/iss/r2, A/1/f0/t2/iss/r3, A/1/f0/t2/iss/r4, A/1/f0/t2/iss/r5, A/1/f0/t2/iss/r7, A/1/f0/t2/iss/r8, A/1/f0/t2/iss/r9, A/1/f0/t2/iss/r10, A/1/f0/t2/nuclear_seg, A/1/f0/t2/pheno, A/1/f0/t2/spots/max, A/1/f0/t2/spots/peaks, A/1/f0/t2/spots/std
    ▸ 'plate', with elements:
        A/1/f0/t2/bases, A/1/f0/t2/cell_bbox, A/1/f0/t2/cell_seg, A/1/f0/t2/iss/r1, A/1/f0/t2/iss/r2, A/1/f0/t2/iss/r3, A/1/f0/t2/iss/r4, A/1/f0/t2/iss/r5, A/1/f0/t2/iss/r7, A/1/f0/t2/iss/r8, A/1/f0/t2/iss/r9, A/1/f0/t2/iss/r10, A/1/f0/t2/nuclear_seg, A/1/f0/t2/pheno, A/1/f0/t2/spots/max, A/1/f0/t2/spots/peaks, A/1/f0/t2/spots/std, A/1/footprints, A/1/tiles, A/2/footprints, A/2/tiles, A/3/footprints, A/3/tiles, wells
```

The coordinate systems are those of the [design record D5](design-decisions.md#d5-cycles-are-registered-to-the-dapi-channel-of-the-first-iss-cycle-at-each-timepoint). There is one registered frame per (tile, `t`), one well frame per well, and an optional `plate` frame. Every element under a `t` collection carries one transformation per ancestor frame (D5). The `'A/1'` and `'plate'` listings therefore hold every element of the well, including `spots/max`, `spots/std`, and `spots/peaks`, while a `t` frame lists only the elements of that (tile, `t`). The branch prints an element under every coordinate system in its transformation dictionary (verified in its `_gen_repr`). In this abbreviated listing the elements of `A/1/f0/t3` to `A/3/f3/t10`, the coordinate systems that go with them, and the well frames `'A/2'` and `'A/3'` are left out. Coordinate system names containing `/` are unverified in spatialdata v0.8.0 ([design record D10](design-decisions.md#d10-element-names-are-the-on-disk-paths-and-a-hyphen-flattens-them-for-v080)); the RFC-8 ids `A-1` and `A-1-f0-t2` of D5 are the fallback spelling.

The plate-level repr hides the tile structure because the branch groups by the first path component only. A sub-view restores it. Indexing with a prefix returns a `SpatialData` whose element names have the prefix stripped, and the same element objects are shared with the parent. The repr of the `A/1` sub-view, grouped by tile, is shown under [design record D10](design-decisions.md#d10-element-names-are-the-on-disk-paths-and-a-hyphen-flattens-them-for-v080).

```python
from spatialdata import SpatialData

sdata = SpatialData.read("ops_plate.zarr")               # proposed API: hierarchical branch plus the D10 un-flattening rule
well = sdata["A/1"]                                       # proposed API: sub-view, prefix "A/1/" stripped
sorted(well.tables)                                       # ['cells', 'fov_features', 'images', 'reads']
well["tiles"] is sdata["A/1/tiles"]                       # proposed API: True, the sub-view shares the GeoDataFrame
well["f0"]["t2"]["iss/r1"] is sdata["A/1/f0/t2/iss/r1"]   # proposed API: True, nested sub-views
"A/2" in sdata                                            # proposed API: True, a prefix counts as contained
one_well = SpatialData.read("ops_plate.zarr/A/1")         # proposed API: partial read of one well
```

[Design record D10](design-decisions.md#d10-element-names-are-the-on-disk-paths-and-a-hyphen-flattens-them-for-v080) records two limits of the branch, checked in its source. A sub-view is built as `SpatialData(elements=...)` without `attrs`, so relationships stored in `attrs` are not visible from `well`. Table `region` values are not rewritten when the prefix is stripped, so `well["images"].obs["region"]` still reads `A/1/footprints`. Both are upstream requests, not rules of this specification.

## Sources

- [OME-NGFF dev specification, plate metadata](https://ngff.openmicroscopy.org/specifications/dev/index.html#plate-metadata): the `rows`, `columns`, `wells`, `acquisitions`, `field_count`, and `name` keys with their requirement levels and the two-acquisition example.
- [OME-NGFF dev specification, well metadata](https://ngff.openmicroscopy.org/specifications/dev/index.html#well-metadata): the `images[].path` character rules and the `images[].acquisition` integer reference.
- [OME-NGFF 0.5 HCS layout](https://ngff.openmicroscopy.org/0.5/#hcs-layout): the released version that the OPS data standard v0.1.0 requires and that the running example writes.
- [OME-NGFF RFC-8: Collections and Extensibility, HCS metadata](https://ngff.openmicroscopy.org/rfc/8/index.html#high-content-screening-hcs-metadata): the `Node`, `Collection`, `Path`, and `Reference` interfaces, the HCS attributes and layouts, the `labels` attribute, and the metadata request note. Status D1.
- [OME-NGFF RFC index](https://ngff.openmicroscopy.org/rfc/index.html): entry point for RFC-5 (coordinate systems and transformations, status S4) referenced by the `scene` attribute.
- [scallops and Biohub OPS layout (HackMD)](https://hackmd.io/@D9GB-ZDcTQyFd7U5aMmk5g/r18soYBuzx): the well `A1`, the ISS cycle set without cycle 6, and the `t=` folder labels. Also the Biohub plate layout `A/{1,2,3}/0/` with its `labels` groups.
- Chan Zuckerberg Initiative (CZI) OPS data standard v0.1.0 (draft) and the audit of a public Biohub submission: the OME-NGFF 0.5 requirement, the `channels_metadata` sibling key, the stitched array `[1, 6, 1, 104650, 105144]` float32 with five levels at 0.325 micrometre per pixel, `field_count` 1, and the int32 labels `nuclear_seg`, `cell_seg`, `gfp_seg`, `iss_gene_image`, and `grid_overlay`. No public URL appears in the source material.
- [ngio table specifications](https://biovisioncenter.github.io/ngio/stable/table_specs/overview/): the `condition_table`, `feature_table`, and `generic_table` type strings carried by `sp-ops:table`.
- [Hierarchical SpatialData slides](https://raw.githubusercontent.com/LucaMarconato/spatialdata/refs/heads/vibecoded-experiment/hierarchical-spatialdata/slides-hierarchical-spatialdata.html): `/` in element names, `sdata["prefix"]` sub-views, the `elements=` constructor, the tree repr, and the partial read of a subfolder. The `_gen_repr` and `__getitem__` code of the same branch fixes the exact repr format and the sub-view semantics.
- [spatialdata documentation](https://spatialdata.scverse.org/en/stable/): the v0.8.0 element name rule and flat repr that the fallback relies on.
- [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119.txt): the meaning of MUST, SHOULD, and MAY.
