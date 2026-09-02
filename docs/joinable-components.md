# Joinable components

This page specifies how the tables, points, and shapes of an optical pooled screening (OPS) store join to each other and to images and labels. It fixes the roles a table can play and the `sp-ops:relationships` edge list that records joins and spatial joins. It also gives the schema of three pipeline products, namely reads with quality control (QC) columns, segmentation bounding boxes, and CellProfiler features. Element names, table names, and columns follow the [running example](design-decisions.md#running-example) of the design record. Statements fall into the three status categories defined on the [overview page](overview.md#every-statement-is-normative-existing-behaviour-or-a-proposal). MUST, SHOULD, and MAY are requirements in the sense of request for comments (RFC) 2119. Existing behaviour here is the Open Microscopy Environment Next-Generation File Format (OME-NGFF) 0.5, spatialdata v0.8.0, and ngio.

## One table type, several roles

spatialdata has one table model. `TableModel.parse` takes an AnnData and records `region`, `region_key`, and `instance_key` in `adata.uns["spatialdata_attrs"]` (v0.8.0). ngio names five table types instead: `generic_table`, `roi_table`, `masking_roi_table`, `feature_table`, and `condition_table`. This specification keeps the single spatialdata model and reuses the ngio names as a role label. Every table MUST declare its role in `adata.uns["sp-ops"]["table_type"]` in memory and in the `sp-ops:table.type` node attribute on disk (proposed). The rule and the allowed values are fixed in [D8](design-decisions.md#d8-table-types-use-the-ngio-vocabulary-under-one-namespaced-dictionary).

Three roles occur in an OPS store.

| Role | ngio type | `sp-ops` `table_type` | Running example | How the link is expressed |
| --- | --- | --- | --- | --- |
| Region table that annotates an image or a label image with boxes | `roi_table`, `masking_roi_table` | none; the geometry is a shapes element | `tiles`, `footprints`, `cell_bbox` | rectangles in GeoParquet; centroids in the well frame MAY be copied to `obsm["spatial"]` |
| Feature table that annotates instances of labels or shapes | `feature_table` | `feature_table` | `cells`, `fov_features`, `well_features` | `spatialdata_attrs` (`region`, `region_key`, `instance_key`) |
| Table with foreign keys that merges with other tables or points | `generic_table`, `condition_table` | `generic_table`, `condition_table` | `reads`, `library` | `join` edges in `sp-ops:relationships` |

`images` is a `condition_table` that annotates `footprints` through `spatialdata_attrs` and takes part in no edge (D4).

### Region tables are redundant with shapes

An ngio region of interest (ROI) table stores each region as number columns. The required columns are `x_micrometer`, `y_micrometer`, `z_micrometer`, `len_x_micrometer`, `len_y_micrometer`, and `len_z_micrometer`. A masking ROI table adds an integer `label` that "corresponds to a specific label in the label image". The same information is a rectangle in a spatialdata shapes element, which `bounding_box_query` and `polygon_query` can search. This specification therefore stores regions as shapes and writes no ROI table. `tiles` and `footprints` describe images, and `cell_bbox` describes labels. A writer MAY derive an ngio `roi_table` or `masking_roi_table` from these elements for Fractal tooling; the shapes element stays authoritative. Cell centroids MAY be copied to `cells.obsm["spatial"]`, expressed in the well coordinate system `A/1`, for tools that expect them there. The labels and `cell_bbox` remain the authoritative geometry ([D7](design-decisions.md#d7-cell-features-annotate-the-labels-fov-features-annotate-the-footprints-well-features-annotate-the-wells)).

### Feature tables annotate instances

A feature table has one row per instance of a labels or shapes element. `cells` annotates every `cell_seg` labels element of a well with `instance_key` `label`, the pixel value. `fov_features` annotates the `footprints` shapes with `instance_key` `image_id`, and `well_features` annotates the `wells` shapes with `well_id`. The `var` axis carries two feature annotations. `compartment` is one of `cell`, `cytosol`, `nuclei`. `feature_type` is one of `measurement`, `categorical`, `metadata`. ngio defines the same three feature types so that "downstream tools can select subsets of features without guessing from dtypes". An ngio feature table names a label image as its `region`. Annotating a shapes element is a spatialdata capability and a widening of the ngio type (D8).

### Foreign-key tables merge

A table with a foreign key has no region. `reads` holds one row per sequenced read. It joins `bases` through the uint64 `read` column of the scallops pipeline, and `spots/peaks` through the same column, which this specification asks a depositor to add (SHOULD, D11). `library` holds one row per single guide RNA (sgRNA) and is reached from `reads` and `cells` through `barcode`. `images` is a condition table that annotates `footprints`; its `element` column names one image per row ([D4](design-decisions.md#d4-timepoints-and-cycles-are-separate-elements-only-aligned-channels-are-stacked)). spatialdata v0.8.0 has no table-to-table join operation. These joins are therefore recorded as edges (next section) and executed with pandas today.

## Elements are linked by joins or spatial joins

:::{admonition} Status
:class: note
The edge list depends on the element relationships proposal. The fields `from`, `to`, `method`, `params`, `how`, `left_on`, `right_on`, `predicate`, and `distance` come from the Padua hackathon prototype, `spatialdata_elements_graph`. The fields `target_coordinate_system`, `result_column`, `status`, `cardinality`, and `description` are additions of this specification (D9). The join vocabulary `index`, `value`, and column name comes from the Venice hackathon prototype, `element_relationships` with `join_strategy`, plus `sjoin_suggestions`. The `name` entry is an addition of this specification. Neither prototype is released, and the Venice README marks its code as unverified. `sdata.attrs` exists in spatialdata v0.8.0 and is where both prototypes store their graph, so the in-memory copy needs nothing unreleased. Storage on collection nodes depends on RFC-8 (status D1).
:::

`sp-ops:relationships` is an object with two fields, `version` (the string `"0.1"`) and `edges` (an array). Every edge has the shape defined in [D9](design-decisions.md#d9-relationships-are-an-edge-list-stored-on-the-lowest-node-that-contains-both-endpoints).

| Field | Type | Requirement | Values |
| --- | --- | --- | --- |
| `from` | string | MUST | element name relative to the node carrying the attribute |
| `to` | string | MUST | element name, same convention; one element, never an array |
| `method` | string | MUST | `join` (by key) or `sjoin` (spatial) |
| `params.how` | string | MUST | `left`, `inner`, `right` |
| `params.left_on` | array of strings | MUST for `join` | each entry is `index`, `value` (label pixel value), or a column name on `from` (Venice vocabulary), or `name` (the element's own name; added by this specification) |
| `params.right_on` | array of strings | MUST for `join` | same vocabulary on `to`; same length as `left_on` |
| `params.predicate` | string | MUST for `sjoin` | `within`, `intersects`, `contains`, `dwithin` |
| `params.distance` | number | MUST when predicate is `dwithin` | in units of `target_coordinate_system` |
| `params.target_coordinate_system` | string | MUST for `sjoin` | the frame in which the predicate is evaluated |
| `params.result_column` | string | SHOULD for `sjoin` | column on `from` that stores the matched `to` instance once computed |
| `status` | string | MUST | `computed` (the result is stored) or `suggested` (not yet computed) |
| `cardinality` | string | SHOULD | `1:1`, `1:n`, `n:1`, `n:m`, `unknown` |
| `description` | string | MAY | free text |

### A join matches keys and an sjoin matches geometry

A `join` edge matches rows where the `left_on` values on `from` equal the `right_on` values on `to`. An `sjoin` edge matches by geometry, evaluated in `target_coordinate_system`. When `to` is a labels element, an `sjoin` means a pixel lookup of the label value at each `from` geometry. Such an edge admits only `within`. An `sjoin` between shapes or points elements is a geopandas spatial join. Annotations that `spatialdata_attrs` already expresses MUST NOT be repeated as edges; a reader adds them to the in-memory graph. The `images` table names its images through the `element` column, which a validator checks by name (D4), so no edge is needed there either. `status: "suggested"` keeps the Venice distinction between a computed join and a hint that two elements can be joined.

### Storage

Each edge MUST be stored on the lowest node whose subtree contains both endpoints, with names relative to that node. A store SHOULD carry `sp-ops:relationships` at the plate root; the root list holds every edge that reaches `library`. Edges between a well table and a (tile, `t`) element sit on the well. Edges inside one (tile, `t`) sit on the `t` collection of the RFC-8 sidecar (proposed). In the OME-NGFF 0.5 layout the plate and well Zarr groups carry the attribute as a sibling of `ome`. When no sidecar is written, the well group carries the `t`-level edges with well-relative names (D9). In memory the reader merges the lists into `sdata.attrs["sp-ops"]["relationships"]` with names relative to the object's root.

### Example

Plate root, attribute value in `ops_plate.zarr/zarr.json`. Wells `A/2` and `A/3` repeat the two edges.

```json
"sp-ops:relationships": {
  "version": "0.1",
  "edges": [
    {"from": "A/1/cells", "to": "library", "method": "join",
     "params": {"how": "left", "left_on": ["barcode"], "right_on": ["barcode"]},
     "status": "computed", "cardinality": "n:1",
     "description": "perturbation call per cell; barcode is unique in library"},
    {"from": "A/1/reads", "to": "library", "method": "join",
     "params": {"how": "left", "left_on": ["barcode"], "right_on": ["barcode"]},
     "status": "computed", "cardinality": "n:1"}
    // A/2/cells, A/2/reads, A/3/cells, A/3/reads: same two edges
  ]
}
```

Well `A/1`, attribute value in `ops_plate.zarr/A/1/zarr.json`. The real well has one pair of edges per (tile, `t`) frame; tile `f0` at `t2` is shown.

```json
"sp-ops:relationships": {
  "version": "0.1",
  "edges": [
    {"from": "f0/t2/bases", "to": "reads", "method": "join",
     "params": {"how": "inner", "left_on": ["read"], "right_on": ["read"]},
     "status": "computed", "cardinality": "n:1",
     "description": "one base call per cycle joins to one read"},
    {"from": "f0/t2/spots/peaks", "to": "reads", "method": "join",
     "params": {"how": "left", "left_on": ["read"], "right_on": ["read"]},
     "status": "computed", "cardinality": "1:1"}
    // f0/t3 ... f3/t10: same two edges per frame
  ]
}
```

The `t2` collection of tile `f0` (proposed; lives in `A/1/collection.json`). Names are relative to `A/1/f0/t2`.

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

## Reads, peaks, boxes, features, and the library are separate elements

The draft lists three independent components. An OPS store ingests them as separate elements. The table adds the three elements they join to, namely the base calls, the spot detection peaks, and the perturbation library. It gives the source, the element, the model, and the join keys, following [D11](design-decisions.md#d11-bases-are-points-bounding-boxes-are-shapes-reads-and-features-are-tables). Every join in the table MUST appear as an edge in `sp-ops:relationships`, except the `cells` to `cell_seg` annotation, which `spatialdata_attrs` already declares.

| Draft component | scallops source | Element | Model and role | Join keys |
| --- | --- | --- | --- | --- |
| barcodes parquet with QC | `reads/reads/A1.parquet` | `A/1/reads` | table, `generic_table`, granularity `read` | `read` to `bases` and `spots/peaks`; `barcode` to `library` |
| base calls with locations | `reads/bases/A1.parquet` | `A/1/f0/t2/bases` | points | `read`; `cell_label` from the spatial join |
| spot detection peaks | `spot-detect.zarr/points/A1-peaks.parquet` | `A/1/f0/t2/spots/peaks` | points | `read` (SHOULD); `cell_label` |
| segmentation bounding boxes | `features/cell/A1-objects.parquet` | `A/1/f0/t2/cell_bbox` | shapes | index equals the `cell_seg` label value |
| CellProfiler features | `features/{cell,cytosol,nuclei}/A1.parquet` and `merge/A1.parquet` | `A/1/cells` | table, `feature_table`, granularity `cell` | `label` with `region`; `barcode` to `library` |
| perturbation library | `perturbation_library.csv` (OPS standard) | `library` | table, `condition_table`, granularity `perturbation` | `barcode` (unique, edge target); `perturbation_id` groups sgRNAs and is copied, not joined |

### Barcodes are a table and their locations are points

The draft's "barcodes parquet (with QC)" corresponds to two scallops files. `reads/reads/A1.parquet` "contains the string called sequence" and has no location. `reads/bases/A1.parquet` "contains the locations", one per cycle. The two join through the `read` column, a uint64. A read has no single location, so `reads` is a table. The per-cycle calls are points in the registered frame. A depositor with one location per read MAY store it in `spots/peaks`. `reads` stays the table that carries the sequence and QC.

`spots/peaks` is a points element with `x` and `y` in the registered frame. It SHOULD carry `read`, one peak per read shared across cycles, and SHOULD carry `cell_label` once the spatial join is computed (D11). In the running example the `spots/peaks` to `cell_seg` edge is `suggested`, not `computed` (D9), so the element carries `x`, `y`, and `read`, three columns.

`reads` columns (`obs`). The table has no `var`, and `X` has shape `(n_reads, 0)`.

| Column | Type | Requirement | Meaning |
| --- | --- | --- | --- |
| `read` | uint64, unique | MUST | read identifier shared with `bases` and `spots/peaks` |
| `tile` | integer | MUST | equals the `tiles` index |
| `t` | integer | MUST | fixation timepoint (folder label from the scallops layout) |
| `sequence` | string | SHOULD | called bases across cycles |
| `barcode` | string, nullable | SHOULD | matched `library` barcode; null when unmatched |
| `perturbation_id` | string, nullable | SHOULD | from `library` through `barcode` |
| `quality` | number | SHOULD | call quality |
| `qc_pass` | boolean | SHOULD; MUST when any read-level QC was applied | the read passed QC |

`bases` columns. Coordinates are in the registered frame `A/1/f0/t2`, in micrometres, with an identity transformation.

| Column | Type | Requirement | Meaning |
| --- | --- | --- | --- |
| `x`, `y` | float | MUST | position of the call |
| `read` | uint64 | MUST | join to `reads` |
| `r` | integer | MUST | in situ sequencing (ISS) cycle |
| `base` | string | MUST | called base, one of `A`, `C`, `G`, `T` |
| one column per base channel | float | SHOULD | intensity behind the call |
| `cell_label` | integer, `0` for unassigned | SHOULD once the spatial join is computed | label of the containing cell |

The running example carries `x`, `y`, `read`, `r`, `base`, and `cell_label`, six columns in that order. It omits the intensity columns because the sources do not name them. `cell_label` is present because the `bases` to `cell_seg` edge is `computed`.

`reads` enters the graph through three `join` edges. `bases` and `spots/peaks` point to `reads` on `read`, and `reads` points to `library` on `barcode`. `bases` also carries an `sjoin` edge to `cell_seg` (predicate `within`, result column `cell_label`). That edge is how a read reaches its cell.

### Bounding boxes are shapes indexed by label value

`features/cell/A1-objects.parquet` holds the bounding boxes of the cells. It becomes the shapes element `cell_bbox`, one per (tile, `t`). On disk, spatialdata v0.8.0 writes a shapes element as `shapes.parquet` inside its Zarr group, readable with `geopandas.read_parquet` (probe-verified in [D3](design-decisions.md#d3-a-tile-is-a-collection-of-per-timepoint-collections-and-the-layout-is-a-shapes-element)).

| Column | Type | Requirement | Meaning |
| --- | --- | --- | --- |
| index | integer, unique | MUST | equals the `cell_seg` label value |
| `geometry` | Polygon, axis-aligned rectangle | MUST | bounding box in `A/1/f0/t2`, micrometres |
| other columns of `A1-objects.parquet` | any | MAY | carried through unchanged (D11) |

`cell_bbox` enters the graph with one `join` edge to `cell_seg`, `left_on` `["index"]` and `right_on` `["value"]`, cardinality `1:1`. When `-objects.parquet` is absent, the boxes MAY be computed from the labels with spatialdata `to_polygons`. A `nuclei_bbox` element from `nuclei/A1-objects.parquet` MAY be added with the same schema.

### CellProfiler features are a feature table on the labels

`features/cell/A1.parquet`, `features/cytosol/A1.parquet`, and `features/nuclei/A1.parquet` hold one row per object and one column per CellProfiler feature. `merge/A1.parquet` "contains perturbation information and which guides it comes from". Together they become the `cells` table, one per well, which annotates every `cell_seg` element in the well.

`cells.obs` columns.

| Column | Type | Requirement | Meaning |
| --- | --- | --- | --- |
| `region` | string | MUST | `region_key`; the labels element, `A/1/f0/t2/cell_seg` |
| `label` | integer | MUST | `instance_key`; the label pixel value |
| `cell_uid` | string, unique | MUST | SHOULD have the form `<row><col>_<tile>_t<t>_<label>`, for example `A1_f0_t2_812` |
| `tile` | integer | MUST | equals the `tiles` index |
| `t` | integer | MUST | fixation timepoint (folder label from the scallops layout) |
| `perturbation_id` | string, nullable | SHOULD once assigned | from `library` |
| `barcode` | string, nullable | SHOULD once assigned | the sgRNA barcode behind the call |
| `n_reads` | integer | SHOULD once assigned | reads supporting the call |
| `qc_pass` | boolean | SHOULD once assigned | the cell passed QC |

`cells.var` columns. `X` holds the feature values.

| Column | Type | Requirement | Meaning |
| --- | --- | --- | --- |
| index | string | MUST | CellProfiler feature name, for example `cell_AreaShape_Area` |
| `compartment` | `cell`, `cytosol`, `nuclei` | MUST | the scallops feature folder the column came from |
| `feature_type` | `measurement`, `categorical`, `metadata` | MUST | the ngio feature table vocabulary |

The draft notes that some features serve QC and others serve downstream analysis. The split is an analysis choice, so this specification does not partition the columns. `feature_type` in `var` lets a tool select measurement columns, and `qc_pass` in `obs` records the per-cell verdict.

`cells` enters the graph in two ways. The annotation of `cell_seg` is expressed by `spatialdata_attrs` and is not an edge. The perturbation call is a `join` edge from `cells` to `library` on `barcode`, stored at the plate root. The `cell_data.parquet` of the OPS data standard is `cells.obs` joined with `cells.X` and concatenated over wells, with `cell_uid` and `perturbation_id` carried unchanged (D7).

### The library is the shared foreign-key target

`library` sits at the plate root. Its `obs` MUST carry `barcode`, `perturbation_id`, `role`, and `control_type`, the OPS data standard fields named in D11. Other columns of `perturbation_library.csv` MAY be carried through unchanged (D11). The standard describes `barcode` as the "per-sgRNA primary key (unique within aggregation)". It describes `perturbation_id` as the "stable join key (submitter-defined)" shared by all sgRNAs that target the same gene. `role` is `targeting` or `control`. `control_type` MUST be present and be `non-targeting` or `intergenic` when `role` is `control`, and MUST NOT be present otherwise (OPS rules V-10 and V-11). A validator MUST check that every non-null `perturbation_id` in `cells` (D7) and in `reads` (D11) exists in `library`. The `reads` value is copied from `library` through `barcode`. The audited submission fails the check on retired gene symbols such as `AARS` for `AARS1` (D7).

## File format example

The scallops sources and where each lands in the store. Only well `A/1`, tile `f0`, and `t2` (a folder label from the scallops layout) are expanded. The store follows the OME-NGFF 0.5 layout with flattened names ([D10](design-decisions.md#d10-element-names-are-the-on-disk-paths-and-a-hyphen-flattens-them-for-v080)).

```text
ops/                                     # scallops outputs (source)
├── features/cell/A1-objects.parquet     # bounding boxes    -> A/1/f0/t2/cell_bbox (shapes)
├── features/cell/A1.parquet             # CellProfiler      -> A/1/cells (table)
└── reads/reads/A1.parquet               # reads with QC     -> A/1/reads (table)

ops_plate.zarr/
├── zarr.json                            # ome.plate; sp-ops:spec; sp-ops:acquisitions; sp-ops:relationships
├── collection.json                      # (proposed) RFC-8 plate collection; sp-ops:table on library
├── library/                             # table, condition_table
│   ├── zarr.json
│   ├── obs/                             # barcode, perturbation_id, role, control_type
│   ├── X/                               # shape (4211, 0)
│   └── uns/
│       └── sp-ops/                      # table_type, table_version, granularity; no spatialdata_attrs (no region)
└── A/
    └── 1/
        ├── zarr.json                    # ome.well.images; sp-ops:relationships (edges to reads)
        ├── collection.json              # (proposed) tile and t collections; t-level edges
        ├── cells/                       # table, feature_table
        │   ├── obs/                     # region, label, cell_uid, tile, t, perturbation_id, barcode, n_reads, qc_pass
        │   ├── var/                     # compartment, feature_type
        │   ├── X/                       # shape (27488, 1400)
        │   └── uns/                     # sp-ops, spatialdata_attrs (region: 32 cell_seg elements)
        ├── reads/                       # table, generic_table
        │   ├── obs/                     # read, tile, t, sequence, barcode, perturbation_id, quality, qc_pass
        │   ├── X/                       # shape (n_reads, 0)
        │   └── uns/                     # sp-ops only; no spatialdata_attrs (no region)
        ├── f0-t2-cell_bbox/             # shapes
        │   ├── zarr.json                # encoding-type ngff:shapes, axes, coordinateTransformations, spatialdata_attrs
        │   └── shapes.parquet           # 859 rectangles, index = label value
        ├── f0-t2-bases/                 # points: x, y, read, r, base, cell_label
        ├── f0-t2-spots-peaks/           # points: x, y, read
        └── f0-t2-pheno/
            └── labels/
                └── cell_seg/            # labels, int32; annotated by cells, joined by cell_bbox and bases
```

The plate root `zarr.json`. Core high-content screening (HCS) metadata is under `ome`; the extension keys are siblings. The full `ome.plate` and `sp-ops:acquisitions` values are on the [hierarchy page](hierarchy.md).

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
        "acquisitions": [ /* 80 entries, see the hierarchy page */ ]
      }
    },
    "sp-ops:spec": {"version": "0.1.0-draft", "profile": "tiled"},
    "sp-ops:acquisitions": [ /* 80 entries, see the hierarchy page */ ],
    "sp-ops:relationships": {
      "version": "0.1",
      "edges": [
        {"from": "A/1/cells", "to": "library", "method": "join",
         "params": {"how": "left", "left_on": ["barcode"], "right_on": ["barcode"]},
         "status": "computed", "cardinality": "n:1"},
        {"from": "A/1/reads", "to": "library", "method": "join",
         "params": {"how": "left", "left_on": ["barcode"], "right_on": ["barcode"]},
         "status": "computed", "cardinality": "n:1"},
        {"from": "A/2/cells", "to": "library", "method": "join",
         "params": {"how": "left", "left_on": ["barcode"], "right_on": ["barcode"]},
         "status": "computed", "cardinality": "n:1"},
        {"from": "A/2/reads", "to": "library", "method": "join",
         "params": {"how": "left", "left_on": ["barcode"], "right_on": ["barcode"]},
         "status": "computed", "cardinality": "n:1"},
        {"from": "A/3/cells", "to": "library", "method": "join",
         "params": {"how": "left", "left_on": ["barcode"], "right_on": ["barcode"]},
         "status": "computed", "cardinality": "n:1"},
        {"from": "A/3/reads", "to": "library", "method": "join",
         "params": {"how": "left", "left_on": ["barcode"], "right_on": ["barcode"]},
         "status": "computed", "cardinality": "n:1"}
      ]
    }
  }
}
```

### Metadata of the region-less tables, the boxes, and the base calls

`reads` and `library` annotate no element. spatialdata v0.8.0 `TableModel.parse` takes `region`, `region_key`, and `instance_key` with default `None` (verified signature). A table parsed without them carries none of the three keys. The spatialdata source guards for the missing dictionary. `SpatialData` reads the region only `if TableModel.ATTRS_KEY in table.uns`, and the annotation setter initialises `table.uns["spatialdata_attrs"]` when `uns.get` returns `None`. Both are existing behaviour, read in the `spatialdata.py` source on record. `uns["spatialdata_attrs"]` is therefore absent or empty for a region-less table, and a validator SHOULD accept both forms. The hierarchical layout adds `element_type` to `spatialdata_attrs` for every element (proposed), so in that layout the dictionary is present and holds only that key. The `sp-ops` dictionary of D8 is present in every case.

```python
sdata["A/1/reads"].uns                                        # proposed API for the name
# {'sp-ops': {'table_type': 'generic_table', 'table_version': '1', 'granularity': 'read'}}
sdata["library"].uns
# {'sp-ops': {'table_type': 'condition_table', 'table_version': '1', 'granularity': 'perturbation'}}
sdata["A/1/cells"].uns["spatialdata_attrs"]                   # for contrast: a feature table
# {'region': ['A/1/f0/t2/cell_seg', ..., 'A/1/f3/t10/cell_seg'], 'region_key': 'region', 'instance_key': 'label'}
```

On disk anndata writes each `uns` key as a Zarr node, so `reads/uns/` holds `sp-ops/` and no `spatialdata_attrs/` in v0.8.0 (existing behaviour). The RFC-8 node carries `sp-ops:table` without `region`, as the `A-1-reads` and `library` nodes in the next section show.

`cell_bbox` is a shapes group. The `zarr.json` below follows the v0.8.0 shapes group probe-verified for `tiles` on the [fields of view page](fields-of-view.md#file-format-example) (existing behaviour). The group attributes are `encoding-type`, `axes`, `coordinateTransformations`, and `spatialdata_attrs`, with `shapes.parquet` beside the `zarr.json`. The transformation is the identity into the registered frame `A/1/f0/t2` (D5), with `input` and `output` keyed by `name`. spatialdata writes the axes as `x, y` and the placeholder unit `"unit"`; D5 fixes the unit as micrometre. The reader adds the `A/1` and `plate` entries in memory when it composes the scene edges (D5). The parquet index is the `cell_seg` label value.

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
          "name": "A/1/f0/t2",
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

`bases` is a points group written by spatialdata's `PointsModel` (existing behaviour). Its group attributes were not probed for this record, so this page gives the in-memory form; the shapes group above is the probed reference for element metadata. The element carries the identity into `A/1/f0/t2` (D5) and the six columns of the running example. `set_transformation`, `get_transformation`, and `Identity` are v0.8.0 names; coordinate-system names containing `/` are unverified in v0.8.0 (D10).

```python
from spatialdata.transformations import Identity, get_transformation, set_transformation

bases = sdata["A/1/f0/t2/bases"]                                            # proposed API for the name
set_transformation(bases, Identity(), to_coordinate_system="A/1/f0/t2")    # "/" in the coordinate-system name is unverified in v0.8.0 (D10)
list(get_transformation(bases, get_all=True))
# ['A/1/f0/t2']
bases.columns.tolist()
# ['x', 'y', 'read', 'r', 'base', 'cell_label']
```

## RFC-8 extension draft

:::{admonition} Status
:class: note
RFC-8 (collections and extensibility) has status D1, an early draft. Everything in this section is a proposal of this specification that depends on it. The prefix rule, and what a reader does with a prefix it does not know, are on the [extension page](extension.md#the-extension-follows-rfc-8-prefixed-naming-with-the-prefix-sp-ops). RFC-8 also says it does not define tables. Instead it "offers a general way to make such additional data types discoverable". The node types below use that opening.
:::

This page specifies two attribute keys and three node types from the [extension key registry](design-decisions.md#extension-key-registry). Its examples also show `sp-ops:spec`, `sp-ops:tile`, and `sp-ops:timepoint`, which the [hierarchy](hierarchy.md) and [fields of view](fields-of-view.md) pages define.

| Identifier | Kind | Applies to | Value | Requirement |
| --- | --- | --- | --- | --- |
| `sp-ops:table` | attribute key | table node | `{"type", "tableVersion", "granularity", "region"}`; `type` is an ngio table type; `region` is an OPTIONAL RFC-8 `Reference` mirroring `spatialdata_attrs.region` | MUST on every table node |
| `sp-ops:relationships` | attribute key | plate and well groups (0.5); any collection node (RFC-8) | `{"version": string, "edges": array}` | SHOULD |
| `sp-ops:table` | node type | collection nodes | node with a `zarr` `path` to a spatialdata `TableModel` element | as needed |
| `sp-ops:shapes` | node type | collection nodes | node with a `zarr` `path` to a `ShapesModel` element | as needed |
| `sp-ops:points` | node type | collection nodes | node with a `zarr` `path` to a `PointsModel` element | as needed |

Plate `collection.json` excerpt (proposed). `"0.x"` is the placeholder version RFC-8 uses in its own examples.

```json
{
  "ome": {
    "version": "0.x",
    "type": "collection",
    "id": "plate",
    "name": "ops_plate",
    "attributes": {
      "plate": { /* rows, columns, acquisitions: see the hierarchy page */ },
      "sp-ops:spec": {"version": "0.1.0-draft", "profile": "tiled"},
      "sp-ops:acquisitions": [ /* 80 entries, see the hierarchy page */ ],
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
    },
    "nodes": [
      {"type": "collection", "id": "A-1", "name": "A/1", "path": {"type": "json", "path": "./A/1/collection.json"}},
      {"type": "sp-ops:table", "id": "library", "name": "library", "path": {"type": "zarr", "path": "./library"},
       "attributes": {"sp-ops:table": {"type": "condition_table", "tableVersion": "1", "granularity": "perturbation"}}}
    ]
  }
}
```

Well `A/1/collection.json` excerpt (proposed). Node ids replace `/` with `-` (D10). The `well` references cross into the plate document and carry a `path` (D5). The `t2` collection carries the edges shown in the previous section.

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
      "sp-ops:relationships": {
        "version": "0.1",
        "edges": [
          {"from": "f0/t2/bases", "to": "reads", "method": "join",
           "params": {"how": "inner", "left_on": ["read"], "right_on": ["read"]},
           "status": "computed", "cardinality": "n:1"}
        ]
      }
    },
    "nodes": [
      {"type": "sp-ops:table", "id": "A-1-cells", "name": "cells", "path": {"type": "zarr", "path": "./cells"},
       "attributes": {"sp-ops:table": {"type": "feature_table", "tableVersion": "1", "granularity": "cell"}}},
      {"type": "sp-ops:table", "id": "A-1-reads", "name": "reads", "path": {"type": "zarr", "path": "./reads"},
       "attributes": {"sp-ops:table": {"type": "generic_table", "tableVersion": "1", "granularity": "read"}}},
      {"type": "collection", "id": "A-1-f0", "name": "f0", "attributes": {"sp-ops:tile": {"index": 0}},
       "nodes": [
         {"type": "collection", "id": "A-1-f0-t2", "name": "t2",
          "attributes": {
            "sp-ops:timepoint": {"index": 2},
            "sp-ops:relationships": { /* cell_bbox, bases, spots/peaks edges to cell_seg */ }
          },
          "nodes": [
            {"type": "multiscale", "id": "A-1-f0-t2-cell_seg", "name": "cell_seg",
             "path": {"type": "zarr", "path": "./f0-t2-pheno/labels/cell_seg"},
             "attributes": {"labels": {"source": [{"id": "A-1-f0-t2-pheno"}]}}},
            {"type": "sp-ops:shapes", "id": "A-1-f0-t2-cell_bbox", "name": "cell_bbox",
             "path": {"type": "zarr", "path": "./f0-t2-cell_bbox"}},
            {"type": "sp-ops:points", "id": "A-1-f0-t2-bases", "name": "bases",
             "path": {"type": "zarr", "path": "./f0-t2-bases"}},
            {"type": "collection", "id": "A-1-f0-t2-spots", "name": "spots", "nodes": [
              {"type": "sp-ops:points", "id": "A-1-f0-t2-spots-peaks", "name": "peaks",
               "path": {"type": "zarr", "path": "./f0-t2-spots-peaks"}}
            ]}
          ]}
       ]}
    ]
  }
}
```

The plate and well edges appear in both the RFC-8 sidecar and the 0.5 group attributes. The `t`-level edges appear only in the sidecar, or in the well group when no sidecar is written. A validator SHOULD report any disagreement between the two copies of the plate and well edges.

## SpatialData view

:::{admonition} Status
:class: note
Element names containing `/`, sub-views such as `sdata["A/1"]`, partial reads of a sub-folder, and the tree repr come from the experimental hierarchical SpatialData branch. None is released. The branch's `__getitem__` builds a sub-view without `attrs`, so the relationships list is not visible from a sub-view today (D10). Once loaded with the flattened names of D10 through the proposed reader of the next section, spatialdata v0.8.0 shows the same elements in the typed containers of its flat repr.
:::

Partial read of one well, in the repr format described on the [hierarchy page](hierarchy.md#the-spatialdata-view-is-a-tree). Only the first `t` value of tile `f0` is listed, and cycles `r3` to `r9` are omitted; a real repr prints every element.

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

Plate root, same format, truncated. The `A/` folder lists every element of the three wells with the row prefix stripped, so `library`, the target of every `barcode` edge, sits beside it. The coordinate systems block is omitted, and the `well_features` shape is illustrative.

```text
SpatialData object at /data/ops_plate.zarr
├── library: [Table] AnnData (4211, 0)
├── well_features: [Table] AnnData (3, 8)
├── wells: [Shapes] GeoDataFrame (3, 4)
└── A/ (1650 elements)
    ├── 1/cells: [Table] AnnData (27488, 1400)
    ├── 1/f0/t2/bases: [Points2D] DataFrame (612340, 6)
    ├── 1/f0/t2/cell_bbox: [Shapes] GeoDataFrame (859, 1)
    ├── 1/footprints: [Shapes] GeoDataFrame (320, 1)
    ├── 1/reads: [Table] AnnData (1203456, 0)
    └── ...
```

Row counts are illustrative except the 859 cells per frame and the 4211 library rows; the 4 tiles and the 320 images follow from the illustrative 2 by 2 grid. Every element under a `t` collection carries one transformation per ancestor frame (D5). The `'A/1'` and `'plate'` listings therefore hold every element of the well, and a `t` frame lists only the elements of that (tile, `t`). Tables never appear under a coordinate system; they reach geometry through `spatialdata_attrs` or through an edge.

## Join examples

Two blocks follow. The first runs on spatialdata v0.8.0 with the flattened element names of D10. Apart from opening the store, it uses only released names from the spatialdata public application programming interface (API). The second uses the proposed relationship-driven API.

### Key joins with spatialdata v0.8.0

`join_spatialelement_table` and `match_table_to_element` follow `spatialdata_attrs`, so they cover the `cells` to `cell_seg` annotation. Joins through `read` and `barcode`, and spatial joins, run in pandas and geopandas. spatialdata v0.8.0 `read_zarr` opens spatialdata's own layout, not an OME-NGFF 0.5 plate. The first line therefore stands for a reader of this specification (proposed) that applies the flattening rule of D10 and returns flattened names. Every call after it is released v0.8.0 API.

```python
import geopandas as gpd
import spatialdata as sd
from spatialdata import get_element_annotators, join_spatialelement_table, match_table_to_element

sdata = sd.read_zarr("ops_plate.zarr")                    # proposed: a reader that applies the D10 flattening rule; every call below is v0.8.0

get_element_annotators(sdata, "A-1-f0-t2-cell_seg")
# {'A-1-cells'}

# annotation join: rows of cells that describe tile f0 at t2
cells_t2 = match_table_to_element(sdata, element_name="A-1-f0-t2-cell_seg", table_name="A-1-cells")
elements, cells_t2 = join_spatialelement_table(                                  # same rows, plus the labels element
    sdata=sdata, spatial_element_names="A-1-f0-t2-cell_seg", table_name="A-1-cells", how="inner"
)
cells_t2.obs[["cell_uid", "label", "barcode", "perturbation_id"]].head(2)

# key join by index: the box of every cell in the joined table
cell_bbox = sdata["A-1-f0-t2-cell_bbox"]
boxes = cell_bbox.loc[cells_t2.obs["label"].to_numpy()]     # index equals the label value

# foreign key joins in pandas: reads to library, bases to reads
reads = sdata["A-1-reads"].obs
library = sdata["library"].obs
reads = reads.merge(library[["barcode", "role", "control_type"]], on="barcode", how="left")
bases = sdata["A-1-f0-t2-bases"].compute()                  # dask DataFrame to pandas
bases = bases.merge(reads[["read", "barcode", "qc_pass"]], on="read", how="inner")

# spatial join in geopandas: base calls within cell boxes, both in the frame A/1/f0/t2
points = gpd.GeoDataFrame(bases, geometry=gpd.points_from_xy(bases["x"], bases["y"]))
in_boxes = gpd.sjoin(points, cell_bbox[["geometry"]], how="left", predicate="within")
```

The `bases` to `cell_seg` edge is a pixel lookup, not a box test, so the last two lines approximate it. A box test assigns a call that falls between two cells to both boxes when they overlap. The label lookup assigns it to at most one cell.

### Relationship-driven joins (proposed)

:::{admonition} Status
:class: note
Every name in this block is proposed. `index_element` and `annotate_by_table` come from the Padua prototype. `query`, `check_relationships`, and the `depth`, `types`, and `ids` arguments come from the Venice `query.py` sketch and its TODO list. The module name `spatialdata.relationships` is a placeholder of the design record. The Venice `query` walks undirected `element_relationships` groups. An implementation of this specification walks the directed edge list in both directions. When it propagates ids, it applies `left_on` and `right_on`, or the `sjoin` result column.
:::

```python
import spatialdata as sd
from spatialdata import match_table_to_element
from spatialdata.relationships import (                     # proposed API
    annotate_by_table, check_relationships, index_element, query,
)

sdata = sd.read_zarr("ops_plate.zarr")                      # hierarchical names, proposed
edges = sdata.attrs["sp-ops"]["relationships"]              # merged list, names relative to the plate root
edges[0]
# {'from': 'A/1/cells', 'to': 'library', 'method': 'join',
#  'params': {'how': 'left', 'left_on': ['barcode'], 'right_on': ['barcode']},
#  'status': 'computed', 'cardinality': 'n:1'}

# declare a key join between an element and a table (Padua names); label repeats across
# the 32 frames of a well, so restrict the table to this frame first
cells_t2 = match_table_to_element(sdata, element_name="A/1/f0/t2/cell_seg", table_name="A/1/cells")
sdata["A/1/f0/t2/cells"] = cells_t2                        # proposed API; per-frame view of A/1/cells
index_element(sdata, "A/1/f0/t2/cell_bbox")                 # proposed API; adds a _sd_index column
annotate_by_table(                                          # proposed API
    sdata, element_name="A/1/f0/t2/cell_bbox", table_name="A/1/f0/t2/cells",
    left_index=True, right_on="label", how="inner",
)

# promote a suggested spatial join after storing cell_label on spots/peaks
peaks_edge = next(e for e in edges if e["from"] == "A/1/f0/t2/spots/peaks" and e["method"] == "sjoin")
peaks_edge["status"] = "computed"

check_relationships(sdata)                                  # proposed API; per edge: cardinality, coverage, order, missing ids

# everything reachable from two cells
linked = query(sdata, "A/1/f0/t2/cell_seg", depth="all", ids=[812, 813])   # proposed API
linked["A/1/cells"].obs[["cell_uid", "barcode", "perturbation_id"]]
linked["A/1/f0/t2/cell_bbox"]                               # two rectangles
linked["A/1/f0/t2/bases"]                                   # base calls with cell_label in {812, 813}
linked["A/1/reads"]                                         # their reads, reached through read
linked["library"]                                           # their sgRNAs, reached through barcode

# one hop from the reads table, tables and points only
query(sdata, "A/1/reads", depth=1, types=["tables", "points"])              # proposed API
# keys: 'A/1/reads', 'library', 'A/1/f0/t2/bases', 'A/1/f0/t2/spots/peaks', ... one pair per frame
```

## Relationship graph

Solid edges are `computed` entries of `sp-ops:relationships`, labelled with the method and the keys. Dotted edges are links that live elsewhere: `spatialdata_attrs` annotations, the RFC-8 `labels.source` reference, the `element` column of `images`, and one `suggested` edge.

```{mermaid}
graph LR
  subgraph T2 ["A/1/f0/t2 (one tile, one timepoint)"]
    PH["pheno (image)"]
    CS["cell_seg (labels)"]
    CB["cell_bbox (shapes)"]
    BA["bases (points)"]
    PK["spots/peaks (points)"]
    PH -. "labels.source" .-> CS
    CB -- "join index = value, 1:1" --> CS
    BA -- "sjoin within, result cell_label, n:1" --> CS
    PK -. "sjoin within, suggested" .-> CS
  end
  subgraph W ["A/1 (well)"]
    CF["cells (table)"]
    RD["reads (table)"]
    FP["footprints (shapes)"]
    IM["images (table)"]
    FV["fov_features (table)"]
    IM -. "spatialdata_attrs region, image_id" .-> FP
    FV -. "spatialdata_attrs region, image_id" .-> FP
  end
  subgraph P ["plate root"]
    LIB["library (table)"]
    WL["wells (shapes)"]
    WF["well_features (table)"]
    WF -. "spatialdata_attrs region, well_id" .-> WL
  end
  CF -. "spatialdata_attrs region, label" .-> CS
  IM -. "element column" .-> PH
  BA -- "join read = read, n:1" --> RD
  PK -- "join read = read, 1:1" --> RD
  CF -- "join barcode = barcode, n:1" --> LIB
  RD -- "join barcode = barcode, n:1" --> LIB
```

## Sources

Specifications this page relies on.

- [ngio table specifications](https://biovisioncenter.github.io/ngio/stable/table_specs/overview/): the five table types, their group attributes, the required ROI columns, and the `measurement`, `categorical`, `metadata` feature vocabulary.
- [OME-NGFF RFC-8: Collections and Extensibility](https://ngff.openmicroscopy.org/rfc/8/index.html#high-content-screening-hcs-metadata): node types, `attributes`, `Reference`, `labels.source`, the extension naming scheme, and the note on tables; status D1.
- [OME-NGFF 0.5](https://ngff.openmicroscopy.org/0.5/) and its [HCS layout](https://ngff.openmicroscopy.org/0.5/#hcs-layout): the released plate and well metadata the store keeps valid.
- Chan Zuckerberg Initiative (CZI) OPS data standard v0.1.0 (draft) and the conformance check of a public Biohub submission: `cell_uid`, `perturbation_id`, `barcode`, `role`, `control_type`, and rules V-10 and V-11. No public URL appears in the source material.
- [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119.txt): the meaning of MUST, SHOULD, and MAY.

Software whose released names appear in the examples.

- [spatialdata documentation](https://spatialdata.scverse.org/en/stable/): the v0.8.0 public API used here, `join_spatialelement_table`, `match_table_to_element`, `get_element_annotators`, `TableModel.parse`, `bounding_box_query`, `polygon_query`, `to_polygons`, and the models.
- [spatialdata tables tutorial](https://spatialdata.scverse.org/en/stable/tutorials/notebooks/notebooks/examples/tables.html): the `region`, `region_key`, `instance_key` annotation model.
- [geopandas documentation](https://geopandas.org/en/stable/): `read_parquet`, `sjoin` with `predicate`, and `points_from_xy`.
- [anndata documentation](https://anndata.readthedocs.io): `obs`, `var`, `X`, `uns`, `obsm`, and the Zarr layout of those attributes.

Prototypes and layouts the proposals depend on.

- [Padua hackathon issue 6](https://github.com/scverse/2026_04_hackathon_padua/issues/6) and its [scverse project view](https://github.com/orgs/scverse/projects/70/views/1?reload=1&pane=issue&itemId=169148807&issue=scverse%7C2026_04_hackathon_padua%7C6): the `spatialdata_elements_graph` prototype with `from`, `to`, `method`, `params`, and the `index_element` and `annotate_by_table` sketches.
- [Venice hackathon relationships prototype](https://github.com/BiocCodingCollaborations/VeniceHackathon2026/tree/main/interoperability/relationships): `element_relationships`, `join_strategy` values `index`, `value`, and column name, `sjoin_suggestions`, and the `query()` and `check_relationships()` sketches.
- [scallops and Biohub OPS layout (HackMD)](https://hackmd.io/@D9GB-ZDcTQyFd7U5aMmk5g/r18soYBuzx): `features/*/A1-objects.parquet`, `features/*/A1.parquet`, `merge/A1.parquet`, `reads/reads/A1.parquet`, `reads/bases/A1.parquet`, and the uint64 `read` join column.
- [Hierarchical SpatialData slides](https://raw.githubusercontent.com/LucaMarconato/spatialdata/refs/heads/vibecoded-experiment/hierarchical-spatialdata/slides-hierarchical-spatialdata.html): `/` in element names, sub-views, partial reads, and the tree repr.
