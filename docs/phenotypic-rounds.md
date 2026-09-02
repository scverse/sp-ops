# Phenotypic rounds

This page specifies how the phenotypic round of an optical pooled screen (OPS) is stored. It also specifies how that round relates to the in situ sequencing (ISS) rounds of the same tile. It covers the channel encoding and the registration into the tile coordinate system. It then gives the on-disk layout in Open Microscopy Environment Next-Generation File Format (OME-NGFF) 0.5 and the collection view of request for comments 8 (RFC-8). It ends with the SpatialData view and the application programming interfaces (APIs) that annotate, resample, and locate the images. Rules shared with the ISS rounds are stated once on the [ISS rounds page](iss-rounds.md) and linked from here. Every name comes from the [running example](design-decisions.md#running-example) of the design record.

:::{admonition} Status
:class: note
Statements fall into the three status categories defined on the [overview page](overview.md#every-statement-is-normative-existing-behaviour-or-a-proposal). Existing behaviour here is OME-NGFF 0.5 high-content screening (HCS) metadata, spatialdata v0.8.0, and the ngio table specifications. The unreleased dependencies here are RFC-8 collections (status D1), RFC-5 coordinate transformations (status S4), the experimental hierarchical SpatialData branch, and the element relationships prototypes behind the D9 spatial join in the registration section.
:::

## Each timepoint has one phenotypic acquisition, and channel is its only axis

A phenotypic acquisition is the phenotypic round at one fixation timepoint `t`. Its core acquisition name MUST be `pheno-t<t>`, and its entry in `sp-ops:acquisitions` MUST carry `kind: "pheno"` and `r: null` ([D1](design-decisions.md#d1-the-extension-prefix-is-sp-ops-with-nine-attribute-keys-and-three-node-types), [D2](design-decisions.md#d2-plates-and-wells-stay-valid-ome-ngff-05-the-rfc-8-view-is-a-sidecar)). The `t` values are folder labels from the scallops layout, not measured timepoints.

The ISS rounds at one `t` vary along two axes, cycle `r` and channel `c`. The phenotypic round varies along one axis, channel `c`. The scallops layout shows the difference. It holds one phenotypic image per well, `stitch/pheno/illumination_correction/A1.ome.tiff`, against one ISS image per cycle, `A1-1.ome.tiff` to `A1-10.ome.tiff`.

The encoding rules of [D4](design-decisions.md#d4-timepoints-and-cycles-are-separate-elements-only-aligned-channels-are-stacked) apply unchanged with `r` absent, as stated for cycles in [Channels are stored aligned when the protocol aligns them](iss-rounds.md#channels-are-stored-aligned-when-the-protocol-aligns-them). A quantity becomes a tensor axis only when it is `c` and every plane shares one pixel grid.

| Quantity | What differs between values | Encoding | Requirement |
| --- | --- | --- | --- |
| `t` | different fixed cells | one element per value, `A/1/f0/t<t>/pheno` | MUST |
| `c`, aligned | wavelength only, one pixel grid | axis `c` of one `(c, y, x)` element | SHOULD |
| `c`, unaligned | wavelength and pixel grid | one `(1, y, x)` element per channel, `A/1/f0/t<t>/pheno/<channel>` | MUST until resampled |

The channel alignment rule is the following. When the protocol yields co-registered channels, the writer SHOULD store one `(c, y, x)` element named `pheno`. When the channels need registration, the writer MUST store one element per channel named `pheno/<channel name>`. Each element MUST carry its own transformation into the registered frame. The `images` table MUST record the channel in its `c` column and set `channel_aligned` to false. After resampling on a common box (see [Resampling](#resampling-shares-the-box-with-the-iss-cycles)) the writer MAY store a stacked `reg/pheno` element.

The phenotypic channels of the running example follow. The nuclear stain is 4′,6-diamidino-2-phenylindole (DAPI). `sp-ops:channels` is authoritative for identity and order, and the `c` coordinate of the spatialdata image MUST carry the same names in the same order (D1). The channels of one phenotypic acquisition MUST include exactly one channel with `role: "nuclear"`, because that channel anchors the registration. In the aligned encoding it is one plane of the `pheno` stack. In the unaligned encoding it is its own element, `pheno/DAPI` in the running example, and the other channel elements carry no nuclear channel (D1). The other channels SHOULD carry `role: "stain"` or `role: "other"`, the two remaining values of the D1 role vocabulary; the running example uses `stain` for all four (D1, [`sp-ops:channels`](extension.md#sp-opschannels-gives-every-channel-a-role)).

| Position | Name | Role | Status |
| --- | --- | --- | --- |
| 0 | `DAPI` | `nuclear` | from the draft |
| 1 | `GFP` | `stain` | from the real label `gfp_seg` |
| 2 | `stain_3` | `stain` | illustrative |
| 3 | `stain_4` | `stain` | illustrative |
| 4 | `stain_5` | `stain` | illustrative |

The `images` table of the well records both encodings. The rows below are the phenotypic rows of the D4 example, aligned first and unaligned second.

```text
image_id  region          element            tile  acquisition  kind   t  r     c     channel_aligned  registered  anchor
9         A/1/footprints  f0/t2/pheno        0     pheno-t2     pheno  2  null  null  true             true        false

9         A/1/footprints  f0/t2/pheno/DAPI   0     pheno-t2     pheno  2  null  DAPI  false            true        false
10        A/1/footprints  f0/t2/pheno/GFP    0     pheno-t2     pheno  2  null  GFP   false            true        false
```

In the unaligned case one acquisition yields one `well.images` entry per channel per tile. `field_count` counts `well.images` entries and grows with them (D2 rule 2). `maximumfieldcount` of `pheno-t<t>` counts the entries the acquisition contributes to one well, so it is tiles times channels in this case (D2 rule 1). The dev specification defines `maximumfieldcount` as "the maximum number of fields of view for the acquisition".

## Phenotypic images are registered to the ISS tile frame through the nuclear channel

Every element under `A/1/f0/t2/` MUST carry a transformation into the registered frame `A/1/f0/t2`, one frame per (tile, `t`) ([D5](design-decisions.md#d5-cycles-are-registered-to-the-dapi-channel-of-the-first-iss-cycle-at-each-timepoint)). The ISS rounds page states the rule for cycles in [Cycles are registered to the DAPI channel](iss-rounds.md#cycles-are-registered-to-the-dapi-channel). The phenotypic image is no exception. Its transformation MUST be its pixel-to-micrometre scale followed by an affine estimated between its nuclear channel and the nuclear channel of the reference image. The reference image is the acquisition with `anchor: true` at that `t`, by default the first ISS cycle `iss-t<t>-r1`. In the running example both nuclear channels are named `DAPI`.

A depositor MAY make the phenotypic round the reference instead. The depositor does so by setting `anchor: true` on its `sp-ops:acquisitions` entry, or by naming it in `sp-ops:registration.reference` on the `t` collection. The ISS cycles are then registered to the phenotypic DAPI. Whichever image is the reference, the frame stays the same and the rules below do not change.

An unaligned element without a nuclear channel cannot be registered by its own nuclear channel. Its affine MUST be the composition of a channel-to-nuclear correction for that element with the nuclear affine of the same acquisition. How the correction is estimated is the writer's choice and is not specified (D5).

The registration links each cell's phenotype to its genotype. The label images `nuclear_seg` and `cell_seg` are computed from the phenotypic image, and their `labels.source` names it. The base calls in `bases` are computed from the ISS cycles. The spatial join `bases` within `cell_seg` ([D9](design-decisions.md#d9-relationships-are-an-edge-list-stored-on-the-lowest-node-that-contains-both-endpoints), proposed; it depends on the element relationships prototypes) is evaluated in `A/1/f0/t2`, and it writes the label value into the `cell_label` column of `bases`. From there `reads` joins on `read`, and `library` joins on `barcode`. If the phenotypic image and the cycles did not share the frame, every read would land in the wrong cell. See [Elements are linked by joins or spatial joins](joinable-components.md#elements-are-linked-by-joins-or-spatial-joins) for the full chain.

Labels follow the grid they were computed on. In the running example the label images are computed in the registered frame and carry a pure scale (D5). A store that segments on the raw phenotypic pixel grid before registration MUST give its labels the same transformation as the phenotypic image (D5).

| Element | Transformation to `A/1/f0/t2` | Reason |
| --- | --- | --- |
| `iss/r1` | scale | reference image |
| `pheno` | scale, then affine nuclear to nuclear | separate microscope pass |
| `pheno/<channel>` (unaligned) | scale, then the nuclear affine; a non-nuclear channel first applies its channel correction (D5) | separate pass or separate optics per channel |
| `nuclear_seg`, `cell_seg` | scale | computed in the registered frame (D5) |
| `cell_bbox` | identity | computed in the registered frame |
| `reg/pheno` (MAY) | identity (D6) | resampled product on the frame grid |

Cross-timepoint registration is undefined. A coordinate in the well frame `A/1` locates an object on the plate; it does not align cells from `t2` with cells from `t3` (D5).

## File format example

The tree below is the OME-NGFF 0.5 layout of the `tiled` profile for tile `f0` at `t2`, aligned channels. Element names in the comments are the hierarchical names of [D10](design-decisions.md#d10-element-names-are-the-on-disk-paths-and-a-hyphen-flattens-them-for-v080). The 0.5 group name replaces `/` with `-`, because `well.images[].path` MUST NOT contain `/`.

```text
ops_plate.zarr/A/1/
├── zarr.json                        # ome.well.images: {"path": "f0-t2-pheno", "acquisition": 9}
├── f0-t2-iss-r1/                    # reference image of A/1/f0/t2, see the ISS rounds page
├── ...                              # f0-t2-iss-r2 to f0-t2-iss-r10 (no r6)
├── f0-t2-pheno/                     # element A/1/f0/t2/pheno, acquisition pheno-t2
│   ├── zarr.json                    # ome.multiscales (c, y, x); sp-ops:tile, sp-ops:channels
│   ├── 0/                           # (5, 2048, 2048) float32, 0.325 micrometre per pixel
│   ├── 1/                           # (5, 1024, 1024)
│   ├── 2/                           # (5, 512, 512)
│   └── labels/
│       ├── zarr.json                # ome.labels: ["nuclear_seg", "cell_seg"]
│       ├── nuclear_seg/             # element A/1/f0/t2/nuclear_seg, (2048, 2048) int32
│       └── cell_seg/                # element A/1/f0/t2/cell_seg, (2048, 2048) int32
├── f0-t2-cell_bbox/                 # shapes, 859 rectangles in the registered frame
├── f0-t3-pheno/                     # next timepoint, same pattern
└── ...
```

The unaligned variant replaces the single group with one group per channel. Every group carries the same `acquisition` id in `well.images`.

```text
ops_plate.zarr/A/1/
├── f0-t2-pheno-DAPI/                # element A/1/f0/t2/pheno/DAPI, (1, 2048, 2048); acquisition 9
│   ├── zarr.json                    # sp-ops:channels has one entry, role nuclear
│   ├── 0/ 1/ 2/
│   └── labels/
│       ├── nuclear_seg/             # element A/1/f0/t2/pheno/nuclear_seg (D2 rule 4, D10 rule 4)
│       └── cell_seg/                # element A/1/f0/t2/pheno/cell_seg
├── f0-t2-pheno-GFP/                 # element A/1/f0/t2/pheno/GFP, (1, 2048, 2048); acquisition 9
├── f0-t2-pheno-stain_3/
├── f0-t2-pheno-stain_4/
├── f0-t2-pheno-stain_5/
└── f0-t2-reg-pheno/                 # MAY: resampled (5, 2048, 2048) stack, element A/1/f0/t2/reg/pheno
```

In this variant D2 rule 4 nests each label under the image it was computed from, and D10 rule 4 names it after the parent of that image. The label at `f0-t2-pheno-DAPI/labels/nuclear_seg` is therefore the element `A/1/f0/t2/pheno/nuclear_seg`, with RFC-8 id `A-1-f0-t2-pheno-nuclear_seg`, not `A/1/f0/t2/nuclear_seg`. `cell_seg` nests under the same group when it was computed on the DAPI grid. When both labels were computed on the resampled stack, they nest under `f0-t2-reg-pheno/labels/`, and the same rule names them `A/1/f0/t2/reg/nuclear_seg` and `A/1/f0/t2/reg/cell_seg`. The running-example label names therefore hold at `<t>/` only in the aligned encoding (D10 rule 4).

The `zarr.json` of `f0-t2-pheno` follows. Core keys sit under `ome`; the `sp-ops:` keys are siblings of `ome` in the group `attributes`, as D1 requires. Pyramid levels beyond `0` are illustrative.

```json
{
  "zarr_format": 3,
  "node_type": "group",
  "attributes": {
    "ome": {
      "version": "0.5",
      "multiscales": [
        {
          "axes": [
            {"name": "c", "type": "channel"},
            {"name": "y", "type": "space", "unit": "micrometer"},
            {"name": "x", "type": "space", "unit": "micrometer"}
          ],
          "datasets": [
            {"path": "0", "coordinateTransformations": [{"type": "scale", "scale": [1.0, 0.325, 0.325]}]},
            {"path": "1", "coordinateTransformations": [{"type": "scale", "scale": [1.0, 0.65, 0.65]}]},
            {"path": "2", "coordinateTransformations": [{"type": "scale", "scale": [1.0, 1.3, 1.3]}]}
          ]
        }
      ]
    },
    "sp-ops:tile": {"index": 0},
    "sp-ops:channels": [
      {"name": "DAPI", "role": "nuclear"},
      {"name": "GFP", "role": "stain"},
      {"name": "stain_3", "role": "stain"},
      {"name": "stain_4", "role": "stain"},
      {"name": "stain_5", "role": "stain"}
    ]
  }
}
```

Channel display settings are outside this specification. `sp-ops:channels` is the only channel identity metadata this specification reads. When the image group carries another list of channel names, such as the `channels_metadata` key seen in the audited store, a validator SHOULD warn when its names or order disagree with `sp-ops:channels` (D1).

The matching entries in the well and plate groups are the following.

| Document | Array | Entry |
| --- | --- | --- |
| `A/1/zarr.json` | `ome.well.images` | `{"path": "f0-t2-pheno", "acquisition": 9}` |
| `ops_plate.zarr/zarr.json` | `ome.plate.acquisitions` | `{"id": 9, "name": "pheno-t2", "maximumfieldcount": 4}` |
| `ops_plate.zarr/zarr.json` | `sp-ops:acquisitions` | `{"id": 9, "kind": "pheno", "t": 2, "r": null, "anchor": false}` |

Registration affines are not in the 0.5 `zarr.json` above. In memory, and in spatialdata's own element metadata, they are element transformations keyed by coordinate system name (existing behaviour, D5). The RFC-8 sidecar below repeats them as a scene.

## RFC-8 extension draft

:::{admonition} Status
:class: note
This section depends on RFC-8 collections, whose own text says "This proposal is early" and gives status D1. It also depends on RFC-5 for the `scene` attribute (status S4). Nothing here is readable by released software. Per D2 the RFC-8 view is a standalone JSON document, `A/1/collection.json`, next to the well `zarr.json`. Node ids replace `/` with `-` because RFC-8 ids MUST match `[a-zA-Z0-9-_.]+`. The enclosing well document carries `"version": "0.x"` in its root `ome` object, the placeholder RFC-8 uses in its own examples; the nested collection below has no version field.
:::

The `t2` collection inside the well document holds the phenotypic image, its two label images, and the scene edges that place them in the frame. The ISS nodes and their edges are shown in the [ISS RFC-8 extension draft](iss-rounds.md#rfc-8-extension-draft) and omitted here. The `acquisition` reference crosses into the plate document and carries a `path` (D5). Affine values are illustrative and are the D5 values. The label edges are `identity` edges, because the labels are computed in the registered frame (D5).

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
         "input": {"id": "intrinsic", "path": {"type": "zarr", "path": "./f0-t2-pheno"}},
         "output": {"id": "A-1-f0-t2"},
         "transformations": [
           {"input_axes": [1, 2], "output_axes": [0, 1],
            "transformation": {"type": "affine",
                               "affine": [[0.9998, 0.0011, -3.25], [-0.0011, 0.9998, 4.55]]}}
         ]},
        {"type": "identity",
         "input": {"id": "intrinsic", "path": {"type": "zarr", "path": "./f0-t2-pheno/labels/nuclear_seg"}},
         "output": {"id": "A-1-f0-t2"}},
        {"type": "identity",
         "input": {"id": "intrinsic", "path": {"type": "zarr", "path": "./f0-t2-pheno/labels/cell_seg"}},
         "output": {"id": "A-1-f0-t2"}}
      ]
    }
  },
  "nodes": [
    {"type": "multiscale", "id": "A-1-f0-t2-pheno", "name": "pheno",
     "path": {"type": "zarr", "path": "./f0-t2-pheno"},
     "attributes": {
       "acquisition": {"id": "pheno-t2", "path": {"type": "json", "path": "../../collection.json"}},
       "sp-ops:channels": [
         {"name": "DAPI", "role": "nuclear"},
         {"name": "GFP", "role": "stain"},
         {"name": "stain_3", "role": "stain"},
         {"name": "stain_4", "role": "stain"},
         {"name": "stain_5", "role": "stain"}
       ]
     }},
    {"type": "multiscale", "id": "A-1-f0-t2-nuclear_seg", "name": "nuclear_seg",
     "path": {"type": "zarr", "path": "./f0-t2-pheno/labels/nuclear_seg"},
     "attributes": {"labels": {"source": [{"id": "A-1-f0-t2-pheno"}]}}},
    {"type": "multiscale", "id": "A-1-f0-t2-cell_seg", "name": "cell_seg",
     "path": {"type": "zarr", "path": "./f0-t2-pheno/labels/cell_seg"},
     "attributes": {"labels": {"source": [{"id": "A-1-f0-t2-pheno"}]}}}
  ]
}
```

Three RFC-8 facts carry this layout. The `acquisition` attribute "MUST be a Reference to one of the acquisitions". The `labels` attribute marks a multiscale as a label map, and its `source` field is "an array with References to the source multiscales". Prefixed keys such as `sp-ops:channels` are the RFC-8 extension point for attributes and follow the prefix rule on the [extension page](extension.md#the-extension-follows-rfc-8-prefixed-naming-with-the-prefix-sp-ops).

In the unaligned variant the phenotypic image becomes a `collection` node named `pheno` with one `multiscale` child per channel. RFC-8 allows this. The `acquisition` attribute "MAY be set on individual multiscale nodes within a well or on a collection sub-node grouping all images from a single acquisition". The scene then carries one `byDimension` edge per channel node. The label nodes take the ids `A-1-f0-t2-pheno-nuclear_seg` and `A-1-f0-t2-pheno-cell_seg`, with paths under `./f0-t2-pheno-DAPI/labels/`, and are omitted below.

```json
{"type": "collection", "id": "A-1-f0-t2-pheno", "name": "pheno",
 "attributes": {"acquisition": {"id": "pheno-t2", "path": {"type": "json", "path": "../../collection.json"}}},
 "nodes": [
   {"type": "multiscale", "id": "A-1-f0-t2-pheno-DAPI", "name": "DAPI",
    "path": {"type": "zarr", "path": "./f0-t2-pheno-DAPI"},
    "attributes": {"sp-ops:channels": [{"name": "DAPI", "role": "nuclear"}]}},
   {"type": "multiscale", "id": "A-1-f0-t2-pheno-GFP", "name": "GFP",
    "path": {"type": "zarr", "path": "./f0-t2-pheno-GFP"},
    "attributes": {"sp-ops:channels": [{"name": "GFP", "role": "stain"}]}}
 ]}
```

## SpatialData view

:::{admonition} Status
:class: note
Element names containing `/`, `sdata["A/1/f0"]` sub-views, and the tree repr come from the experimental hierarchical SpatialData branch, which is not released. spatialdata v0.8.0 rejects `/` in names; the v0.8.0 fallback is the flattened name `A-1-f0-t2-pheno` (D10). The repr format below follows `_gen_repr` on the branch, which groups elements by their first path component only.
:::

One tile is a sub-view. Inside it, the phenotypic elements of one timepoint sit next to the ISS cycles they are registered with.

```python
tile = sdata["A/1/f0"]                       # proposed API: sub-view of one tile
tile["t2/pheno"] is sdata["A/1/f0/t2/pheno"]  # True
tile["t2"].images.keys()                      # 'iss/r1', ..., 'iss/r10', 'pheno', 'spots/max', 'spots/std'
```

The repr of `tile` follows. Lines marked `...` are elided; the real repr prints every element and every coordinate system. Row counts other than the 859 cells are illustrative.

```text
SpatialData object at /data/ops_plate.zarr/A/1/f0
├── t2/ (17 elements)
│   ├── bases: [Points2D] DataFrame (612340, 6)
│   ├── cell_bbox: [Shapes] GeoDataFrame (859, 1)
│   ├── cell_seg: [Labels2D] DataTree[yx] (2048, 2048), (1024, 1024), (512, 512)
│   ├── iss/r1: [Image2D] DataTree[cyx] (5, 2048, 2048), (5, 1024, 1024), (5, 512, 512)
│   ├── ...                                   # iss/r2 to iss/r10, see the ISS rounds page
│   ├── nuclear_seg: [Labels2D] DataTree[yx] (2048, 2048), (1024, 1024), (512, 512)
│   ├── pheno: [Image2D] DataTree[cyx] (5, 2048, 2048), (5, 1024, 1024), (5, 512, 512)
│   ├── spots/max: [Image2D] DataArray[cyx] (4, 2048, 2048)
│   ├── spots/peaks: [Points2D] DataFrame (70112, 3)
│   └── spots/std: [Image2D] DataArray[cyx] (1, 2048, 2048)
├── t3/ (17 elements)
│   ├── ...
│   └── pheno: [Image2D] DataTree[cyx] (5, 2048, 2048), (5, 1024, 1024), (5, 512, 512)
└── ...                                       # t4, t5, t7, t8, t9, t10
with coordinate systems:
    ▸ 'A/1', with elements:
        t2/bases, t2/cell_bbox, t2/cell_seg, t2/iss/r1, ..., t2/nuclear_seg, t2/pheno, t2/spots/max, t2/spots/peaks, t2/spots/std, t3/bases, ..., t3/pheno, t3/spots/max, t3/spots/peaks, t3/spots/std, ...
    ▸ 'A/1/f0/t2', with elements:
        t2/bases, t2/cell_bbox, t2/cell_seg, t2/iss/r1, ..., t2/nuclear_seg, t2/pheno, t2/spots/max, t2/spots/peaks, t2/spots/std
    ▸ 'A/1/f0/t3', with elements:
        t3/bases, t3/cell_bbox, t3/cell_seg, t3/iss/r1, ..., t3/nuclear_seg, t3/pheno, ...
```

With unaligned channels the `pheno` line becomes one line per channel, the two label lines move under `pheno/`, and the optional resampled stack appears under `reg/`.

```text
│   ├── pheno/DAPI: [Image2D] DataTree[cyx] (1, 2048, 2048), (1, 1024, 1024), (1, 512, 512)
│   ├── pheno/GFP: [Image2D] DataTree[cyx] (1, 2048, 2048), (1, 1024, 1024), (1, 512, 512)
│   ├── pheno/cell_seg: [Labels2D] DataTree[yx] (2048, 2048), (1024, 1024), (512, 512)
│   ├── pheno/nuclear_seg: [Labels2D] DataTree[yx] (2048, 2048), (1024, 1024), (512, 512)
│   ├── ...                                   # pheno/stain_3 to pheno/stain_5
│   ├── reg/pheno: [Image2D] DataArray[cyx] (5, 2048, 2048)
```

## APIs annotate, resample, and locate the phenotypic image

The functions below are spatialdata v0.8.0 names, taken from the verified API notes. Every element name containing `/` is hierarchical SpatialData (proposed). Lookups with such names carry a `# proposed API` comment, and string arguments naming such elements carry the same comment. Coordinate-system names containing `/`, such as `A/1` and `A/1/f0/t2`, are unverified in spatialdata v0.8.0 ([D10](design-decisions.md#d10-element-names-are-the-on-disk-paths-and-a-hyphen-flattens-them-for-v080)). The RFC-8 ids `A-1` and `A-1-f0-t2` of D5 are the fallback spelling, as on the [hierarchy page](hierarchy.md#the-spatialdata-view-is-a-tree). Calls that pass such a name carry a `# unverified in v0.8.0` comment.

### The images table records t and c for every phenotypic element

The `images` table is one ngio `condition_table` per well, specified in [A table keeps track of t, r, and c](iss-rounds.md#a-table-keeps-track-of-t-r-and-c). It annotates the `footprints` shapes with `region_key` `region` and `instance_key` `image_id` (D4). A reader finds the phenotypic element of a (tile, `t`) by filtering the joined table. It then checks `channel_aligned` to decide whether it holds one stack or one element per channel.

```python
import anndata as ad
import pandas as pd
from spatialdata import get_pyramid_levels, join_spatialelement_table
from spatialdata.models import TableModel

obs = pd.DataFrame({
    "region": "A/1/footprints",
    "image_id": [9, 19],
    "element": ["f0/t2/pheno", "f0/t3/pheno"],
    "tile": [0, 0],
    "acquisition": ["pheno-t2", "pheno-t3"],
    "kind": ["pheno", "pheno"],
    "t": [2, 3],
    "r": pd.array([None, None], dtype="Int64"),
    "c": pd.array([None, None], dtype="string"),
    "channel_aligned": [True, True],
    "registered": [True, True],
    "anchor": [False, False],
})
images = TableModel.parse(
    ad.AnnData(obs=obs), region="A/1/footprints", region_key="region", instance_key="image_id"
)
images.uns["sp-ops"] = {"table_type": "condition_table", "table_version": "1", "granularity": "image"}

_, joined = join_spatialelement_table(
    sdata=sdata, spatial_element_names="A/1/footprints", table_name="A/1/images", how="inner"   # proposed API for the names
)
rows = joined.obs.query("tile == 0 and t == 2 and kind == 'pheno'")
if rows["channel_aligned"].all():
    pheno = sdata[f"A/1/{rows.iloc[0].element}"]                             # proposed API
    get_pyramid_levels(pheno, n=0).coords["c"].values                        # level 0 of the DataTree: ['DAPI', 'GFP', 'stain_3', 'stain_4', 'stain_5']
else:
    per_channel = {row.c: sdata[f"A/1/{row.element}"] for row in rows.itertuples()}   # proposed API
```

For unaligned channels the `obs` rows carry the channel name in `c`, one row per element, as in the table of the first section.

### Resampling shares the box with the ISS cycles

`rasterize` (existing behaviour) is described in [`rasterize` resamples every cycle onto the common box](iss-rounds.md#rasterize-resamples-every-cycle-onto-the-common-box). Passing one element returns a single-scale `DataArray`.

A writer that resamples the phenotypic image SHOULD use the same box as the ISS cycles of the same (tile, `t`). A pixel index then means the same location in every resampled element. This page proposes the shared box. [D6](design-decisions.md#d6-resampling-uses-the-largest-contained-box-by-default) defines the `contained` rule as the intersection of the footprints of every image being resampled. Taking every acquisition at that (tile, `t`) into the intersection gives the shared box.

```python
import shapely
from spatialdata import rasterize, transform
from spatialdata.transformations import get_transformation_between_coordinate_systems

ids = joined.obs.query("tile == 0 and t == 2")["image_id"].to_list()      # every acquisition at (f0, t2)
to_t2 = get_transformation_between_coordinate_systems(sdata, "A/1", "A/1/f0/t2")   # unverified in v0.8.0: "/" in coordinate-system names (D10)
fp = transform(sdata["A/1/footprints"].loc[ids], transformation=to_t2, maintain_positioning=True)   # footprints in the registered frame; proposed API for the name
xmin, ymin, xmax, ymax = shapely.intersection_all(fp.geometry.values).bounds   # contained rule (D6)

pheno_reg = rasterize(
    sdata["A/1/f0/t2/pheno"],                                              # proposed API for the name
    axes=("y", "x"),
    min_coordinate=[ymin, xmin],
    max_coordinate=[ymax, xmax],
    target_coordinate_system="A/1/f0/t2",
    target_unit_to_pixels=1 / 0.325,                                       # keep the native pixel size
)
```

With unaligned channels, each channel element is resampled with the same call and the results are stacked along `c`. The stack MAY be stored as `A/1/f0/t2/reg/pheno`, with `registered` true, `resample_rule` set, and `resample_um_per_px` set when the grid differs from the anchor pixel size (D6). `rasterize` places its output in `target_coordinate_system`, so the stack reaches the frame by the identity of D6 and needs no further registration.

```python
import xarray as xr
from spatialdata.models import Image2DModel
from spatialdata.transformations import get_transformation

names = ["DAPI", "GFP", "stain_3", "stain_4", "stain_5"]
arrays = [
    rasterize(
        sdata[f"A/1/f0/t2/pheno/{name}"],                                  # proposed API for the name
        axes=("y", "x"),
        min_coordinate=[ymin, xmin],
        max_coordinate=[ymax, xmax],
        target_coordinate_system="A/1/f0/t2",
        target_unit_to_pixels=1 / 0.325,
    )
    for name in names
]
stack = Image2DModel.parse(
    xr.concat(arrays, dim="c").data,
    dims=("c", "y", "x"),
    c_coords=names,
    transformations={"A/1/f0/t2": get_transformation(arrays[0], to_coordinate_system="A/1/f0/t2")},
)
sdata["A/1/f0/t2/reg/pheno"] = stack                                       # proposed API
```

### The phenotypic image is one more edge into the registered frame

The phenotypic image is one more edge into the registered frame of D5. The frame nodes `frame A/1/f0/t2, tile at t2`, `frame A/1, well`, and `frame plate (optional)` carry the same labels as in the [ISS transformation graph](iss-rounds.md#transformation-graph). That graph also draws the per-image intrinsic systems and their `scale` edges, which this diagram folds into the element nodes. On disk the edges between frames are scene edges in the sidecar (proposed). In memory spatialdata composes them onto each element (existing behaviour), and `get_transformation_between_coordinate_systems(sdata, "A/1/f0/t2", "A/1")` recovers the tile translation, subject to the caveat above on `/` in coordinate-system names.

```{mermaid}
graph LR
  subgraph T2 ["A/1/f0/t2 (registered frame)"]
    R1["iss/r1 (reference)"] -- "scale" --> CS2["frame A/1/f0/t2, tile at t2"]
    RK["iss/r2 to iss/r10"] -- "scale, affine" --> CS2
    PH["pheno"] -- "scale, affine DAPI to DAPI" --> CS2
    SEG["nuclear_seg, cell_seg"] -- "scale" --> CS2
    BB["cell_bbox, bases"] -- "identity" --> CS2
    REG["reg/pheno (MAY)"] -- "identity (D6)" --> CS2
  end
  subgraph UN ["unaligned channels (alternative to pheno)"]
    PD["pheno/DAPI"] -- "scale, affine" --> CS2
    PG["pheno/GFP"] -- "scale, channel correction, nuclear affine" --> CS2
  end
  CS2 -- "translation from tiles row f0" --> W["frame A/1, well"]
  CS3["frame A/1/f0/t3"] -- "same translation" --> W
  W -- "translation from wells row A/1" --> P["frame plate (optional)"]
```

## Sources

- [OME-NGFF 0.5 specification](https://ngff.openmicroscopy.org/0.5/) and its [HCS layout](https://ngff.openmicroscopy.org/0.5/#hcs-layout): the released version the OPS data standard requires; `multiscales`, `axes`, `datasets[].coordinateTransformations`, and nested `labels`.
- [OME-NGFF dev specification, well metadata](https://ngff.openmicroscopy.org/specifications/dev/index.html#well-metadata): `well.images[].path` and `acquisition`, the rule that `path` MUST NOT contain `/`, and the definition of `maximumfieldcount`.
- [OME-NGFF RFC-8: Collections and Extensibility](https://ngff.openmicroscopy.org/rfc/8/index.html#high-content-screening-hcs-metadata): status D1, `multiscale` and `collection` nodes, the `acquisition` and `labels` attributes, prefixed extension keys, and the id character rule.
- [OME-NGFF RFC index](https://ngff.openmicroscopy.org/rfc/index.html): entry point for RFC-5 (status S4), `affine`, `identity`, `byDimension`, and the `scene` attribute.
- [scallops and Biohub OPS layout (HackMD)](https://hackmd.io/@D9GB-ZDcTQyFd7U5aMmk5g/r18soYBuzx): one phenotypic image per well under `stitch/pheno`, nine ISS cycle images, and the `t=` folder labels.
- Chan Zuckerberg Initiative (CZI) OPS data standard v0.1.0 (draft) and its conformance check of a public Biohub submission; no public URL appears in the source material. They supply the 0.5 HCS requirement, the pixel size, the dtypes, the `channels_metadata` key, and the real labels `nuclear_seg`, `cell_seg`, and `gfp_seg`.
- [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119.txt): the meaning of MUST, SHOULD, and MAY.
- [spatialdata documentation](https://spatialdata.scverse.org/en/stable/): v0.8.0 public API used here, `rasterize`, `transform`, `get_pyramid_levels`, `get_transformation`, `get_transformation_between_coordinate_systems`, `join_spatialelement_table`, `TableModel.parse`, and `Image2DModel.parse`.
- [Hierarchical SpatialData slides](https://raw.githubusercontent.com/LucaMarconato/spatialdata/refs/heads/vibecoded-experiment/hierarchical-spatialdata/slides-hierarchical-spatialdata.html): `/` in element names, sub-views, and the tree repr; experimental and unreleased.
- [ngio table specifications](https://biovisioncenter.github.io/ngio/stable/table_specs/overview/): the `condition_table` type used for the `images` table.
