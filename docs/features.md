# Features

This page specifies how measured features are stored in an optical pooled screening (OPS) store. Features exist at three granularities, namely per cell, per field of view (FOV) image, and per well. A FOV image is one camera image of one tile at one acquisition, the `image` granularity of the design record. Each granularity is one spatialdata table that annotates one spatial element, or one list of elements for the cell table. For each table, the page fixes the annotated element, the `spatialdata_attrs` keys, and the required and recommended columns. It also relates each table to the OPS data standard `cell_data.parquet` and to CellProfiler output. Names, counts, and the plate `ops_plate.zarr` come from the [running example](design-decisions.md#running-example) of the design record.

Statements fall into the three status categories defined on the [overview page](overview.md#every-statement-is-normative-existing-behaviour-or-a-proposal). Requirements use MUST, SHOULD, and MAY in the sense of request for comments (RFC) 2119. Existing behaviour here is Open Microscopy Environment Next-Generation File Format (OME-NGFF) 0.5 high-content screening (HCS) metadata, spatialdata v0.8.0, ngio, and the OPS data standard v0.1.0. Proposals carry a "Status" note, an inline "(proposed)" tag, or a `# proposed API` comment on a code line, where API is an application programming interface. Hierarchical element names such as `A/1/cells` are proposed; the released spatialdata v0.8.0 spells the same element `A-1-cells` (see [D10](design-decisions.md#d10-element-names-are-the-on-disk-paths-and-a-hyphen-flattens-them-for-v080) of the design record).

## Three granularities are three tables

The table below is the summary. The rows restate decision D7 of the design record, which is the [authoritative text](design-decisions.md#d7-cell-features-annotate-the-labels-fov-features-annotate-the-footprints-well-features-annotate-the-wells).

| Granularity | Table | Requirement | Annotates (`region`) | `region_key` | `instance_key` | ngio `table_type` | `granularity` |
| --- | --- | --- | --- | --- | --- | --- | --- |
| cell | `A/1/cells`, one per well | MUST | every `cell_seg` labels element in the well (a list) | `region` | `label` | `feature_table` | `cell` |
| FOV | `A/1/fov_features`, one per well | MAY | `A/1/footprints` (shapes, one rectangle per camera image) | `region` | `image_id` | `feature_table` | `image` |
| well | `well_features`, at the plate root | MAY | `wells` (shapes, one rectangle per well) | `region` | `well_id` | `feature_table` | `well` |

Every feature table MUST be a spatialdata `TableModel` element with `uns["spatialdata_attrs"]` holding exactly `region`, `region_key`, and `instance_key` (existing behaviour of `TableModel.parse`). Every feature table MUST also carry `uns["sp-ops"]` with `table_type`, `table_version`, and `granularity` as decision [D8](design-decisions.md#d8-table-types-use-the-ngio-vocabulary-under-one-namespaced-dictionary) defines. The `feature_table` string and the feature type vocabulary (`measurement`, `categorical`, `metadata`) are the ngio names. ngio itself points a feature table at a label image. This specification widens the region to a shapes element for the FOV and well tables (D8).

```{mermaid}
graph LR
  subgraph W ["A/1 (well)"]
    CELLS["cells (table)"] -- "region, instance_key label" --> SEG["f0/t2/cell_seg ... (labels, one per frame)"]
    FOV["fov_features (table)"] -- "region, instance_key image_id" --> FP["footprints (shapes)"]
    IMG["images (table)"] -- "region, instance_key image_id" --> FP
  end
  WF["well_features (table, plate root)"] -- "region, instance_key well_id" --> WL["wells (shapes, plate root)"]
  CELLS -. "aggregated per well" .-> WF
  FOV -. "aggregated per well" .-> WF
```

## Cell-level features are the unit of biological interpretation

A cell-level feature is a number measured on one segmented or masked object. Examples are its area, its shape, and the mean intensity of one channel inside it. In the running example the objects come from the `cell_seg` and `nuclear_seg` label images of each (tile, `t`) frame, and the measurements are CellProfiler features. These are the values that downstream analysis compares across perturbations, so this table is the one that leaves the store as `cell_data.parquet`.

The table is `A/1/cells`, one per well. It annotates the list of every `cell_seg` labels element in the well, so one table covers every frame of the well. `region_key` is `region` and `instance_key` is `label`, the integer pixel value of the object. The label value is what CellProfiler measured, so the join to pixels is exact. spatialdata v0.8.0 accepts a list as `region` (existing behaviour, probe-verified).

| Slot | Column | Type | Requirement | Meaning |
| --- | --- | --- | --- | --- |
| `obs` | `region` | string | MUST | the labels element the row belongs to, `A/1/f0/t2/cell_seg` |
| `obs` | `label` | integer | MUST | the label pixel value; the `instance_key` |
| `obs` | `cell_uid` | string | MUST, unique across the aggregation | SHOULD have the form `<row><col>_<tile>_t<t>_<label>`, `A1_f0_t2_812` |
| `obs` | `tile`, `t` | integer | MUST | the frame the cell was segmented in; `tile` equals the `tiles` index |
| `obs` | `perturbation_id`, `barcode` | string, nullable | SHOULD once assigned | the perturbation call and the guide it came from ([D11](design-decisions.md#d11-bases-are-points-bounding-boxes-are-shapes-reads-and-features-are-tables)) |
| `obs` | `n_reads`, `qc_pass` | integer, boolean | SHOULD once assigned | read support and the cell-level quality control (QC) verdict |
| `var` | index | string | MUST | the CellProfiler feature name, unique across compartments; SHOULD carry the compartment prefix, `cell_AreaShape_Area` |
| `var` | `compartment` | string | MUST | `cell`, `cytosol`, or `nuclei`, the scallops feature folders |
| `var` | `feature_type` | string | MUST | `measurement`, `categorical`, or `metadata`, the ngio vocabulary |
| `X` | | numeric, float32 SHOULD | MUST | one value per cell and feature |
| `obsp` | any | sparse matrix | MAY | spatial neighbour graphs for cell to cell relations |
| `obsm` | `spatial` | float (n, 2) | MAY | cell centroids in the well frame for legacy tools; labels and `cell_bbox` are authoritative |

The compartment prefix on the `var` index keeps names unique when the three CellProfiler files are joined side by side (D7). A `nuclei` table with the same schema annotating `nuclear_seg` MAY be added when nuclear and cell label values do not match one to one (D7).

`X` MUST be numeric and SHOULD be float32 (D7). A feature marked `categorical` in `var` is therefore stored in `X` as integer codes. A `metadata` column that is not numeric cannot be a column of `X` and belongs in `obs`.

The table maps onto the scallops CellProfiler output as follows; this is existing behaviour of the scallops layout. The scallops pipeline writes `features/cell/A1.parquet`, `features/cytosol/A1.parquet`, and `features/nuclei/A1.parquet`, one CellProfiler feature parquet per compartment, next to `-objects.parquet` bounding boxes. It writes the perturbation call per cell to `merge/A1.parquet`. This specification builds `cells` by joining the three parquet files on the object label and takes `barcode` and `perturbation_id` from `merge` (D11). The bounding boxes become the `cell_bbox` shapes element, not table columns (D11).

The OPS data standard v0.1.0 is existing behaviour. Its `cell_data.parquet` has one row per cell, a globally unique `cell_uid`, and a `perturbation_id` foreign key into `perturbation_library.csv`. The optional `feature_definitions.csv` is a catalog of the feature columns. This specification maps them as follows.

| OPS artifact | sp-ops source | Rule |
| --- | --- | --- |
| `cell_data.parquet` rows | `cells.obs` joined with `cells.to_df()`, concatenated over wells | `cell_uid` and `perturbation_id` MUST be carried unchanged |
| `cell_data.parquet` feature columns | `cells.var` index | one parquet column per `var` row |
| `feature_definitions.csv` | `cells.var` | `compartment` and `feature_type` are candidate definition fields |
| `perturbation_library.csv` | `library` table at the plate root | a validator MUST check that every non-null `perturbation_id` in `cells` exists in `library` |

The audited public submission fails the last check on retired gene symbols, for example `AARS` in `cell_data.parquet` against `AARS1` in the library. The [running example](design-decisions.md#running-example) records the counts.

## FOV-level features measure one camera image and serve quality control

A FOV-level feature is a property of one camera exposure, not of an object in it. Examples are a focus score, the background level, a vignetting or uneven-background measure, and the signal-to-noise ratio. These values decide which images enter base calling and which cells are trusted, so they are QC data. They are rarely of biological interest on their own.

The table is `A/1/fov_features`, one per well, and a writer MAY omit it. It annotates `A/1/footprints`, the shapes element with one rectangle per acquisition image element in the well ([D3](design-decisions.md#d3-a-tile-is-a-collection-of-per-timepoint-collections-and-the-layout-is-a-shapes-element)). `region_key` is `region` and `instance_key` is `image_id`, the footprint index. The `images` condition table annotates the same element with the same `image_id` ([D4](design-decisions.md#d4-timepoints-and-cycles-are-separate-elements-only-aligned-channels-are-stacked)). The two tables therefore share a row key, and a pandas merge on `image_id` attaches `tile`, `acquisition`, `kind`, `t`, `r`, and `c` to every QC row. The tables stay separate because `images` is required and mirrors the JSON metadata, while `fov_features` is optional and holds measurements. `footprints` stands in for the images for the reason given in [A table keeps track of t, r, and c](iss-rounds.md#a-table-keeps-track-of-t-r-and-c) (D3).

| Slot | Column | Type | Requirement | Meaning |
| --- | --- | --- | --- | --- |
| `obs` | `region` | string | MUST | `A/1/footprints` on every row |
| `obs` | `image_id` | integer | MUST | the footprint rectangle of the camera image; the `instance_key` |
| `obs` | `qc_pass` | boolean | SHOULD | the per-image verdict after thresholds are applied |
| `var` | index | string | MUST | metric names; not fixed by this specification |
| `var` | `feature_type` | string | MAY | `measurement`, `categorical`, or `metadata` |
| `X` | | numeric, float32 SHOULD | MUST | one value per image and metric |

The `qc_pass` column mirrors the same column on `cells` (D7) and `reads` (D11), so one name means "passed QC" at every granularity (D7). Metric names are the depositor's. The running example uses `focus_score`, `background_level`, `background_gradient`, and `snr` among its columns; all names are illustrative.

The OPS data standard defines no per-image artifact. Its artifact list holds collection metadata, the perturbation library, example images, experimental metadata, aggregated data, feature definitions, the single-cell feature table, and the image store. FOV QC reaches `cell_data.parquet` only through the cell-level `qc_pass` column, which a writer SHOULD derive from the frames a cell was measured in.

## Well-level features are optional and mostly derived

A well-level feature summarises one well. Two kinds exist. The first kind is QC at a broader scale. Examples are stitching and alignment residuals between tiles, and global variation such as uneven seeding or cell clumping at one side of the well. The second kind is cell to cell relation in space, for example a k-nearest-neighbour graph or neurite connectivity, which can carry biological meaning. Whether any of this is written depends on the depositor. Well-level features presuppose FOVs that are stitched into one well image. In the `tiled` profile of [D2](design-decisions.md#d2-plates-and-wells-stay-valid-ome-ngff-05-the-rfc-8-view-is-a-sidecar) the stitching and alignment residuals between tiles are the QC kind. In the `stitched` profile each acquisition yields one image per well (D2), and `well_features` is the table that describes those images.

Most well-level values are aggregates of the cell and FOV tables. Seeding uniformity is a density map of `cells`, and a well focus summary is a mean over `fov_features`. Stitching and alignment artefacts are the exception, because they are measured between images and exist at no lower granularity. Cell to cell graphs are per cell, not per well. When a writer stores one, it belongs in `cells.obsp` (MAY, D7), and `well_features` MAY hold its summary statistics.

The table is `well_features` at the plate root, and a writer MAY omit it. It annotates `wells`, the shapes element with one rectangle per well in the `plate` coordinate system ([D5](design-decisions.md#d5-cycles-are-registered-to-the-dapi-channel-of-the-first-iss-cycle-at-each-timepoint), D7). `region_key` is `region` and `instance_key` is `well_id`, the integer index of `wells`.

| Slot | Column | Type | Requirement | Meaning |
| --- | --- | --- | --- | --- |
| `obs` | `region` | string | MUST | `wells` on every row |
| `obs` | `well_id` | integer | MUST | the `wells` index; the `instance_key` |
| `obs` | `well` | string | MUST | the well path, `A/1` |
| `obs` | `n_tiles`, `n_cells` | integer | MUST | tiles and cells counted in the well |
| `var` | index | string | MUST | metric names; not fixed by this specification |
| `X` | | numeric, float32 SHOULD | MUST | one value per well and metric, for example stitching residuals and seeding uniformity |

The `wells` shapes element has an integer index and the columns `well`, `row`, `column`, and `geometry` (D7). It is the only element that makes a well addressable by a spatialdata query, which is why a well table without a region was rejected (D7). The OPS data standard has no per-well artifact; its `aggregated_data.h5ad` is per perturbation, not per well.

## File format example

The tree shows the OME-NGFF 0.5 layout of `ops_plate.zarr` (D2) with the feature tables in place. The FOV table is expanded because it is the table that annotates the images. Inside the group, the layout is what spatialdata v0.8.0 writes for a table, namely the anndata Zarr encoding (existing behaviour, probe-verified). The group's location directly under the well follows D2; spatialdata v0.8.0 on its own would write it under a `tables/` folder.

```text
ops_plate.zarr/
├── zarr.json                        # ome.plate (0.5); sp-ops:spec, sp-ops:acquisitions, sp-ops:relationships
├── collection.json                  # (proposed) RFC-8 plate collection; holds the well_features node
├── library/                         # table, condition_table: barcode, perturbation_id, role, control_type
├── wells/                           # shapes, one rectangle per well (MAY); region of well_features
├── well_features/                   # table, feature_table, granularity well (MAY), 3 rows
└── A/
    └── 1/
        ├── zarr.json                # ome.well.images, 320 entries; sp-ops:relationships
        ├── collection.json          # (proposed) RFC-8 well collection; holds the cells and fov_features nodes
        ├── tiles/                   # shapes, 4 rows
        ├── footprints/              # shapes, 320 rows; region of images and fov_features
        ├── images/                  # table, condition_table, 320 rows, X (320, 0)
        ├── fov_features/            # table, feature_table, granularity image (MAY), 320 rows
        │   ├── zarr.json            # encoding-type anndata; spatialdata-encoding-type ngff:regions_table
        │   ├── X/                   # float32 (320, 12), one metric per column
        │   ├── obs/                 # _index, region, image_id, qc_pass
        │   ├── var/                 # _index holds the metric names
        │   ├── ...                  # obsm, obsp, varm, varp, layers, raw: empty anndata groups
        │   └── uns/
        │       ├── spatialdata_attrs/   # region, region_key, instance_key
        │       └── sp-ops/              # table_type, table_version, granularity
        ├── cells/                   # table, feature_table, granularity cell, 27488 rows x 1400 features
        ├── f0-t2-iss-r1/            # image, image_id 0 in images and fov_features
        ├── f0-t2-iss-r2/            # image, image_id 1
        ├── f0-t2-pheno/             # image, image_id 9
        │   └── labels/
        │       ├── nuclear_seg/
        │       └── cell_seg/        # one region of cells; rows with region A/1/f0/t2/cell_seg
        └── ...                      # remaining tiles, timepoints, cycles
```

Group attributes of `A/1/fov_features/zarr.json`. The seven attribute keys and their values are what spatialdata v0.8.0 writes (probe-verified). The region name is the hierarchical form; v0.8.0 writes `A-1-footprints`.

```json
{
  "zarr_format": 3,
  "node_type": "group",
  "attributes": {
    "encoding-type": "anndata",
    "encoding-version": "0.1.0",
    "spatialdata-encoding-type": "ngff:regions_table",
    "region": "A/1/footprints",
    "region_key": "region",
    "instance_key": "image_id",
    "version": "0.2"
  }
}
```

AnnData layout of `fov_features`. Shapes are those of the running example; metric values are illustrative.

```text
fov_features                 AnnData (320, 12)
obs    region                string    "A/1/footprints" on every row        region_key
       image_id              int64     footprint index of the camera image  instance_key
       qc_pass               bool      per-image verdict (SHOULD)
var    index                 string    focus_score, background_level, background_gradient, snr, ...
X      float32 (320, 12)               one metric per column
obsm   empty                            geometry lives in footprints, not here
uns    spatialdata_attrs     {"region": "A/1/footprints", "region_key": "region", "instance_key": "image_id"}
       sp-ops                {"table_type": "feature_table", "table_version": "1", "granularity": "image"}
```

First rows of `fov_features`, with `obs` on the left of the bar and `X` on the right. The `image_id` values match the `images` rows shown under D4: `0` is `f0/t2/iss/r1`, `1` is `f0/t2/iss/r2`, and `9` is `f0/t2/pheno`.

```text
image_id  region          qc_pass | focus_score  background_level  background_gradient  snr
0         A/1/footprints  true    | 0.91         112.0             0.03                 14.2
1         A/1/footprints  true    | 0.88         118.0             0.04                 13.5
9         A/1/footprints  false   | 0.42         240.0             0.21                  6.1
```

Building the table with spatialdata v0.8.0 names. The `uns["sp-ops"]` dictionary survives a write and read round trip because anndata stores `uns` unchanged (probe-verified).

```python
import anndata as ad
import numpy as np
import pandas as pd
from spatialdata.models import TableModel

obs = pd.DataFrame({
    "region": "A/1/footprints",
    "image_id": [0, 1, 9],
    "qc_pass": [True, True, False],
})
var = pd.DataFrame(index=["focus_score", "background_level", "background_gradient", "snr"])
X = np.array([[0.91, 112.0, 0.03, 14.2], [0.88, 118.0, 0.04, 13.5], [0.42, 240.0, 0.21, 6.1]], dtype="float32")
fov_features = TableModel.parse(
    ad.AnnData(X=X, obs=obs, var=var), region="A/1/footprints", region_key="region", instance_key="image_id"
)
fov_features.uns["sp-ops"] = {"table_type": "feature_table", "table_version": "1", "granularity": "image"}
```

## RFC-8 extension draft

:::{admonition} Status
:class: note
This section depends on OME-NGFF RFC-8 (collections and extensibility, status D1, an early draft). The node type `sp-ops:table` and the attribute key `sp-ops:table` are entries of the [extension key registry](design-decisions.md#extension-key-registry) in the design record. RFC-8 states that "Attribute keys within the `attributes` dictionary of nodes are an extension point". The prefix rule for such keys is on the [extension page](extension.md#the-extension-follows-rfc-8-prefixed-naming-with-the-prefix-sp-ops). Nothing below is readable by released software today; the `uns["sp-ops"]` dictionary is the in-memory mirror that works now (D8).
:::

Feature granularity is not a new key. It is the `granularity` field of the `sp-ops:table` attribute, which every table node MUST carry (D8). The three feature tables use the values `cell`, `image`, and `well`; the other two allowed values, `read` and `perturbation`, belong to the `reads` and `library` tables.

| Field of `sp-ops:table` | Type | Requirement | Values on feature tables |
| --- | --- | --- | --- |
| `type` | string | MUST | `feature_table` (one of the five ngio strings) |
| `tableVersion` | string | MUST | `"1"` |
| `granularity` | string | MUST | `cell`, `image`, or `well` |
| `region` | RFC-8 `Reference` | MAY | the annotated node, mirroring `spatialdata_attrs.region`; omitted when that value is a list, because a `Reference` names one node |

The three table nodes. The first two sit in the well document `A/1/collection.json`; the third sits in the plate document. Node ids follow D10, with `/` replaced by `-`.

```json
[
  {"type": "sp-ops:table", "id": "A-1-cells", "name": "cells",
   "path": {"type": "zarr", "path": "./cells"},
   "attributes": {"sp-ops:table": {"type": "feature_table", "tableVersion": "1", "granularity": "cell"}}},

  {"type": "sp-ops:table", "id": "A-1-fov_features", "name": "fov_features",
   "path": {"type": "zarr", "path": "./fov_features"},
   "attributes": {"sp-ops:table": {"type": "feature_table", "tableVersion": "1", "granularity": "image",
                                   "region": {"id": "A-1-footprints"}}}},

  {"type": "sp-ops:table", "id": "well_features", "name": "well_features",
   "path": {"type": "zarr", "path": "./well_features"},
   "attributes": {"sp-ops:table": {"type": "feature_table", "tableVersion": "1", "granularity": "well",
                                   "region": {"id": "wells"}}}}
]
```

The `cells` node carries no `region` because its `spatialdata_attrs.region` is the list of every `cell_seg` in the well. The list stays in `uns["spatialdata_attrs"]` inside the AnnData group, which is authoritative (this page follows the D3 example, which also omits it).

Compatibility with ngio (existing behaviour plus D8 rules). An ngio feature table declares `type`, `table_version`, `region.path`, `backend`, `index_key`, `index_type`, and `instance_key` in the table group attributes, and names a label image as its region. A writer MUST NOT emit a partial set of those keys unless it writes a full ngio `tables` group whose attributes carry the `tables` list (D8). When ngio's `type` is present it MUST agree with `sp-ops:table.type`.

## SpatialData view

:::{admonition} Status
:class: note
The repr below depends on the experimental hierarchical SpatialData branch, which is not released. Its format is described on the [hierarchy page](hierarchy.md#the-spatialdata-view-is-a-tree). spatialdata v0.8.0 prints the flat typed repr shown on the [Fields of view](fields-of-view.md#a-tile-is-a-name-prefix-in-the-spatialdata-view) page and requires the flattened names of D10.
:::

Plate root. The well table is a flat element at the root because its name has no `/`. Everything under a well is collapsed into the `A/` folder, so the two well-level feature tables appear as `1/cells` and `1/fov_features`. Only the rows and coordinate systems relevant to features are shown; a real repr prints every element and every coordinate system (about one hundred for the running example, D10). The coordinate systems block lists spatial elements only, because tables carry no transformation. The optional `plate` frame lists every element of every well next to `wells`, because each element composes one transformation per ancestor frame (D5).

```text
SpatialData object at /data/ops_plate.zarr
├── library: [Table] AnnData (4211, 0)
├── well_features: [Table] AnnData (3, 8)
├── wells: [Shapes] GeoDataFrame (3, 4)
└── A/ (1650 elements)
    ├── 1/cells: [Table] AnnData (27488, 1400)
    ├── 1/f0/t2/cell_bbox: [Shapes] GeoDataFrame (859, 1)
    ├── 1/f0/t2/cell_seg: [Labels2D] DataTree[yx] (2048, 2048), (1024, 1024), (512, 512)
    ├── 1/f0/t2/nuclear_seg: [Labels2D] DataTree[yx] (2048, 2048), (1024, 1024), (512, 512)
    ├── 1/f0/t2/pheno: [Image2D] DataTree[cyx] (5, 2048, 2048), (5, 1024, 1024), (5, 512, 512)
    ├── ...
    ├── 1/footprints: [Shapes] GeoDataFrame (320, 1)
    ├── 1/fov_features: [Table] AnnData (320, 12)
    ├── 1/images: [Table] AnnData (320, 0)
    ├── 1/reads: [Table] AnnData (1203456, 0)
    ├── 1/tiles: [Shapes] GeoDataFrame (4, 4)
    ├── 2/cells: [Table] AnnData (27488, 1400)
    ├── ...
    └── 3/tiles: [Shapes] GeoDataFrame (4, 4)
with coordinate systems:
    ▸ 'A/1', with elements:
        A/1/f0/t2/cell_bbox, A/1/f0/t2/cell_seg, A/1/f0/t2/nuclear_seg, A/1/f0/t2/pheno, ..., A/1/footprints, A/1/tiles
    ▸ 'A/1/f0/t2', with elements:
        A/1/f0/t2/cell_bbox, A/1/f0/t2/cell_seg, A/1/f0/t2/nuclear_seg, A/1/f0/t2/pheno, ...
    ▸ ...
    ▸ 'plate', with elements:
        A/1/f0/t2/cell_bbox, A/1/f0/t2/cell_seg, A/1/f0/t2/nuclear_seg, A/1/f0/t2/pheno, ..., A/1/footprints, A/1/tiles, ..., wells
```

Well sub-view, `sdata["A/1"]`. The two well-level feature tables are now flat, and each tile is a folder holding the label images that `cells` annotates. The FOV table has one row per image inside those tile folders. Per-tile counts are those of the running example; only the first timepoint of the first tile is expanded.

```text
SpatialData object at /data/ops_plate.zarr/A/1
├── cells: [Table] AnnData (27488, 1400)
├── footprints: [Shapes] GeoDataFrame (320, 1)
├── fov_features: [Table] AnnData (320, 12)
├── images: [Table] AnnData (320, 0)
├── reads: [Table] AnnData (1203456, 0)
├── tiles: [Shapes] GeoDataFrame (4, 4)
├── f0/ (136 elements)
│   ├── t2/cell_bbox: [Shapes] GeoDataFrame (859, 1)
│   ├── t2/cell_seg: [Labels2D] DataTree[yx] (2048, 2048), (1024, 1024), (512, 512)
│   ├── t2/iss/r1: [Image2D] DataTree[cyx] (5, 2048, 2048), (5, 1024, 1024), (5, 512, 512)
│   ├── t2/nuclear_seg: [Labels2D] DataTree[yx] (2048, 2048), (1024, 1024), (512, 512)
│   ├── t2/pheno: [Image2D] DataTree[cyx] (5, 2048, 2048), (5, 1024, 1024), (5, 512, 512)
│   └── ...
├── f1/ (136 elements)
├── f2/ (136 elements)
└── f3/ (136 elements)
with coordinate systems:
    ▸ 'A/1', with elements:
        f0/t2/cell_bbox, f0/t2/cell_seg, f0/t2/iss/r1, f0/t2/nuclear_seg, f0/t2/pheno, ..., footprints, tiles
    ▸ 'A/1/f0/t2', with elements:
        f0/t2/cell_bbox, f0/t2/cell_seg, f0/t2/iss/r1, f0/t2/nuclear_seg, f0/t2/pheno, ...
    ▸ ...
    ▸ 'plate', with elements:
        f0/t2/cell_bbox, f0/t2/cell_seg, f0/t2/iss/r1, f0/t2/nuclear_seg, f0/t2/pheno, ..., footprints, tiles
```

Row counts are illustrative except the 859 cells per frame and the 4211 library rows; the 4 tiles, the 320 images, and the 27488 cells per well follow from the illustrative 2 by 2 grid of the [running example](design-decisions.md#running-example). Every element under a `t` collection carries one transformation per ancestor frame ([D5](design-decisions.md#d5-cycles-are-registered-to-the-dapi-channel-of-the-first-iss-cycle-at-each-timepoint)), so the `'A/1'` and `'plate'` listings hold the same elements of the well, and a `t` frame lists only the elements of that (tile, `t`).

## Example: join cells to their labels and filter by FOV quality control

The example keeps the cells of frames whose every camera image is sharp. It uses two spatialdata v0.8.0 functions, `filter_by_table_query` and `join_spatialelement_table`. Predicates are `annsel` expressions. spatialdata v0.8.0 imports the `Predicates` type from `annsel.core.typing` for `obs_expr` and `x_expr` (probe-verified).

Two behaviours of v0.8.0 shape the code (probe-verified). First, `filter_by_table_query` with `x_expr` on the FOV table returns a SpatialData whose `footprints` element keeps only the passing rectangles. Their index is therefore the set of passing `image_id` values. Second, a join against a labels element returns no table when `how="inner"`, so every labels join on this page uses `how="left"`. With `how="left"` it returns the rows whose `label` values occur in that labels element, and it rewrites `spatialdata_attrs.region` to that single element (D7).

:::{admonition} Status
:class: note
Every element name containing `/` depends on hierarchical SpatialData, which is not released. In spatialdata v0.8.0 the same element is spelled with `-`, for example `A-1-fov_features` (D10). The `sdata[...]` lookups on such names carry a `# proposed API` comment.
:::

```python
import annsel as an
from spatialdata import filter_by_table_query, join_spatialelement_table

# 1. Sharp camera images. fov_features annotates footprints, one row per acquisition image.
sharp = filter_by_table_query(
    sdata, table_name="A/1/fov_features", x_expr=an.col("focus_score") > 0.6, how="inner"
)
sharp_ids = set(sharp["A/1/footprints"].index)                                   # proposed API

# 2. Frames (tile, t) in which every image is sharp, via the images table (same image_id).
images = sdata["A/1/images"].obs                                                 # proposed API
frame_ok = images.groupby(["tile", "t"])["image_id"].agg(lambda s: s.isin(sharp_ids).all())
good_frames = frame_ok[frame_ok].index.tolist()                                  # [(0, 2), (0, 3), ...]

# 3. Cell features of one good frame, joined to the label image they were measured on.
tile, t = good_frames[0]
tile_name = sdata["A/1/tiles"].loc[tile, "tile"]                                 # 'f0'; proposed API
labels, cells_t = join_spatialelement_table(
    sdata=sdata, spatial_element_names=f"A/1/{tile_name}/t{t}/cell_seg", table_name="A/1/cells", how="left"
)
cells_t.obs[["cell_uid", "label", "perturbation_id", "qc_pass"]]
cells_t.to_df()["cell_AreaShape_Area"]

# 4. The same frame as a SpatialData subset: the labels element plus the matching table rows.
frame = filter_by_table_query(
    sdata,
    table_name="A/1/cells",
    element_names=[f"A/1/{tile_name}/t{t}/cell_seg"],
    obs_expr=(an.col("tile") == tile) & (an.col("t") == t),
    how="left",
)
list(frame.labels), frame["A/1/cells"].n_obs                                     # ['A/1/f0/t2/cell_seg'], 859; proposed API
```

Exporting the OPS single-cell table is a concatenation over wells, shown under D7 of the design record. The relationships that link `cells` to `library` and to the read-level elements are specified on the [Joinable components](joinable-components.md) page. The annotation of `cells` by `cell_seg` is not repeated there, because `spatialdata_attrs` already declares it (D9).

## Sources

- [OME-NGFF RFC-8: Collections and Extensibility](https://ngff.openmicroscopy.org/rfc/8/index.html#high-content-screening-hcs-metadata): node `attributes` as an extension point, prefixed identifiers, `Reference` objects, HCS attributes; status D1.
- [OME-NGFF 0.5](https://ngff.openmicroscopy.org/0.5/) and its [HCS layout](https://ngff.openmicroscopy.org/0.5/#hcs-layout): the released version the OPS data standard requires and the layout of the directory tree.
- [OME-NGFF dev specification, plate metadata](https://ngff.openmicroscopy.org/specifications/dev/index.html#plate-metadata) and [well metadata](https://ngff.openmicroscopy.org/specifications/dev/index.html#well-metadata): the plate and well keys, which 0.5 shares.
- [scallops and Biohub OPS layout (HackMD)](https://hackmd.io/@D9GB-ZDcTQyFd7U5aMmk5g/r18soYBuzx): `features/{cell,cytosol,nuclei}/A1.parquet` CellProfiler features, `-objects.parquet` bounding boxes, `merge/A1.parquet` perturbation calls, `segment.zarr` labels.
- Chan Zuckerberg Initiative (CZI) OPS data standard v0.1.0 (draft) and the conformance check of a public Biohub submission: `cell_data.parquet` (`cell_uid`, `perturbation_id`), `perturbation_library.csv`, `feature_definitions.csv`, the artifact list, and the audited store facts. No public URL appears in the source material.
- [ngio table specifications](https://biovisioncenter.github.io/ngio/stable/table_specs/overview/): `feature_table` attributes, `region.path` to a label image, `instance_key`, the `measurement`, `categorical`, `metadata` vocabulary.
- [spatialdata documentation](https://spatialdata.scverse.org/en/stable/): v0.8.0 `TableModel.parse`, `join_spatialelement_table`, `filter_by_table_query`; on-disk table attributes and join behaviour probe-verified against v0.8.0.
- [spatialdata tables tutorial](https://spatialdata.scverse.org/en/stable/tutorials/notebooks/notebooks/examples/tables.html): the `region`, `region_key`, `instance_key` annotation model.
- [annsel documentation](https://annsel.readthedocs.io/en/latest/): the package whose `Predicates` type spatialdata imports for `obs_expr` and `x_expr` (`from annsel.core.typing import Predicates`); `an.col(...)` expressions probe-verified against v0.8.0.
- [Hierarchical SpatialData slides](https://raw.githubusercontent.com/LucaMarconato/spatialdata/refs/heads/vibecoded-experiment/hierarchical-spatialdata/slides-hierarchical-spatialdata.html): `/` in element names, sub-views, the tree repr and its `_gen_repr` format.
- [anndata documentation](https://anndata.readthedocs.io): `obs`, `var`, `X`, `obsm`, `obsp`, `uns`, `to_df`, and the Zarr encoding of an AnnData object.
- [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119.txt): the meaning of MUST, SHOULD, and MAY.
