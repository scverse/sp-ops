# Fields of view (tiles)

This page specifies how one well of an optical pooled screening (OPS) plate is split into fields of view (FOVs), which this specification calls tiles. It defines what a tile contains and the well-level tile layout that places each tile in the well. It then shows the layout on disk, in the request for comments 8 (RFC-8) collection view, and in a SpatialData object. Statements fall into the three status categories defined on the [overview page](overview.md#every-statement-is-normative-existing-behaviour-or-a-proposal). Existing behaviour here is Open Microscopy Environment Next-Generation File Format (OME-NGFF) 0.5 high-content screening (HCS) metadata and spatialdata v0.8.0. Names and numbers follow the [running example](design-decisions.md#running-example) of the design record.

## A well MAY be profiled as several tiles

A tile is one stage position in one well, imaged across every acquisition. In OPS every acquisition is one pass of the microscope over the plate. An in situ sequencing (ISS) cycle, also called a sequencing by synthesis (SBS) cycle, is one acquisition. A phenotypic round is another. A tile therefore collects every image taken at one position, plus everything computed from those images.

A well MAY be profiled as several tiles. A writer MUST use the `tiled` profile when a well has more than one tile. It MUST use the `stitched` profile when each acquisition yields one image per well. The profile is declared in `sp-ops:spec.profile` on the plate (see [D2](design-decisions.md#d2-plates-and-wells-stay-valid-ome-ngff-05-the-rfc-8-view-is-a-sidecar)). A stitched well is the one-tile case of this page. The public Biohub OPS submission audited for this specification is a real example. Its store is an OME-NGFF 0.5 HCS plate with one stitched field of view per well, and that field is one `merged` acquisition whose channels were assembled from the ISS cycles and the phenotypic round after registration (D2). The well set, the channel count, and the label names are in the [running example](design-decisions.md#running-example); the directory tree and metadata are in the [stitched profile example](design-decisions.md#stitched-profile-example) of D2.

| Item | `tiled` profile | `stitched` profile |
| --- | --- | --- |
| tiles per well | more than one; `f0`, `f1`, `f2`, `f3` in the running example | one |
| 0.5 image name under the well | the D10 flattening of the hierarchical name, `<tile>-t<t>-iss-r<r>` or `<tile>-t<t>-pheno`, for example `f0-t2-iss-r1` | `t<t>-iss-r<r>`, `t<t>-pheno`, or `t<t>-merged` (D10 rule 6), or `0` for a well with exactly one acquisition (the real Biohub store) |
| acquisition `kind` in `sp-ops:acquisitions` | `iss` or `pheno` | `iss`, `pheno`, or `merged`; `merged` is one stitched image per well assembled from the ISS cycles and the phenotypic round of one `t`, with `r` null, and a writer MUST NOT use it when the raw acquisitions are stored (D2) |
| registered frame | `A/1/f0/t2`, one per (tile, `t`) | `A/1/t2`, RFC-8 id `A-1-t2` (D5) |
| `tiles` shapes element | MUST | not required (D3 defines `tiles` for the `tiled` profile only) |
| `sp-ops:tile` and `sp-ops:tileLayout` | MUST | not used |
| RFC-8 tile collection (proposed) | one per tile under the well | omitted; `t` collections sit directly under the well |

Each tile is a container of images, labels, points, shapes, and tables. It holds one sub-container per fixation timepoint `t`, because the cells fixed at different `t` are different cells and are never aligned (see [D4](design-decisions.md#d4-timepoints-and-cycles-are-separate-elements-only-aligned-channels-are-stacked)). The `t` values of the running example are folder labels from the scallops layout, not measured timepoints (see the [running example](design-decisions.md#running-example)). Inside one (tile, `t`) the running example holds the following elements. The element paths follow [D10](design-decisions.md#d10-element-names-are-the-on-disk-paths-and-a-hyphen-flattens-them-for-v080).

```text
A/1/f0/t2/iss/r1 ... iss/r10   images   nine ISS cycles (no r6), (5, 2048, 2048) float32 each
A/1/f0/t2/pheno                image    phenotypic round, (5, 2048, 2048)
A/1/f0/t2/spots/max            image    derived spot image, (4, 2048, 2048)
A/1/f0/t2/spots/std            image    derived spot image, (1, 2048, 2048)
A/1/f0/t2/spots/peaks          points   detected spots
A/1/f0/t2/bases                points   base calls
A/1/f0/t2/nuclear_seg          labels   (2048, 2048) int32
A/1/f0/t2/cell_seg             labels   (2048, 2048) int32
A/1/f0/t2/cell_bbox            shapes   one rectangle per cell, index equals the label value
```

Tables that describe cells or images across the whole well live at the well level, not inside a tile. They are `images`, `fov_features`, `cells`, and `reads` (see [D7](design-decisions.md#d7-cell-features-annotate-the-labels-fov-features-annotate-the-footprints-well-features-annotate-the-wells)). The `tile` column of `images` and of `cells` is the join back to a tile. The tile shape and the counts above are illustrative; the label names and the int32 dtype are real values from the audit.

## The tile layout is one shapes row per tile

Every well in the `tiled` profile MUST contain a shapes element named `tiles`. It is a spatialdata `ShapesModel` element, so it is a GeoDataFrame in memory and a GeoParquet file inside a Zarr group on disk. The schema is normative and comes from [D3](design-decisions.md#d3-a-tile-is-a-collection-of-per-timepoint-collections-and-the-layout-is-a-shapes-element).

| Column | Type | Requirement | Meaning |
| --- | --- | --- | --- |
| index | integer, unique | MUST | equals `sp-ops:tile.index` of the tile collection |
| `geometry` | Polygon, axis-aligned rectangle | MUST | the nominal tile extent in the well coordinate system, in micrometres |
| `tile` | string | MUST | equals the tile path component, `f0` |
| `grid_row`, `grid_col` | integer | SHOULD | position in the acquisition grid, zero-based |
| `stage_x`, `stage_y` | float, micrometre | MAY | raw stage coordinates as reported by the microscope |
| `n_timepoints` | integer | MAY | number of `t` collections under the tile |

`tiles` has exactly one row per tile, never one per acquisition. The element MUST carry an identity transformation to the well coordinate system, named `A/1` for the running example (see [D5](design-decisions.md#d5-cycles-are-registered-to-the-dapi-channel-of-the-first-iss-cycle-at-each-timepoint)). The polygon is the nominal extent of the tile, so neighbouring rectangles overlap by the acquisition overlap.

Acquisition references are not columns of `tiles`. Every well MUST also contain a shapes element named `footprints`. It holds one rectangle per acquisition image element, in the well coordinate system, indexed by the integer `image_id`. The well table `images` annotates `footprints` and carries `tile`, `acquisition`, `t`, and `r` per image. A reader that needs "the images of tile `f0` at cycle `r2`" filters `images`, not `tiles`.

The layout serves two purposes.

- Stitching. The translation from each registered (tile, `t`) frame `A/1/f0/t2` into the well frame `A/1` is the offset of that tile's rectangle. In the RFC-8 sidecar (proposed) these translations are the edges of the well scene, and their values come from `tiles`. Per-acquisition stage jitter lives in the registration affines of D5, not in duplicate layout rows. `footprints` records the registered extent of each image and is the geometry from which resampling boxes are computed (see [D6](design-decisions.md#d6-resampling-uses-the-largest-contained-box-by-default)).
- Spatial joins. A polygon or bounding box in the well frame selects tiles with `polygon_query` or `bounding_box_query` (existing behaviour, spatialdata v0.8.0). The `tile` column of `cells` and `images` equals the `tiles` index, so a tile row joins to its cells and images by key without any geometry.

An ngio `roi_table` MAY be derived from `tiles` for Fractal tooling. ngio requires the columns `x_micrometer`, `y_micrometer`, `z_micrometer`, `len_x_micrometer`, `len_y_micrometer`, and `len_z_micrometer`, and uses `FieldIndex` as the default index key (existing behaviour, ngio table specifications). A two-dimensional tile layout still writes the two `z` columns. The shapes element is authoritative; the derived table MUST NOT be the only copy of the layout.

The table and block below give the rows of `tiles` for well `A/1`. The rectangle size follows from the tile shape and the real pixel size; the step is illustrative.

| Quantity | Value | Status |
| --- | --- | --- |
| tile shape in pixels | `2048 x 2048` | illustrative |
| pixel size | `0.325` micrometre | real (audit) |
| tile width in micrometres | `665.6` | derived |
| grid step in micrometres | `599.0` | illustrative; gives the overlap |

```text
index  tile  grid_row  grid_col  geometry
0      f0    0         0         POLYGON ((0 0, 665.6 0, 665.6 665.6, 0 665.6, 0 0))
1      f1    0         1         POLYGON ((599.0 0, 1264.6 0, 1264.6 665.6, 599.0 665.6, 599.0 0))
2      f2    1         0         POLYGON ((0 599.0, 665.6 599.0, 665.6 1264.6, 0 1264.6, 0 599.0))
3      f3    1         1         POLYGON ((599.0 599.0, 1264.6 599.0, 1264.6 1264.6, 599.0 1264.6, 599.0 599.0))
```

## File format example

The tree below shows well `A/1` in the OME-NGFF 0.5 layout of [D2](design-decisions.md#d2-plates-and-wells-stay-valid-ome-ngff-05-the-rfc-8-view-is-a-sidecar). The 0.5 well metadata requires that `well.images[].path` contains no `/`. Every image is therefore a direct child of the well, and the tile is the leading component of its name. Only tile `f0` at `t2` is expanded. The `tiles` group is the layout element.

```text
ops_plate.zarr/A/1/
├── zarr.json                      # ome.well.images: 320 entries, one per tile and acquisition
├── collection.json                # (proposed) RFC-8 well collection: sp-ops:tileLayout, tile collections, scenes
├── tiles/                         # shapes, 4 rows, the tile layout
│   ├── zarr.json                  # encoding-type ngff:shapes, identity to coordinate system A/1
│   └── shapes.parquet             # GeoParquet: tile, grid_row, grid_col, geometry
├── footprints/                    # shapes, 320 rows, one registered rectangle per acquisition image
├── images/                        # table, 320 rows, annotates footprints; columns tile, acquisition, t, r
├── fov_features/                  # table, 320 rows, per-image quality control (QC) metrics (MAY)
├── cells/                         # table, annotates every cell_seg in the well; column tile
├── reads/                         # table, one row per read
├── f0-t2-iss-r1/                  # tile f0, t2, ISS cycle 1; zarr.json carries sp-ops:tile {"index": 0}
├── f0-t2-iss-r2/
├── ...                            # f0-t2-iss-r3 ... f0-t2-iss-r10 (no r6)
├── f0-t2-pheno/
│   ├── zarr.json
│   ├── 0/ 1/ 2/                   # pyramid levels
│   └── labels/
│       ├── nuclear_seg/
│       └── cell_seg/
├── f0-t2-spots-max/               # derived image
├── f0-t2-spots-std/
├── f0-t2-spots-peaks/             # points: x, y, read
├── f0-t2-bases/                   # points: x, y, read, r, base, cell_label
├── f0-t2-cell_bbox/               # shapes
├── ...                            # f0-t3-... to f0-t10-...
├── f1-t2-iss-r1/                  # tile f1; zarr.json carries sp-ops:tile {"index": 1}
└── ...                            # f1-..., f2-..., f3-...
```

The `zarr.json` of the `tiles` group below was written by spatialdata v0.8.0 for the four rows above (existing behaviour, probe-verified). spatialdata writes the geometry as `shapes.parquet` next to it, readable with `geopandas.read_parquet` without spatialdata. The group attributes carry `encoding-type`, `axes`, `coordinateTransformations`, and `spatialdata_attrs`. The transformation is the identity into the well coordinate system `A/1`, with `input` and `output` objects keyed by `name`. spatialdata writes the shapes axes in `x, y` order, and the D5 scene lists the well frame as `y, x`. Both describe the same frame, so a validator that compares the sidecar with this copy matches axes by `name`, not by position. spatialdata v0.8.0 writes the placeholder string `"unit"` for axis units. This specification fixes the unit as micrometre through the definition of the well coordinate system in D5.

```json
{
  "zarr_format": 3,
  "node_type": "group",
  "attributes": {
    "encoding-type": "ngff:shapes",
    "axes": ["x", "y"],
    "coordinateTransformations": [
      {
        "type": "identity",
        "input": {
          "name": "xy",
          "axes": [
            {"name": "x", "type": "space", "unit": "unit"},
            {"name": "y", "type": "space", "unit": "unit"}
          ]
        },
        "output": {
          "name": "A/1",
          "axes": [
            {"name": "x", "type": "space", "unit": "unit"},
            {"name": "y", "type": "space", "unit": "unit"}
          ]
        }
      }
    ],
    "spatialdata_attrs": {"version": "0.3"}
  }
}
```

:::{admonition} Status
:class: note
The content of the `tiles` group is what spatialdata v0.8.0 writes today. Its location directly under the well (`A/1/tiles`) follows the flat layout of the experimental hierarchical SpatialData branch (proposed, not released). That layout drops the `shapes/` type folder and scans for `spatialdata_attrs.element_type`. The `zarr.json` above has no `element_type` because v0.8.0 does not write it. A hierarchical writer adds `"element_type": "shapes"` to `spatialdata_attrs` (proposed), so the block above is the v0.8.0 content at the proposed location. A v0.8.0 writer places the same group at `<store>/shapes/A-1-tiles/` with the flattened name of D10. The columns of `shapes.parquet` are `tile` (string), `grid_row` and `grid_col` (int64), and `geometry`; the integer index is stored as the parquet index (probe-verified).
:::

## RFC-8 marks a tile as a collection with `sp-ops:tile`

:::{admonition} Status
:class: note
RFC-8 (collections and extensibility) is at status D1, an early draft. Everything in this section is a proposal of this specification and can change with the RFC. The well document is the standalone `collection.json` sidecar of D2, referenced from the plate document by the RFC-8 path type `json`. An RFC-8 reader that does not know the `sp-ops` prefix treats its values as opaque, as the [extension page](extension.md#the-extension-follows-rfc-8-prefixed-naming-with-the-prefix-sp-ops) explains, so it still sees the well, its tiles, and its images. `"0.x"` is the placeholder version string RFC-8 uses in its own examples.
:::

Three identifiers from the [extension key registry](design-decisions.md#extension-key-registry) describe tiles. Every identifier is spelled `sp-ops:<key>`, following the prefix rule on the [extension page](extension.md#the-extension-follows-rfc-8-prefixed-naming-with-the-prefix-sp-ops).

| Identifier | Kind | Applies to | Type | Required | Meaning |
| --- | --- | --- | --- | --- | --- |
| `sp-ops:tile` | attribute key | tile collection (RFC-8) or image group (0.5) | `{"index": integer}` | MUST in the `tiled` profile | the tile a node belongs to; equals `tiles` index |
| `sp-ops:tileLayout` | attribute key | well collection | RFC-8 `Reference` | MUST in the `tiled` profile | the `sp-ops:shapes` node holding the tile layout |
| `sp-ops:shapes` | node type | collection nodes | node with `path` | as needed | a spatialdata `ShapesModel` element (GeoParquet inside a Zarr group) |

The rules for these identifiers are as follows.

- A tile is a `collection` node under the well, marked with `sp-ops:tile`. Its `index` MUST equal the `tiles` row index, and its `name` MUST equal the `tile` column of that row.
- A tile collection contains one `collection` per fixation timepoint, marked with `sp-ops:timepoint`. The registration scene of that timepoint lives there (D5).
- The well collection MUST carry `sp-ops:tileLayout`, an RFC-8 `Reference` (`id`, optional `path`) to the `sp-ops:shapes` node that holds `tiles`. The referenced node MUST be a child of the well collection.
- RFC-8 ids MUST match `[a-zA-Z0-9-_.]+`, so ids are the hierarchical names with `/` replaced by `-` (D10).
- In the 0.5 layout the well group has no `sp-ops:tileLayout`. The fixed element name `tiles` locates the layout, and each image group carries `sp-ops:tile` as a sibling of `ome` (D3; the sibling placement follows D1).

The block below is well `A/1/collection.json` (proposed). It shows the layout reference, the two shapes nodes, the `images` table node, and two tile collections. Tile `f0` is expanded to its `t2` collection, which shows the `iss` collection with one cycle, the `pheno` image, and the `cell_seg` labels. The other elements of that timepoint are omitted. The `scene` and `sp-ops:relationships` attributes are omitted here and shown in D5 and D9. References into the plate document carry a `path` (D5).

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
      {"type": "sp-ops:shapes", "id": "A-1-tiles", "name": "tiles",
       "path": {"type": "zarr", "path": "./tiles"}},
      {"type": "sp-ops:shapes", "id": "A-1-footprints", "name": "footprints",
       "path": {"type": "zarr", "path": "./footprints"}},
      {"type": "sp-ops:table", "id": "A-1-images", "name": "images",
       "path": {"type": "zarr", "path": "./images"},
       "attributes": {"sp-ops:table": {"type": "condition_table", "tableVersion": "1",
                                       "granularity": "image", "region": {"id": "A-1-footprints"}}}},
      {"type": "collection", "id": "A-1-f0", "name": "f0",
       "attributes": {"sp-ops:tile": {"index": 0}},
       "nodes": [
         {"type": "collection", "id": "A-1-f0-t2", "name": "t2",
          "attributes": {"sp-ops:timepoint": {"index": 2}},
          "nodes": [
            {"type": "collection", "id": "A-1-f0-t2-iss", "name": "iss", "nodes": [
              {"type": "multiscale", "id": "A-1-f0-t2-iss-r1", "name": "r1",
               "path": {"type": "zarr", "path": "./f0-t2-iss-r1"},
               "attributes": {"acquisition": {"id": "iss-t2-r1", "path": {"type": "json", "path": "../../collection.json"}}}}
            ]},
            {"type": "multiscale", "id": "A-1-f0-t2-pheno", "name": "pheno",
             "path": {"type": "zarr", "path": "./f0-t2-pheno"},
             "attributes": {"acquisition": {"id": "pheno-t2", "path": {"type": "json", "path": "../../collection.json"}}}},
            {"type": "multiscale", "id": "A-1-f0-t2-cell_seg", "name": "cell_seg",
             "path": {"type": "zarr", "path": "./f0-t2-pheno/labels/cell_seg"},
             "attributes": {"labels": {"source": [{"id": "A-1-f0-t2-pheno"}]}}}
          ]}
       ]},
      {"type": "collection", "id": "A-1-f1", "name": "f1",
       "attributes": {"sp-ops:tile": {"index": 1}},
       "nodes": [
         {"type": "collection", "id": "A-1-f1-t2", "name": "t2",
          "attributes": {"sp-ops:timepoint": {"index": 2}},
          "nodes": []}
       ]}
    ]
  }
}
```

The same `sp-ops:tile` value appears in the 0.5 layout on every image group of the tile, as a sibling of `ome` in the Zarr group attributes. The D1 example of the design record shows the full image group.

```json
{
  "zarr_format": 3,
  "node_type": "group",
  "attributes": {
    "ome": {"version": "0.5", "multiscales": ["..."]},
    "sp-ops:tile": {"index": 0}
  }
}
```

## A tile is a name prefix in the SpatialData view

:::{admonition} Status
:class: note
The hierarchical repr below depends on the experimental hierarchical SpatialData branch, which is not released. That branch allows `/` in element names, returns a sub-view for a prefix, and groups the repr by the first path component only. The format follows `_gen_repr` on that branch. spatialdata v0.8.0 rejects `/` in names and prints the flat, typed repr shown at the end of this section (probe-verified).
:::

A tile is a name prefix. `sdata["A/1/f0"]` returns the tile as a sub-view, and `sdata["A/1/f0/t2"]` returns one fixation timepoint (proposed). The repr below is for a partial read of well `A/1`, which is why element names have no `A/1/` prefix while coordinate system names keep it. Two tiles are expanded at `t2`. The other timepoints and tiles are collapsed to their element counts. A real repr prints every element. Row counts are illustrative except the 859 cells; the 4 tiles and the 320 images follow from the illustrative 2 by 2 grid of the running example.

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
│   ├── t2/bases: [Points2D] DataFrame (598211, 6)
│   ├── t2/cell_bbox: [Shapes] GeoDataFrame (842, 1)
│   ├── t2/cell_seg: [Labels2D] DataTree[yx] (2048, 2048), (1024, 1024), (512, 512)
│   ├── t2/iss/r1: [Image2D] DataTree[cyx] (5, 2048, 2048), (5, 1024, 1024), (5, 512, 512)
│   ├── t2/iss/r2: [Image2D] DataTree[cyx] (5, 2048, 2048), (5, 1024, 1024), (5, 512, 512)
│   ├── t2/iss/r10: [Image2D] DataTree[cyx] (5, 2048, 2048), (5, 1024, 1024), (5, 512, 512)
│   ├── t2/nuclear_seg: [Labels2D] DataTree[yx] (2048, 2048), (1024, 1024), (512, 512)
│   ├── t2/pheno: [Image2D] DataTree[cyx] (5, 2048, 2048), (5, 1024, 1024), (5, 512, 512)
│   ├── t2/spots/max: [Image2D] DataArray[cyx] (4, 2048, 2048)
│   ├── t2/spots/peaks: [Points2D] DataFrame (69870, 3)
│   └── t2/spots/std: [Image2D] DataArray[cyx] (1, 2048, 2048)
├── f2/ (136 elements)
└── f3/ (136 elements)
with coordinate systems:
    ▸ 'A/1', with elements:
        f0/t2/bases, f0/t2/cell_bbox, f0/t2/cell_seg, f0/t2/iss/r1, f0/t2/iss/r2, f0/t2/iss/r10, f0/t2/nuclear_seg, f0/t2/pheno, f0/t2/spots/max, f0/t2/spots/peaks, f0/t2/spots/std, f1/t2/bases, f1/t2/cell_bbox, f1/t2/cell_seg, f1/t2/iss/r1, f1/t2/iss/r2, f1/t2/iss/r10, f1/t2/nuclear_seg, f1/t2/pheno, f1/t2/spots/max, f1/t2/spots/peaks, f1/t2/spots/std, footprints, tiles
    ▸ 'A/1/f0/t2', with elements:
        f0/t2/bases, f0/t2/cell_bbox, f0/t2/cell_seg, f0/t2/iss/r1, f0/t2/iss/r2, f0/t2/iss/r10, f0/t2/nuclear_seg, f0/t2/pheno, f0/t2/spots/max, f0/t2/spots/peaks, f0/t2/spots/std
    ▸ 'A/1/f1/t2', with elements:
        f1/t2/bases, f1/t2/cell_bbox, f1/t2/cell_seg, f1/t2/iss/r1, f1/t2/iss/r2, f1/t2/iss/r10, f1/t2/nuclear_seg, f1/t2/pheno, f1/t2/spots/max, f1/t2/spots/peaks, f1/t2/spots/std
    ▸ 'plate', with elements:
        f0/t2/bases, f0/t2/cell_bbox, f0/t2/cell_seg, f0/t2/iss/r1, f0/t2/iss/r2, f0/t2/iss/r10, f0/t2/nuclear_seg, f0/t2/pheno, f0/t2/spots/max, f0/t2/spots/peaks, f0/t2/spots/std, f1/t2/bases, f1/t2/cell_bbox, f1/t2/cell_seg, f1/t2/iss/r1, f1/t2/iss/r2, f1/t2/iss/r10, f1/t2/nuclear_seg, f1/t2/pheno, f1/t2/spots/max, f1/t2/spots/peaks, f1/t2/spots/std, footprints, tiles
```

The `tiles` element has four rows and four columns (`tile`, `grid_row`, `grid_col`, `geometry`). It appears in the well frame `A/1` and, when the optional plate frame exists, in `plate`. The elements of each tile appear in their registered frame `A/1/f0/t2`, in the well frame, and in the plate frame. The reader composes one transformation per ancestor frame onto each element (D5), so the `'A/1'` and `'plate'` listings are identical and a `t` frame lists only the elements of that (tile, `t`). The branch prints an element under every coordinate system in its transformation dictionary (`_gen_repr`).

With spatialdata v0.8.0 the same layout element is stored under its flattened name and printed by the flat repr (existing behaviour, probe-verified).

```text
SpatialData object, with associated Zarr store: /data/ops_plate.zarr
└── Shapes
      └── 'A-1-tiles': GeoDataFrame shape: (4, 4) (2D shapes)
with coordinate systems:
    ▸ 'A/1', with elements:
        A-1-tiles (Shapes)
```

## Example: reading the layout and querying one tile

`polygon_query` and `bounding_box_query` are spatialdata v0.8.0 names with the signatures shown in the comments (probe-verified). Both take a `target_coordinate_system`, and the query geometry is expressed in that frame. Passing a SpatialData object filters every element that has a transformation into that frame. Lines that use `/` in element names or a prefix sub-view carry a `# proposed API` comment, where API is an application programming interface.

```python
import geopandas as gpd
from spatialdata import SpatialData, bounding_box_query, polygon_query

# polygon_query(element, polygon, target_coordinate_system, filter_table=True, clip=False)
# bounding_box_query(element, axes, min_coordinate, max_coordinate, target_coordinate_system,
#                    return_request_only=False, filter_table=True)

well = SpatialData.read("ops_plate.zarr/A/1")                     # partial read of one well; proposed API
tiles = well["tiles"]                                             # GeoDataFrame with 4 rows

# without spatialdata: the GeoParquet file inside the shapes group (plain GeoDataFrame, no transformation)
tiles_gdf = gpd.read_parquet("ops_plate.zarr/A/1/tiles/shapes.parquet")   # proposed layout; v0.8.0 writes shapes/A-1-tiles/shapes.parquet

f0 = tiles.loc[0]                                                 # index 0 equals sp-ops:tile.index
assert f0.tile == "f0"

# everything that overlaps the nominal extent of tile f0 in the well frame;
# the overlap strips of f1, f2, and f3 are included because the rectangles overlap
overlap = polygon_query(well, polygon=f0.geometry, target_coordinate_system="A/1")

# the elements that belong to tile f0, by name prefix rather than by geometry
tile = well["f0"]                                                  # proposed API
t2 = tile["t2"]                                                    # same as well["f0/t2"]; proposed API

# a 300 micrometre window at the top-left corner of tile f0, in the well frame
minx, miny, maxx, maxy = f0.geometry.bounds
window = bounding_box_query(
    well,
    axes=("y", "x"),
    min_coordinate=[miny, minx],
    max_coordinate=[miny + 300.0, minx + 300.0],
    target_coordinate_system="A/1",
)

# which tiles does an arbitrary point of the well fall in
hits = polygon_query(tiles, polygon=f0.geometry.centroid.buffer(1.0), target_coordinate_system="A/1")
hits.tile.tolist()                                                 # ['f0']
```

A GeoDataFrame read with geopandas carries no coordinate transformation, so `polygon_query` and `bounding_box_query` accept only the element returned by spatialdata (probe-verified). The two queries answer different questions. The geometric query returns pixels and objects inside a region of the well, whichever tile recorded them. That is what a viewer or a stitching check needs. The prefix sub-view returns the container of one tile, which is what a per-tile processing step needs.

## Sources

- [OME-NGFF RFC-8: Collections and Extensibility](https://ngff.openmicroscopy.org/rfc/8/index.html#high-content-screening-hcs-metadata) and the [OME-NGFF RFC index](https://ngff.openmicroscopy.org/rfc/index.html): Node, Collection, Path, and Reference interfaces, HCS `plate`, `well`, and `acquisition` attributes, extension naming with prefixes, the rule that unknown prefixed values are opaque (status D1), and the entry point for RFC-5 coordinate systems.
- [OME-NGFF dev specification, plate metadata](https://ngff.openmicroscopy.org/specifications/dev/index.html#plate-metadata) and [well metadata](https://ngff.openmicroscopy.org/specifications/dev/index.html#well-metadata): `acquisitions`, `maximumfieldcount`, `field_count`, `rows`, `columns`, `wells`; `well.images[].path` MUST NOT contain `/`, which forces the flat well of the 0.5 layout.
- [OME-NGFF 0.5](https://ngff.openmicroscopy.org/0.5/) and its [HCS layout](https://ngff.openmicroscopy.org/0.5/#hcs-layout): the released version the OPS data standard requires.
- [scallops and Biohub OPS layout (HackMD)](https://hackmd.io/@D9GB-ZDcTQyFd7U5aMmk5g/r18soYBuzx): real pipeline output names (well `A1`, cycles, `A1-peaks.parquet`, `A1-objects.parquet`, `segment.zarr` labels) and the Biohub submission layout with one stitched field of view per well.
- Chan Zuckerberg Initiative (CZI) OPS data standard v0.1.0 (draft) and the conformance check of a public Biohub submission: the audited OME-NGFF 0.5 HCS plate (wells `A/1` to `A/3`, one stitched field per well, six channels, `0.325` micrometre per pixel, real label names). No public URL appears in the source material.
- [spatialdata documentation](https://spatialdata.scverse.org/en/stable/): v0.8.0 public API used here, `bounding_box_query`, `polygon_query`, `ShapesModel`, `SpatialData.read`, and the on-disk shapes group (`shapes.parquet`, `encoding-type: "ngff:shapes"`).
- [geopandas documentation](https://geopandas.org/en/stable/): `read_parquet` for reading the GeoParquet file of the `tiles` group without spatialdata.
- [Hierarchical SpatialData slides](https://raw.githubusercontent.com/LucaMarconato/spatialdata/refs/heads/vibecoded-experiment/hierarchical-spatialdata/slides-hierarchical-spatialdata.html): `/` in element names, prefix sub-views, partial reads, the tree repr, and the flat Zarr layout without type folders; experimental, not released.
- [ngio table specifications](https://biovisioncenter.github.io/ngio/stable/table_specs/overview/): `roi_table` required columns `x_micrometer`, `y_micrometer`, `z_micrometer`, `len_x_micrometer`, `len_y_micrometer`, `len_z_micrometer` and default index key `FieldIndex`.
- [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119.txt): the meaning of MUST, SHOULD, and MAY.
