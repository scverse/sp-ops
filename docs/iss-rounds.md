# In situ sequencing rounds

This page specifies how the in situ sequencing (ISS) images of one tile are stored, registered, and resampled. ISS is also called sequencing by synthesis (SBS). A tile is one field of view (FOV) in one well of a high-content screening (HCS) plate. It holds two groups of images, the ISS rounds described here and the [phenotypic rounds](phenotypic-rounds.md). The page follows the [design decisions](design-decisions.md) and uses the running example, well `A/1`, tile `f0`, timepoint `t2`, and cycles `r1` to `r10` without `r6`. The nuclear stain of the running example is 4′,6-diamidino-2-phenylindole (DAPI). Statements fall into the three status categories defined on the [overview page](overview.md#every-statement-is-normative-existing-behaviour-or-a-proposal). Existing behaviour comes from Open Microscopy Environment Next-Generation File Format (OME-NGFF) 0.5, spatialdata v0.8.0, and ngio. Proposals depend on two requests for comments (RFC-5 and RFC-8) and on hierarchical SpatialData.

## Each timepoint varies along cycle and channel

The ISS images of one tile exist for several fixation timepoints `t`. The `t` values of the running example are folder labels from the output layout of the scallops optical pooled screening (OPS) pipeline, not measured times (see the [running example](design-decisions.md#running-example)). For one `t` value the images vary along two axes.

| Axis | Symbol | Meaning | Running example | Storage |
| --- | --- | --- | --- | --- |
| cycle, also called round | `r` | one acquisition per position in the hybridised barcode | `1, 2, 3, 4, 5, 7, 8, 9, 10` | one image element per value |
| channel | `c` | one nuclear stain plus one channel per nucleotide | `DAPI, A, G, C, T` | tensor axis `c` when the channels are aligned |

A cycle is one pass of the microscope over the plate. It is the acquisition level of the HCS metadata, and its core acquisition name is `iss-t<t>-r<r>` (D2). The channel axis holds the nuclear stain and up to four base channels. A depositor MAY use fewer than four bases; the `c` axis is then shorter and `sp-ops:channels` lists only the bases present (D12). `sp-ops:channels` on each image is authoritative for channel identity. The `c` coordinate of the spatialdata image MUST carry the same names in the same order (D1).

```json
"sp-ops:channels": [
  {"name": "DAPI", "role": "nuclear"},
  {"name": "A", "role": "base", "base": "A"},
  {"name": "G", "role": "base", "base": "G"},
  {"name": "C", "role": "base", "base": "C"},
  {"name": "T", "role": "base", "base": "T"}
]
```

## Timepoints are separate specimens and are not aligned

Cells fixed at different `t` are different cells. No transformation between two `t` values exists, and this specification does not define one (D5). Two encodings can express that fact.

Encoding A keeps `t` as a tensor axis of length one and uses the `t` value as its coordinate. Under RFC-5 (status S4, not released) the coordinate is a `translation` after the `scale` in a `sequence` inside the dataset transformation. RFC-5 admits at most one `time` axis, so the axis itself is legal. spatialdata `Image2DModel` has dims `(c, y, x)` and no `t`, so the array cannot be loaded as an image. This specification therefore forbids encoding A (D4). It is shown for comparison only.

```json
// Encoding A, NOT permitted by this specification: axes (t, c, y, x), t of length 1, plane placed at t = 2. RFC-5 form.
"multiscales": [{
  "coordinateSystems": [{"name": "intrinsic",
    "axes": [{"name": "t", "type": "time"}, {"name": "c", "type": "channel"},
             {"name": "y", "type": "space", "unit": "micrometer"}, {"name": "x", "type": "space", "unit": "micrometer"}]}],
  "datasets": [{"path": "0", "coordinateTransformations": [
    {"type": "sequence", "input": "0", "output": "intrinsic", "transformations": [
      {"type": "scale", "scale": [1.0, 1.0, 0.325, 0.325]},
      {"type": "translation", "translation": [2.0, 0.0, 0.0, 0.0]}]}]}]
}]
```

Encoding B drops `t` from the tensor. Every `t` value is a separate `(c, y, x)` element, and the per-well `images` table records `t` in one row per image (D4). The design record chose encoding B. Every ISS image MUST be a separate element per `t`, and the `images` table MUST carry its `t`. The rows below are the first two cycles of tile `f0` at two timepoints. The `image_id`, `element`, `acquisition`, and `t` values tell them apart. Every other column is equal.

```text
image_id  region          element         tile  acquisition  kind  t  r   c     channel_aligned  registered  anchor
0         A/1/footprints  f0/t2/iss/r1    0     iss-t2-r1    iss   2  1   null  true             false       true
1         A/1/footprints  f0/t2/iss/r2    0     iss-t2-r2    iss   2  2   null  true             true        false
10        A/1/footprints  f0/t3/iss/r1    0     iss-t3-r1    iss   3  1   null  true             false       true
11        A/1/footprints  f0/t3/iss/r2    0     iss-t3-r2    iss   3  2   null  true             true        false
```

## Cycles are registered to the DAPI channel

Every cycle is a separate pass of the microscope, so the cycles are unaligned until registration. The anchor channel is the channel with `role: "nuclear"` in `sp-ops:channels`, DAPI in the running example. The reference image of one (tile, `t`) is the acquisition whose `sp-ops:acquisitions` entry has `anchor: true`. Exactly one acquisition per `t` MUST carry `anchor: true`. A reader that finds none MUST treat the ISS acquisition with the lowest `r` at that `t` as the reference, `iss-t2-r1` here. A validator MUST report the missing flag (D5). The `t` collection SHOULD carry `sp-ops:registration`, and when present it MUST name `anchorChannel`.

### Before registration each cycle is its own element

The draft sketches an `(r, y, x)` tensor with `r` of length one per acquisition. RFC-5 allows a multiscale image at most one `channel` or custom axis, so `r` and `c` cannot both be axes of one image. spatialdata has no `r` axis either. This specification therefore stores each cycle as one `(c, y, x)` element named `iss/r<k>` (D4). The draft's second form is one image per cycle plus a table with a column `r`. That is the form adopted here. Each cycle is one `(c, y, x)` element and the `images` table carries `r`. Splitting further into one `(1, y, x)` element per channel, with `c` set in the table, is used only when the channels of one cycle are unaligned (see [below](#channels-are-stored-aligned-when-the-protocol-aligns-them)).

```json
// Draft form, NOT permitted: a custom axis r next to the channel axis c breaks the RFC-5 axis rule.
"axes": [{"name": "r", "type": "cycle"}, {"name": "c", "type": "channel"},
         {"name": "y", "type": "space", "unit": "micrometer"}, {"name": "x", "type": "space", "unit": "micrometer"}]
```

Before registration every image carries only its pixel scale. The reference image maps into the registered frame `A/1/f0/t2` by that scale alone. Every other cycle receives an affine estimated from its DAPI channel to the reference DAPI channel, stored as its scale followed by the affine (D5). Registration changes metadata only. No pixel is rewritten.

### After registration cycles share a frame and MAY share a grid

Once every cycle has a transformation into `A/1/f0/t2`, the cycles share a coordinate system but not a pixel grid. A writer MAY resample them onto one grid. Two rules define the common area. Both are computed in the registered frame from the image footprints (D6).

| Rule | Common area | Default | Use |
| --- | --- | --- | --- |
| `contained` | the largest contained box, the intersection of the cycle footprints | yes (SHOULD) | base calling; every output pixel has a value in every cycle |
| `containing` | the smallest containing box, the union of the cycle footprints | no (MAY) | display; pixels outside a footprint are fill values |

The output is the draft's `(r, y, x)` tensor with `r` of length nine, in the only form spatialdata admits. It is either one `(c, y, x)` element per cycle under `reg/iss/r<k>`, all on one grid, or one stacked element `reg/iss_stack`. The stack's `c` names are `r<k>_<channel>` (D6). A writer that stores resampled images MUST set `registered` to true and `resample_rule` to the rule used in the `images` table. It MUST keep the raw acquisition images and MUST set `resample_um_per_px` when the output grid differs from the anchor pixel size (D6).

## Channels are stored aligned when the protocol aligns them

Most protocols yield co-registered channels within one cycle. The channels SHOULD then be stacked as one `(c, y, x)` element. `c` equals the nuclear channel plus the base channels, five in the running example (D4). When the protocol needs a per-channel registration, each channel MUST be its own `(1, y, x)` element named `<acquisition>/<channel>` until it is resampled, for example `A/1/f0/t2/iss/r2/DAPI`. The `images` table then has one row per channel element with `c` set and `channel_aligned` false. After resampling onto the common area the channels MAY be stacked (D4).

```text
image_id  region          element              tile  acquisition  kind  t  r  c     channel_aligned  registered  anchor
1         A/1/footprints  f0/t2/iss/r2/DAPI    0     iss-t2-r2    iss   2  2  DAPI  false            true        false
2         A/1/footprints  f0/t2/iss/r2/A       0     iss-t2-r2    iss   2  2  A     false            true        false
```

## File format example

The trees show tile `f0` at `t2`. Element names follow the [path scheme](design-decisions.md#d10-element-names-are-the-on-disk-paths-and-a-hyphen-flattens-them-for-v080). The hierarchical tree is the collections layout, in which the Zarr path equals the element name. The flat tree is the OME-NGFF 0.5 HCS layout that is valid today, in which `/` below the well becomes `-` (D2, D10).

:::{admonition} Status
:class: note
The hierarchical tree depends on RFC-8 collections (status D1) and on hierarchical SpatialData, neither released. The 0.5 layout depends on nothing unreleased. The `collection.json` sidecar inside it is proposed (D2).
:::

### Before registration every cycle carries only its pixel scale

```text
ops_plate.zarr/A/1/f0/t2/iss/      # collections layout (proposed); 0.5 layout: ops_plate.zarr/A/1/f0-t2-iss-r<k>/
├── r1/                             # acquisition iss-t2-r1, anchor; transformation: scale only
│   ├── zarr.json                   # ome.multiscales (c, y, x); sp-ops:tile, sp-ops:channels
│   ├── 0/                          # (5, 2048, 2048) float32
│   ├── 1/                          # (5, 1024, 1024)
│   └── 2/                          # (5, 512, 512)
├── r2/                             # acquisition iss-t2-r2; same layout; still scale only
├── r3/
├── r4/
├── r5/
├── r7/                             # no r6: cycle 6 is absent in the scallops data
├── r8/
├── r9/
└── r10/
```

### After registration the raw cycles stay unchanged and `reg/` holds the products

Registration adds an affine per cycle to the metadata. Resampling adds derived images under `reg/`. The raw cycles are unchanged.

```text
ops_plate.zarr/A/1/
├── collection.json                 # (proposed) t2 scene: identity for r1, affine for r2 to r10
├── footprints/                     # shapes; one rectangle per image, raw and resampled, at its registered position
├── images/                         # table; registered true for r2 to r10; new rows for reg/iss/r<k>
└── f0/t2/
    ├── iss/                        # raw cycles; pixels unchanged
    │   ├── r1/
    │   ├── r2/
    │   └── ...                     # r3 to r10
    └── reg/                        # resampled products (MAY)
        ├── iss/
        │   ├── r1/                 # (5, 2042, 2046) on the common grid; shape illustrative
        │   ├── r2/
        │   └── ...                 # r3 to r10, same shape
        └── iss_stack/              # (45, 2042, 2046); c names r1_DAPI, r1_A, ..., r10_T (MAY)
```

The next tree shows the same content in the 0.5 layout. Resampled images are derived nodes, not acquisitions (D2). In the 0.5 layout they are extra groups in the well, like points, shapes, and tables. They are not `well.images` entries, so `field_count` counts acquisition images only, and a 0.5 reader does not see the resampled groups (D2 rule 5). The OPS validator has not been tested against extra image groups (D2).

```text
ops_plate.zarr/A/1/                 # OME-NGFF 0.5 HCS layout (existing)
├── zarr.json                       # ome.well.images: f0-t2-iss-r1 ... f0-t2-iss-r10, acquisition ids 0 to 8
├── collection.json                 # (proposed) sidecar with the t2 scene
├── footprints/
├── images/
├── f0-t2-iss-r1/                   # element A/1/f0/t2/iss/r1
├── f0-t2-iss-r2/
├── ...                             # f0-t2-iss-r3 to f0-t2-iss-r10
├── f0-t2-reg-iss-r1/               # element A/1/f0/t2/reg/iss/r1; derived
├── ...                             # f0-t2-reg-iss-r2 to f0-t2-reg-iss-r10
└── f0-t2-reg-iss_stack/            # element A/1/f0/t2/reg/iss_stack
```

### Metadata excerpts

The next block is the image group of cycle 2 in the 0.5 layout. The pixel scale is the OME-NGFF 0.5 `scale` transformation inside `multiscales > datasets` (existing behaviour); RFC-5 keeps the same form. The `sp-ops` keys are siblings of `ome` (D1). Registration changes this file. spatialdata v0.8.0 writes an element's transformations into `multiscales[0].coordinateTransformations` of the element's own group attributes, keyed by coordinate system name (existing behaviour, probe-verified). The `datasets` entries stay intact. D5 makes that copy authoritative until RFC-5 and RFC-8 are released; the sidecar scene repeats it (proposed). The excerpt shows the pre-registration state.

```json
// ops_plate.zarr/A/1/f0-t2-iss-r2/zarr.json, before registration
{
  "zarr_format": 3,
  "node_type": "group",
  "attributes": {
    "ome": {
      "version": "0.5",
      "multiscales": [{
        "axes": [{"name": "c", "type": "channel"},
                 {"name": "y", "type": "space", "unit": "micrometer"},
                 {"name": "x", "type": "space", "unit": "micrometer"}],
        "datasets": [
          {"path": "0", "coordinateTransformations": [{"type": "scale", "scale": [1.0, 0.325, 0.325]}]},
          {"path": "1", "coordinateTransformations": [{"type": "scale", "scale": [1.0, 0.65, 0.65]}]},
          {"path": "2", "coordinateTransformations": [{"type": "scale", "scale": [1.0, 1.3, 1.3]}]}
        ]
      }]
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

After registration the same file gains a `coordinateTransformations` list next to `datasets` in the first `multiscales` entry (existing behaviour, probe-verified). It holds one entry per coordinate system. For cycle 2 that entry is a `sequence` of the `scale` and the affine, with `input` and `output` objects keyed by `name`, the output named `A/1/f0/t2`.

The next block shows the registration edges in the `t2` scene of `A/1/collection.json` (proposed; affine values illustrative). Each edge is an RFC-5 `byDimension` that maps the two space axes of the intrinsic `(c, y, x)` system onto the two axes of the registered frame. The reference image uses `identity`; every other cycle uses a 2 by 3 `affine` (D5). A 0.5 image declares no coordinate system, so a sidecar reader synthesises `intrinsic` from the image `axes` and the level 0 `scale` (D5).

```json
// A/1/collection.json, attributes of the collection node id "A-1-f0-t2"
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
     ]}
  ]
}
```

The next block is the resampled image of cycle 2. Its pixel grid starts at the corner of the common box, not at the tile origin. In the 0.5 layout the group lists a `scale` followed by a `translation` in `datasets[].coordinateTransformations`. RFC-5 names these two types as the existing, backward-compatible transformations. In the collections layout (proposed, RFC-5 status S4) the same offset is a `sequence` of one `scale` and one `translation`, the only compound form RFC-5 admits inside `multiscales > datasets`. The multiscale then declares a `coordinateSystems` entry named `intrinsic`. The scene edge into `A-1-f0-t2` is an `identity` in both layouts (D6). In memory, `rasterize` returns the same offset as the element transformation (values illustrative, derived from the cycle 2 affine alone).

```json
// ops_plate.zarr/A/1/f0-t2-reg-iss-r2/zarr.json, OME-NGFF 0.5 form (existing)
"datasets": [
  {"path": "0", "coordinateTransformations": [
    {"type": "scale", "scale": [1.0, 0.325, 0.325]},
    {"type": "translation", "translation": [0.0, 1.95, 0.0]}]}
]
```

```json
// collections layout, RFC-5 dataset form (proposed)
"coordinateSystems": [{"name": "intrinsic",
  "axes": [{"name": "c", "type": "channel"},
           {"name": "y", "type": "space", "unit": "micrometer"}, {"name": "x", "type": "space", "unit": "micrometer"}]}],
"datasets": [
  {"path": "0", "coordinateTransformations": [
    {"type": "sequence", "input": "0", "output": "intrinsic", "transformations": [
      {"type": "scale", "scale": [1.0, 0.325, 0.325]},
      {"type": "translation", "translation": [0.0, 1.95, 0.0]}]}]}
]
```

The annotating table is `images`. It is an AnnData table with no `var`. Its `obs` holds the rows shown throughout this page. `uns["spatialdata_attrs"]` names the annotated element (existing behaviour, `TableModel` constants). `uns["sp-ops"]` carries the ngio table type (D8).

```json
{
  "spatialdata_attrs": {"region": "A/1/footprints", "region_key": "region", "instance_key": "image_id"},
  "sp-ops": {"table_type": "condition_table", "table_version": "1", "granularity": "image"}
}
```

```text
image_id  region          element             tile  acquisition  kind  t  r   c     channel_aligned  registered  anchor  resample_rule
0         A/1/footprints  f0/t2/iss/r1        0     iss-t2-r1    iss   2  1   null  true             false       true    null
1         A/1/footprints  f0/t2/iss/r2        0     iss-t2-r2    iss   2  2   null  true             true        false   null
320       A/1/footprints  f0/t2/reg/iss/r1    0     iss-t2-r1    iss   2  1   null  true             true        false   contained
321       A/1/footprints  f0/t2/reg/iss/r2    0     iss-t2-r2    iss   2  2   null  true             true        false   contained
```

The `image_id` values of the resampled rows continue past the raw rows and are illustrative. A resampled row carries the acquisition id of its source image (D4). Every resampled row MUST have a `footprints` rectangle with the same `image_id`, because `image_id` is the table's `instance_key` (D3).

## RFC-8 extension draft

:::{admonition} Status
:class: note
This section depends on RFC-8 collections, status D1, an early draft. The keys below are proposals of this specification and are listed in the [extension key registry](design-decisions.md#extension-key-registry). `sp-ops` is the prefix (D1), following the prefix rule on the [extension page](extension.md#the-extension-follows-rfc-8-prefixed-naming-with-the-prefix-sp-ops).
:::

Five `sp-ops` keys and the core `acquisition` reference describe an ISS cycle. The core `acquisition` reference on each image names the acquisition. `sp-ops:tile` marks the tile collection, or the image group in the 0.5 layout. `sp-ops:acquisitions` on the plate says what that acquisition is, with `kind`, `t`, `r`, and `anchor`. `sp-ops:timepoint` marks the `t` collection, and `sp-ops:registration` names the anchor channel. `sp-ops:channels` gives each channel a role (D1). There is no per-image copy of `t` or `r`.

The plate document carries the definitions. Only the cycles of `t2` are shown.

```json
// ops_plate.zarr/collection.json, attributes of the plate node
"plate": {
  "rows": [{"id": "A", "name": "A"}],
  "columns": [{"id": "1", "name": "1"}, {"id": "2", "name": "2"}, {"id": "3", "name": "3"}],
  "acquisitions": [
    {"id": "iss-t2-r1", "name": "ISS cycle 1, t=2"},
    {"id": "iss-t2-r2", "name": "ISS cycle 2, t=2"},
    {"id": "iss-t2-r10", "name": "ISS cycle 10, t=2"}
  ]
},
"sp-ops:acquisitions": [
  {"id": "iss-t2-r1", "kind": "iss", "t": 2, "r": 1, "anchor": true},
  {"id": "iss-t2-r2", "kind": "iss", "t": 2, "r": 2, "anchor": false},
  {"id": "iss-t2-r10", "kind": "iss", "t": 2, "r": 10, "anchor": false}
]
```

The well document carries the tile, the `t` collection, and the `iss` collection. Node ids are the hierarchical names with `/` replaced by `-` (D10). The `acquisition` references cross into the plate document and carry a `path` (D5). The `scene` of the `t2` collection is shown in the [metadata excerpts](#metadata-excerpts).

```json
// ops_plate.zarr/A/1/collection.json, excerpt: the f0 tile node inside the well collection A-1; the root, well attribute, and sp-ops:tileLayout are shown under D3
{"type": "collection", "id": "A-1-f0", "name": "f0",
 "attributes": {"sp-ops:tile": {"index": 0}},
 "nodes": [
   {"type": "collection", "id": "A-1-f0-t2", "name": "t2",
    "attributes": {
      "sp-ops:timepoint": {"index": 2},
      "sp-ops:registration": {"anchorChannel": "DAPI", "reference": {"id": "A-1-f0-t2-iss-r1"}},
      "scene": {"coordinateSystems": ["..."], "coordinateTransformations": ["..."]}
    },
    "nodes": [
      {"type": "collection", "id": "A-1-f0-t2-iss", "name": "iss", "nodes": [
        {"type": "multiscale", "id": "A-1-f0-t2-iss-r1", "name": "r1",
         "path": {"type": "zarr", "path": "./f0-t2-iss-r1"},
         "attributes": {
           "acquisition": {"id": "iss-t2-r1", "path": {"type": "json", "path": "../../collection.json"}},
           "sp-ops:channels": [{"name": "DAPI", "role": "nuclear"}, {"name": "A", "role": "base", "base": "A"},
                               {"name": "G", "role": "base", "base": "G"}, {"name": "C", "role": "base", "base": "C"},
                               {"name": "T", "role": "base", "base": "T"}]}},
        {"type": "multiscale", "id": "A-1-f0-t2-iss-r2", "name": "r2",
         "path": {"type": "zarr", "path": "./f0-t2-iss-r2"},
         "attributes": {"acquisition": {"id": "iss-t2-r2", "path": {"type": "json", "path": "../../collection.json"}},
                        "sp-ops:channels": ["..."]}}
      ]},
      {"type": "collection", "id": "A-1-f0-t2-reg", "name": "reg", "nodes": [
        {"type": "collection", "id": "A-1-f0-t2-reg-iss", "name": "iss", "nodes": [
          {"type": "multiscale", "id": "A-1-f0-t2-reg-iss-r2", "name": "r2",
           "path": {"type": "zarr", "path": "./f0-t2-reg-iss-r2"},
           "attributes": {"sp-ops:channels": ["..."]}}
        ]},
        {"type": "multiscale", "id": "A-1-f0-t2-reg-iss_stack", "name": "iss_stack",
         "path": {"type": "zarr", "path": "./f0-t2-reg-iss_stack"},
         "attributes": {"sp-ops:channels": ["..."]}}
      ]}
    ]}
 ]}
```

`sp-ops:channels` is repeated on the resampled node because a reader of that node alone still needs the channel roles. A resampled node carries no `acquisition` reference; the `images` table links it to its source (D2, D4). In the 0.5 layout `sp-ops:channels` sits in the image group `zarr.json` next to `ome`, as shown above; the spelling is identical in both places (D1).

## SpatialData view

:::{admonition} Status
:class: note
Names containing `/`, sub-views such as `sdata["A/1/f0/t2/iss"]`, and the tree repr come from the experimental hierarchical SpatialData branch (proposed, not released). The repr format follows `_gen_repr` on that branch. It prints elements without `/` at the root and groups the rest under a `folder/` header by the first path component. A sub-view of a store-backed object keeps the store path with the prefix appended, so its first line names the path. In spatialdata v0.8.0 the same elements exist under the flattened names `A-1-f0-t2-iss-r1` and so on (D10).
:::

The first repr shows the ISS cycles of tile `f0` at `t2`, before or after registration. Registration adds no element; it only adds a transformation into `A/1/f0/t2` to each image.

```text
SpatialData object at /data/ops_plate.zarr/A/1/f0/t2/iss
├── r1: [Image2D] DataTree[cyx] (5, 2048, 2048), (5, 1024, 1024), (5, 512, 512)
├── r2: [Image2D] DataTree[cyx] (5, 2048, 2048), (5, 1024, 1024), (5, 512, 512)
├── r3: [Image2D] DataTree[cyx] (5, 2048, 2048), (5, 1024, 1024), (5, 512, 512)
├── r4: [Image2D] DataTree[cyx] (5, 2048, 2048), (5, 1024, 1024), (5, 512, 512)
├── r5: [Image2D] DataTree[cyx] (5, 2048, 2048), (5, 1024, 1024), (5, 512, 512)
├── r7: [Image2D] DataTree[cyx] (5, 2048, 2048), (5, 1024, 1024), (5, 512, 512)
├── r8: [Image2D] DataTree[cyx] (5, 2048, 2048), (5, 1024, 1024), (5, 512, 512)
├── r9: [Image2D] DataTree[cyx] (5, 2048, 2048), (5, 1024, 1024), (5, 512, 512)
└── r10: [Image2D] DataTree[cyx] (5, 2048, 2048), (5, 1024, 1024), (5, 512, 512)
with coordinate systems:
    ▸ 'A/1', with elements:
        r1, r2, r3, r4, r5, r7, r8, r9, r10
    ▸ 'A/1/f0/t2', with elements:
        r1, r2, r3, r4, r5, r7, r8, r9, r10
```

The second repr shows the resampled products of the same tile and timepoint, `sdata["A/1/f0/t2/reg"]`. The stacked element has no `/` and prints first; the per-cycle elements group under `iss/`. Shapes are illustrative.

```text
SpatialData object at /data/ops_plate.zarr/A/1/f0/t2/reg
├── iss_stack: [Image2D] DataArray[cyx] (45, 2042, 2046)
└── iss/ (9 elements)
    ├── r1: [Image2D] DataArray[cyx] (5, 2042, 2046)
    ├── r2: [Image2D] DataArray[cyx] (5, 2042, 2046)
    ├── r3: [Image2D] DataArray[cyx] (5, 2042, 2046)
    ├── r4: [Image2D] DataArray[cyx] (5, 2042, 2046)
    ├── r5: [Image2D] DataArray[cyx] (5, 2042, 2046)
    ├── r7: [Image2D] DataArray[cyx] (5, 2042, 2046)
    ├── r8: [Image2D] DataArray[cyx] (5, 2042, 2046)
    ├── r9: [Image2D] DataArray[cyx] (5, 2042, 2046)
    └── r10: [Image2D] DataArray[cyx] (5, 2042, 2046)
with coordinate systems:
    ▸ 'A/1', with elements:
        iss/r1, iss/r2, iss/r3, iss/r4, iss/r5, iss/r7, iss/r8, iss/r9, iss/r10, iss_stack
    ▸ 'A/1/f0/t2', with elements:
        iss/r1, iss/r2, iss/r3, iss/r4, iss/r5, iss/r7, iss/r8, iss/r9, iss/r10, iss_stack
```

The whole tile, `sdata["A/1/f0"]`, prints one folder per timepoint, `t2/` to `t10/`, each with the seventeen elements of that timepoint. The well-level repr is shown under [D10](design-decisions.md#d10-element-names-are-the-on-disk-paths-and-a-hyphen-flattens-them-for-v080).

## A table keeps track of t, r, and c

The `images` table is one ngio `condition_table` per well with one row per image element (D4, D8). It annotates the `footprints` shapes, one rectangle per image, through `region`, `region_key`, and `instance_key` (existing behaviour). The draft suggests a table whose `region` is the list of image names. `TableModel.parse` accepts that form, but `join_spatialelement_table` rejects image regions in v0.8.0 with `Element type Image2DModel not supported for join operation` (D3, probe-verified). The footprints therefore stand in for the images, and the `element` column names the image.

The first example builds the table for the nine cycles of tile `f0` at `t2`. Every name is a spatialdata v0.8.0 name.

```python
import anndata as ad
import pandas as pd
from spatialdata.models import TableModel

cycles = [1, 2, 3, 4, 5, 7, 8, 9, 10]
obs = pd.DataFrame({
    "region": "A/1/footprints",
    "image_id": list(range(len(cycles))),
    "element": [f"f0/t2/iss/r{k}" for k in cycles],
    "tile": 0,
    "acquisition": [f"iss-t2-r{k}" for k in cycles],
    "kind": "iss",
    "t": 2,
    "r": pd.array(cycles, dtype="Int64"),
    "c": pd.array([None] * len(cycles), dtype="string"),
    "channel_aligned": True,
    "registered": [False] + [True] * (len(cycles) - 1),
    "anchor": [True] + [False] * (len(cycles) - 1),
})
images = TableModel.parse(
    ad.AnnData(obs=obs), region="A/1/footprints", region_key="region", instance_key="image_id"
)
images.uns["sp-ops"] = {"table_type": "condition_table", "table_version": "1", "granularity": "image"}
```

The second example selects every image of cycle 2 across tiles and timepoints. `match_table_to_element` and `join_spatialelement_table` are v0.8.0 names. The names `A/1/footprints` and `A/1/images` and the element lookup by hierarchical name are proposed; in v0.8.0 pass `A-1-footprints` and `A-1-images` (D10).

```python
from spatialdata import join_spatialelement_table, match_table_to_element

table = match_table_to_element(sdata, element_name="A/1/footprints", table_name="A/1/images")
rows = table.obs.query("kind == 'iss' and r == 2").sort_values(["tile", "t"])
cycle2 = {row.element: sdata[f"A/1/{row.element}"] for row in rows.itertuples()}    # proposed API
# v0.8.0 fallback with flattened names (D10):
cycle2 = {row.element: sdata["A-1-" + row.element.replace("/", "-")] for row in rows.itertuples()}

footprints, joined = join_spatialelement_table(
    sdata=sdata, spatial_element_names="A/1/footprints", table_name="A/1/images", how="inner"
)
joined.obs.groupby(["t", "r"]).size()        # one row per (t, r) per tile; cycle 6 is absent
table.obs.query("t == 2 and r == 2 and c == 'DAPI'")      # one row when the channels of a cycle are separate elements
```

The same query answers the questions of the draft. Filter on `t` for one timepoint, on `r` for one cycle, and on `c` for one channel when the channels are stored as separate elements. The JSON metadata stays authoritative, and a validator MUST report any disagreement between the table and `well.images`, `sp-ops:acquisitions`, and `sp-ops:channels` (D4).

## `rasterize` resamples every cycle onto the common box

`spatialdata.rasterize` (v0.8.0) resamples an element into a named coordinate system over an explicit box at an explicit resolution. `axes` is `("y", "x")`. `min_coordinate` and `max_coordinate` give the box in `target_coordinate_system`, which is also the output coordinate system. spatialdata requires exactly one of `target_unit_to_pixels`, `target_width`, `target_height`, and `target_depth` (existing behaviour). The value `1 / 0.325` pixels per micrometre keeps the native pixel size (D6). The result is a single-scale `DataArray`.

The common area comes from `spatialdata.get_extent` (v0.8.0). It returns a dictionary from axis name to `(min, max)` in the requested coordinate system. The `contained` rule takes the largest minimum and the smallest maximum over the cycles; the `containing` rule takes the opposite. D6 computes the same box from the `footprints` shapes with shapely; the two routes agree because `footprints` holds the registered image extents.

```python
from spatialdata import get_extent, rasterize

cs = "A/1/f0/t2"
cycles = [1, 2, 3, 4, 5, 7, 8, 9, 10]
extents = {k: get_extent(sdata[f"{cs}/iss/r{k}"], coordinate_system=cs) for k in cycles}   # proposed lookup
# extents[1] == {"y": (ymin, ymax), "x": (xmin, xmax)}; the reference spans the whole tile


def common_box(extents: dict[int, dict[str, tuple[float, float]]], rule: str = "contained"):
    lo, hi = (max, min) if rule == "contained" else (min, max)
    y0, y1 = lo(e["y"][0] for e in extents.values()), hi(e["y"][1] for e in extents.values())
    x0, x1 = lo(e["x"][0] for e in extents.values()), hi(e["x"][1] for e in extents.values())
    return [y0, x0], [y1, x1]


min_coordinate, max_coordinate = common_box(extents)              # contained, the default rule
for k in cycles:
    resampled = rasterize(
        sdata[f"{cs}/iss/r{k}"],
        axes=("y", "x"),
        min_coordinate=min_coordinate,
        max_coordinate=max_coordinate,
        target_coordinate_system=cs,
        target_unit_to_pixels=1 / 0.325,
    )
    sdata[f"{cs}/reg/iss/r{k}"] = resampled                       # proposed API
```

Passing the whole sub-view resamples every cycle in one call (existing behaviour on a `SpatialData`; the sub-view itself is proposed). The outputs are single-scale images whose names gain the suffix `_rasterized_images`, so a writer MUST rename them before storing them under `reg/` (D6).

```python
registered = rasterize(
    sdata[f"{cs}/iss"],                                             # sub-view, proposed API
    axes=("y", "x"),
    min_coordinate=min_coordinate,
    max_coordinate=max_coordinate,
    target_coordinate_system=cs,
    target_unit_to_pixels=1 / 0.325,
)
list(registered.images)            # ['r1_rasterized_images', 'r2_rasterized_images', ..., 'r10_rasterized_images']
```

The optional stack `reg/iss_stack` is built from these outputs with `Image2DModel.parse(..., c_coords=...)`, as shown under [D6](design-decisions.md#d6-resampling-uses-the-largest-contained-box-by-default). Labels resampled the same way MUST use nearest-neighbour semantics (D6).

## Transformation graph

Every coordinate system is a node and every transformation is an edge. Edge labels are RFC-5 types. Each raw cycle has its own intrinsic system, reached from its level 0 array by a `scale`. The intrinsic system of the reference cycle holds the DAPI anchor, so its edge into the registered frame is an `identity`. Every other cycle reaches the frame by an `affine` wrapped in a `byDimension`. A resampled image reaches its intrinsic system by a `scale` and a `translation`, a `sequence` in RFC-5, and the frame by an `identity`. The frame reaches the well and the well reaches the plate by a `translation` each (D5, D6). The `t3` frame joins the well by its own translation. No edge links the `A/1/f0/t2` frame to the `A/1/f0/t3` frame, because timepoints are not registered to each other (D5).

```{mermaid}
graph LR
  subgraph RAW ["raw cycles of A/1/f0/t2"]
    A1["iss/r1 array 0"] -- "scale" --> I1["iss/r1 intrinsic (DAPI anchor)"]
    A2["iss/r2 array 0"] -- "scale" --> I2["iss/r2 intrinsic"]
    A10["iss/r10 array 0"] -- "scale" --> I10["iss/r10 intrinsic"]
  end
  subgraph REG ["resampled products (MAY)"]
    AR["reg/iss/r2 array 0"] -- "scale, translation" --> IR["reg/iss/r2 intrinsic"]
  end
  I1 -- "identity (byDimension)" --> T["frame A/1/f0/t2, tile at t2"]
  I2 -- "affine (byDimension)" --> T
  I10 -- "affine (byDimension)" --> T
  IR -- "identity" --> T
  T -- "translation" --> W["frame A/1, well"]
  T3["frame A/1/f0/t3"] -- "translation" --> W
  W -- "translation" --> P["frame plate (optional)"]
```

On disk the edges between frames are scene edges in the sidecar (proposed). In memory, spatialdata v0.8.0 keeps transformations on elements, never between coordinate systems (existing behaviour). The sp-ops reader therefore composes the scene edges into one transformation per element and ancestor frame when it loads the store (D5). The reference cycle carries a `Scale`; every other cycle carries a `Sequence` of that `Scale` and its `Affine`; the well edge appends a `Translation` (D5).

```python
from spatialdata.transformations import (
    Affine, Scale, Sequence, Translation, get_transformation_between_coordinate_systems, set_transformation,
)

px = Scale([0.325, 0.325], axes=("y", "x"))
reg = Affine([[1.0002, -0.0004, 1.95], [0.0004, 1.0002, -0.65], [0, 0, 1]],
             input_axes=("y", "x"), output_axes=("y", "x"))                     # illustrative values
to_well = Translation([0.0, 0.0], axes=("y", "x"))                              # tile f0 sits at the well origin

set_transformation(sdata["A/1/f0/t2/iss/r1"], px, to_coordinate_system="A/1/f0/t2")             # proposed lookup
set_transformation(sdata["A/1/f0/t2/iss/r2"], Sequence([px, reg]), to_coordinate_system="A/1/f0/t2")
set_transformation(sdata["A/1/f0/t2/iss/r2"], Sequence([px, reg, to_well]), to_coordinate_system="A/1")
get_transformation_between_coordinate_systems(sdata, "A/1/f0/t2", "A/1")        # recovers to_well
```

## Sources

### Specifications

- [OME-NGFF RFC-8: Collections and Extensibility](https://ngff.openmicroscopy.org/rfc/8/index.html#high-content-screening-hcs-metadata): `Node`, `Collection`, `Multiscale`, `Path`, `Reference`, `scene`, HCS `plate`, `well`, and `acquisition` attributes, prefixed extension keys; status D1.
- [OME-NGFF RFC index](https://ngff.openmicroscopy.org/rfc/index.html): entry point for RFC-5 (status S4). Used for coordinate systems, the types `identity`, `scale`, `translation`, `affine`, `sequence`, and `byDimension`, the multiscales axis rule, and the dataset transformation rule.
- [OME-NGFF dev specification, plate metadata](https://ngff.openmicroscopy.org/specifications/dev/index.html#plate-metadata): `acquisitions` with `id`, `name`, `maximumfieldcount`.
- [OME-NGFF dev specification, well metadata](https://ngff.openmicroscopy.org/specifications/dev/index.html#well-metadata): `well.images[].path` and `acquisition`, path character rules.
- [OME-NGFF 0.5](https://ngff.openmicroscopy.org/0.5/): the released version the OPS data standard requires.
- Chan Zuckerberg Initiative (CZI) OPS data standard v0.1.0 (draft) and the conformance check of a public Biohub submission: the OME-NGFF 0.5 HCS requirement, the pixel size, and the float32 dtype. No public URL appears in the source material.
- [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119.txt): the meaning of MUST, SHOULD, and MAY.

### Libraries, prototypes, and data

- [spatialdata documentation](https://spatialdata.scverse.org/en/stable/): the v0.8.0 public application programming interface (API) used here (`rasterize`, `get_extent`, `set_transformation`, `get_transformation_between_coordinate_systems`, `join_spatialelement_table`, `match_table_to_element`, `TableModel.parse`, `Image2DModel`). The `get_extent` signature and the `_rasterized_images` suffix were verified against the v0.8.0 source (`_core/data_extent.py`, `_core/operations/rasterize.py`).
- [spatialdata tables tutorial](https://spatialdata.scverse.org/en/stable/tutorials/notebooks/notebooks/examples/tables.html): the `region`, `region_key`, `instance_key` annotation model.
- [Hierarchical SpatialData slides](https://raw.githubusercontent.com/LucaMarconato/spatialdata/refs/heads/vibecoded-experiment/hierarchical-spatialdata/slides-hierarchical-spatialdata.html): `/` in element names, sub-views, the tree repr; experimental, not released.
- [ngio table specifications](https://biovisioncenter.github.io/ngio/stable/table_specs/overview/): the `condition_table` type used by `images`.
- [scallops and Biohub OPS layout (HackMD)](https://hackmd.io/@D9GB-ZDcTQyFd7U5aMmk5g/r18soYBuzx): the cycle set `A1-1.ome.tiff` to `A1-10.ome.tiff` without cycle 6, the `iss-transforms-t0/A1/t=<t>` affine folders, `iss-registered-t0.zarr`.
