# Extension keys and node types

This page consolidates every extension that the sp-ops specification introduces to Open Microscopy Environment Next-Generation File Format (OME-NGFF) request for comments 8 (RFC-8, collections and extensibility). The extensions describe optical pooled screening (OPS) data. It states the prefix and lists the RFC-8 extension points used. It then gives one subsection per identifier with a field table and a JSON example. It closes with a complete collection for the running example and a mapping to the OME-NGFF 0.5 high-content screening (HCS) layout. A reader should be able to write and validate the extension from this page alone. The identifiers and the running example follow the [design decisions](design-decisions.md) page; when the two disagree, that page wins.

:::{admonition} Status
:class: note
The `collection.json` documents, the three node types, and the placement of keys inside a node's `attributes` object are proposals. They depend on RFC-8, whose own text reads "This proposal is early. Status: D1" and "This RFC has not been implemented yet". The `scene` attribute also depends on RFC-5 (coordinate systems and transformations, status S4). Node ids and the `from` and `to` names of `sp-ops:relationships` derive from element names containing `/`. Those names depend on the unreleased hierarchical SpatialData branch; the flattened forms are valid spatialdata v0.8.0 names. `sp-ops:relationships` also depends on two unreleased hackathon prototypes. The same keys written as siblings of `ome` in an OME-NGFF 0.5 Zarr group depend on nothing unreleased and are normative now (D1, D8, D9). The section on OME-NGFF 0.5 describes released behaviour and existing stores.
:::

## The extension follows RFC-8 prefixed naming with the prefix `sp-ops`

RFC-8 separates core identifiers from extension identifiers by a prefix. It states that "Unprefixed identifiers are reserved for the core specification and can only be added or modified through the RFC process." It adds that "Prefixed identifiers (separated by `:`) can be freely introduced by custom extensions without requiring an RFC." In its words, "The prefix identifies the user or organization that introduces and maintains the extension." The `ome:` prefix "is reserved for official extensions that have not yet been incorporated into the core specification". An RFC-8 reader that does not know a prefix SHOULD "treat the referenced value as opaque" and MAY "skip it or display it with a generic representation". For OME-NGFF 0.5, the audited store already carries a sibling key (`channels_metadata`) next to `ome`, and its plate root passes the OPS validator.

The prefix of this specification is `sp-ops`. Every non-core attribute key and node type introduced here MUST be spelled `sp-ops:<key>`. The reasons are recorded in [D1](design-decisions.md#d1-the-extension-prefix-is-sp-ops-with-nine-attribute-keys-and-three-node-types) and are summarised here.

- RFC-8's own examples use project names as prefixes (`fractal:well`, `mobie:grid`, `neuroglancer:shader`, `webknossos:settings`). A reader who meets `sp-ops:tile` can find this specification by its name.
- `scverse` was rejected because other scverse projects would need the same prefix for unrelated keys, and the prefix alone would not lead to the defining document.
- `ops` was rejected because it names a technique, and several OPS pipelines exist.
- `ome` is reserved by RFC-8.

RFC-8 asks that prefixes "SHOULD be registered in a central registry (a Github repository under the `ome` organization)". The prefix `sp-ops` is not registered there, and this page does not claim registration.

The extension surface is nine attribute keys, three node types, no path type, and no coordinate transformation type. Where the identifiers live depends on the layout. In an RFC-8 document they sit inside a node's `attributes` object. In an OME-NGFF 0.5 store they sit in the Zarr group `attributes` object as siblings of `ome`. The audited Biohub store already does this with its `channels_metadata` key. The spelling is identical in both places. The RFC-8 view is written as standalone `collection.json` documents, one at the plate root and one at each well root, for the reason given on the [hierarchy page](hierarchy.md#rfc-8-collections-describe-the-same-plate-as-nodes) ([D2](design-decisions.md#d2-plates-and-wells-stay-valid-ome-ngff-05-the-rfc-8-view-is-a-sidecar)). RFC-8 allows this. Its text reads "Node metadata may also be stored in standalone JSON files that are stored in arbitrary locations and have a file name ending in `.json`."

## The extension uses two of the five RFC-8 extension points

RFC-8 names its extension points as "node types, attribute keys, path types, coordinate transformation types, and coordinate system axis types". This specification uses two of the five.

| RFC-8 extension point | Used | Identifiers |
| --- | --- | --- |
| node types | yes | `sp-ops:shapes`, `sp-ops:points`, `sp-ops:table` |
| attribute keys | yes | `sp-ops:spec`, `sp-ops:acquisitions`, `sp-ops:tile`, `sp-ops:tileLayout`, `sp-ops:timepoint`, `sp-ops:registration`, `sp-ops:channels`, `sp-ops:table`, `sp-ops:relationships` |
| path types | no | core `zarr` and `json` reach every element |
| coordinate transformation types | no | RFC-5 `identity`, `scale`, `translation`, `affine`, `byDimension` |
| coordinate system axis types | no | RFC-5 `space` and `channel` |

The extension relies on these core RFC-8 identifiers. The node types are `collection` and `multiscale`. The attribute keys are `plate`, `well`, `acquisition`, `labels`, and `scene`. The interfaces are `Path` and `Reference`. The diagram shows where each identifier attaches in the running example. Each node label gives the node name, then the attribute keys it carries; every key is `sp-ops:`-prefixed except `acquisition`, `labels`, and `scene`. Shapes, points, and table nodes are marked by their node type.

```{mermaid}
graph TD
  subgraph plate_doc ["collection.json"]
    P["plate: spec, acquisitions, relationships, scene"]
    LIB["library (table node): table"]
  end
  subgraph well_doc ["A/1/collection.json"]
    W["well A/1: tileLayout, relationships, scene"]
    TL["tiles (shapes node)"]
    CT["cells (table node): table"]
    F0["f0: tile"]
    T2["t2: timepoint, registration, relationships, scene"]
    ISS["iss"]
    R1["r1: acquisition, channels"]
    PH["pheno: acquisition, channels"]
    SEG["cell_seg: labels.source"]
    BA["bases (points node)"]
    BB["cell_bbox (shapes node)"]
  end
  P --> W
  P --> LIB
  W --> TL
  W --> CT
  W --> F0
  F0 --> T2
  T2 --> ISS
  ISS --> R1
  T2 --> PH
  T2 --> SEG
  T2 --> BA
  T2 --> BB
```

## Nine attribute keys and three node types make up the registry

Each subsection gives the node the identifier applies to, its requirement level, a field table, and a JSON example. The examples come from the running example (well `A/1`, tile `f0`, timepoint label `t2`). The field tables use "MUST" for fields a writer has to emit, "SHOULD" for recommended fields, and "MAY" for optional ones. Values marked illustrative in the [running example](design-decisions.md#running-example) are illustrative here too.

### `sp-ops:spec` names the specification version and the profile

Applies to the plate collection node (RFC-8) or the plate group (0.5). A writer MUST emit it. A writer MUST use the `tiled` profile when a well has more than one tile and the `stitched` profile when each acquisition yields one image per well. The audited Biohub store is the `stitched` profile with one `merged` acquisition per well; its plate, well, and image metadata are in the [stitched profile example](design-decisions.md#stitched-profile-example) of D2.

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `version` | string | MUST | version of this specification the store follows; `0.1.0-draft` for this draft |
| `profile` | string | MUST | `tiled` or `stitched` |

```json
{"sp-ops:spec": {"version": "0.1.0-draft", "profile": "tiled"}}
```

### `sp-ops:acquisitions` defines every acquisition once, at the plate

Applies to the plate collection node or the plate group. A writer MUST emit one entry per core acquisition, and the `id` MUST equal the core acquisition id in the same document. An acquisition is one pass of the microscope over the plate. For OPS it is one in situ sequencing (ISS) cycle `r` at one fixation timepoint `t`, the phenotypic round at one `t`, or a `merged` image. A `merged` acquisition is one stitched image per well whose channels were assembled after registration from the ISS cycles and the phenotypic round of one `t` ([D2](design-decisions.md#d2-plates-and-wells-stay-valid-ome-ngff-05-the-rfc-8-view-is-a-sidecar)). A writer MUST NOT use `merged` when the raw acquisitions are stored; it then stores the product under `reg/` (D6). The core acquisition id (RFC-8) or name (0.5) MUST be `iss-t<t>-r<r>`, `pheno-t<t>`, or `merged-t<t>`. Image nodes carry only the core `acquisition` reference; there is no per-image copy of `kind`, `t`, or `r`. Registered or resampled images are derived nodes, not acquisitions.

RFC-8 defines the core `Acquisition` interface with only `id` (string matching `[a-zA-Z0-9-_.]+`) and `name`. In a 0.5 plate the acquisition `id` is an integer, so the entry carries the integer there and the string in the RFC-8 document.

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `id` | string (RFC-8) or integer (0.5) | MUST | equals the core acquisition id in the same document |
| `kind` | string | MUST | `iss`, `pheno`, or `merged` |
| `t` | integer | MUST | fixation timepoint label |
| `r` | integer or null | MUST | ISS cycle; null when `kind` is `pheno` or `merged` |
| `anchor` | boolean | MUST | true for the reference acquisition of this `t` |

Exactly one entry per `t` MUST have `anchor: true`. When a store has none, a reader uses the ISS acquisition with the lowest `r` at that `t`. A `merged` acquisition is already registered, maps into the registered frame by a pure scale, and is the anchor when it is the only acquisition at its `t` (D5). In the 0.5 form of the real store the one entry is `{"id": 0, "kind": "merged", "t": 2, "r": null, "anchor": true}`, where `t` is illustrative because the audit did not record it.

```json
{
  "plate": {
    "rows": [{"id": "A", "name": "A"}],
    "columns": [{"id": "1", "name": "1"}, {"id": "2", "name": "2"}, {"id": "3", "name": "3"}],
    "acquisitions": [
      {"id": "iss-t2-r1", "name": "ISS cycle 1, t=2"},
      {"id": "iss-t2-r2", "name": "ISS cycle 2, t=2"},
      {"id": "pheno-t2", "name": "phenotypic round, t=2"}
    ]
  },
  "sp-ops:acquisitions": [
    {"id": "iss-t2-r1", "kind": "iss", "t": 2, "r": 1, "anchor": true},
    {"id": "iss-t2-r2", "kind": "iss", "t": 2, "r": 2, "anchor": false},
    {"id": "pheno-t2", "kind": "pheno", "t": 2, "r": null, "anchor": false}
  ]
}
```

### `sp-ops:tile` marks a tile collection

A tile is one stage position in one well, imaged across every acquisition. In the RFC-8 view it is a `collection` node that holds one collection per fixation timepoint. In the 0.5 layout the same attribute sits on every image group that belongs to the tile. A writer MUST emit it in the `tiled` profile. The `stitched` profile has no tile level ([D10](design-decisions.md#d10-element-names-are-the-on-disk-paths-and-a-hyphen-flattens-them-for-v080)), so the key does not appear there.

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `index` | integer | MUST | the tile; equals the `index` of the matching `tiles` row |

```json
{"type": "collection", "id": "A-1-f0", "name": "f0",
 "attributes": {"sp-ops:tile": {"index": 0}},
 "nodes": []}
```

### `sp-ops:tileLayout` points to the tile layout shapes element

Applies to the well collection node. A writer MUST emit it in the `tiled` profile. Its value is an RFC-8 `Reference` to the `sp-ops:shapes` node named `tiles`. RFC-8 defines a `Reference` as an object with `id` (required) and `path` (required only "for external references").

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `id` | string | MUST | id of the `sp-ops:shapes` node that holds the layout |
| `path` | `Path` object | absent | the `tiles` node MUST be a child of the well collection ([fields of view](fields-of-view.md#rfc-8-marks-a-tile-as-a-collection-with-sp-opstile)), so the reference is internal and RFC-8 requires no `path` |

The `tiles` element has exactly one row per tile, never one per acquisition. Its normative schema, the companion `footprints` element, and the optional ngio `roi_table` export are specified in [The tile layout is one shapes row per tile](fields-of-view.md#the-tile-layout-is-one-shapes-row-per-tile) (D3).

The `well.row` and `well.column` references below carry a `path` because the rows and columns are defined in the plate document (see the complete example).

```json
{
  "attributes": {
    "well": {
      "row": {"id": "A", "path": {"type": "json", "path": "../../collection.json"}},
      "column": {"id": "1", "path": {"type": "json", "path": "../../collection.json"}}
    },
    "sp-ops:tileLayout": {"id": "A-1-tiles"}
  },
  "nodes": [
    {"type": "sp-ops:shapes", "id": "A-1-tiles", "name": "tiles", "path": {"type": "zarr", "path": "./tiles"}},
    {"type": "sp-ops:shapes", "id": "A-1-footprints", "name": "footprints", "path": {"type": "zarr", "path": "./footprints"}}
  ]
}
```

### `sp-ops:timepoint` marks a fixation timepoint collection

Applies to the `t` collection inside a tile. A writer MUST emit it. Different `t` values are different fixed cells, so nothing under one `t` collection is aligned to another `t` collection. The `t` values of the running example are folder labels from the scallops layout (`t=2` to `t=10`), not measured timepoints. The optional `time` and `unit` fields exist for depositors who know the elapsed time.

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `index` | integer | MUST | the `t` label; equals the `t` of every acquisition under the collection |
| `time` | number | MAY | elapsed time since a depositor-defined origin |
| `unit` | string | MAY | an RFC-5 time unit such as `second` or `hour`; MUST accompany `time` |

```json
{"type": "collection", "id": "A-1-f0-t2", "name": "t2",
 "attributes": {"sp-ops:timepoint": {"index": 2}},
 "nodes": []}
```

### `sp-ops:registration` names the anchor channel and the reference image

Applies to the `t` collection. A writer SHOULD emit it, and `anchorChannel` MUST be present when the key is. Within one (tile, `t`) the anchor channel is the channel whose `sp-ops:channels` role is `nuclear`, 4′,6-diamidino-2-phenylindole (DAPI) in the running example. That channel is present in every ISS cycle and in the phenotypic round, so it can anchor both registrations. The reference image is the acquisition whose `sp-ops:acquisitions` entry has `anchor: true` for that `t`; `reference` overrides that choice for one tile.

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `anchorChannel` | string | MUST | channel name used for registration; its role MUST be `nuclear` |
| `reference` | `Reference` | MAY | the image node that maps to the registered frame by a pure scale |

The reference image maps into the registered frame by a pure scale. Every other acquisition image at that `t` carries its scale followed by an affine estimated from anchor channel to anchor channel. Labels and derived images computed in the registered frame carry a pure scale; points and shapes computed there carry an identity ([D5](design-decisions.md#d5-cycles-are-registered-to-the-dapi-channel-of-the-first-iss-cycle-at-each-timepoint)). In the sidecar the input frame `intrinsic` already includes the multiscale `scale`, so a pure-scale edge is written as `identity` from `intrinsic` (D5).

```json
{"sp-ops:registration": {"anchorChannel": "DAPI", "reference": {"id": "A-1-f0-t2-iss-r1"}}}
```

### `sp-ops:channels` gives every channel a role

Applies to every image group (0.5) or `multiscale` node (RFC-8) that is not a label image, including derived images. A writer MUST emit it. The value is an array with one object per channel, in array order. `sp-ops:channels` is authoritative for channel identity, and the `c` coordinate of the spatialdata image MUST carry the same names in the same order. Channel names are the depositor's names; a nuclear stain called Hoechst keeps its name and takes the role `nuclear`.

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `name` | string | MUST | depositor's channel name, equal to the `c` coordinate value |
| `role` | string | MUST | `nuclear`, `base`, `stain`, or `other` |
| `base` | string | MUST when `role` is `base`, absent otherwise | `A`, `C`, `G`, or `T` |

Registration reads the channel whose role is `nuclear`, so the channels of one acquisition MUST include exactly one such channel (D1). When a store also carries other channel-name metadata, such as the `channels_metadata` key of the audited store, a validator SHOULD warn on disagreement. A depositor MAY use fewer than four `base` channels. The ISS-derived channels of a `merged` image carry `role: "other"` (D2).

```json
{
  "sp-ops:channels": [
    {"name": "DAPI", "role": "nuclear"},
    {"name": "A", "role": "base", "base": "A"},
    {"name": "G", "role": "base", "base": "G"},
    {"name": "C", "role": "base", "base": "C"},
    {"name": "T", "role": "base", "base": "T"}
  ]
}
```

The phenotypic image of the running example uses `DAPI` with role `nuclear` and `GFP`, `stain_3`, `stain_4`, `stain_5` with role `stain`; the last three names are illustrative.

### `sp-ops:table` declares the table type and the row unit

Applies to every `sp-ops:table` node. A writer MUST emit it. The vocabulary is the five ngio table types, `generic_table`, `roi_table`, `masking_roi_table`, `feature_table`, and `condition_table`. ngio recognises the last four automatically on read and loads anything else as a generic table. In memory the same facts live in `adata.uns["sp-ops"]` as `table_type`, `table_version`, and `granularity`. The design record ([D8](design-decisions.md#d8-table-types-use-the-ngio-vocabulary-under-one-namespaced-dictionary)) relies on spatialdata v0.8.0 writing and reading `uns` unchanged. `spatialdata_attrs` stays exactly `region`, `region_key`, `instance_key` as `TableModel` defines them.

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `type` | string | MUST | one of the five ngio table type strings |
| `tableVersion` | string | MUST | `"1"`, the ngio V1 table specifications |
| `granularity` | string | MUST | `cell`, `image`, `well`, `read`, or `perturbation` |
| `region` | `Reference` | MAY | mirrors `spatialdata_attrs.region`; omitted when that value is a list, because a `Reference` names one node; the list stays in `uns["spatialdata_attrs"]`, which is authoritative |

| Table | `type` | `granularity` | `region` |
| --- | --- | --- | --- |
| `A/1/images` | `condition_table` | `image` | `footprints` |
| `A/1/fov_features` | `feature_table` | `image` | `footprints` |
| `A/1/cells` | `feature_table` | `cell` | none in the node; `spatialdata_attrs.region` lists every `cell_seg` in the well |
| `A/1/reads` | `generic_table` | `read` | none |
| `well_features` | `feature_table` | `well` | `wells` |
| `library` | `condition_table` | `perturbation` | none |

When ngio's own `type` attribute is present on a table group it MUST agree with `sp-ops:table.type`. A writer MUST NOT emit a partial set of ngio group attributes (`type`, `table_version`, `backend`, `index_key`) unless it writes a full ngio `tables` group with the `tables` list. A validator MUST warn on `generic_table`, because ngio defines that type as the fallback "not tied to any specific domain or use case". The `reads` table triggers the warning by design. Widening `feature_table` to a shapes region (`fov_features`, `well_features`) is a spatialdata capability and a departure from ngio, whose feature tables name a label image.

```json
{"type": "sp-ops:table", "id": "A-1-images", "name": "images",
 "path": {"type": "zarr", "path": "./images"},
 "attributes": {"sp-ops:table": {"type": "condition_table", "tableVersion": "1",
                                 "granularity": "image", "region": {"id": "A-1-footprints"}}}}
```

### `sp-ops:relationships` lists join and spatial join edges

Applies to the plate and well groups (0.5) and to any collection node (RFC-8). A writer SHOULD emit it. This key depends on two unreleased element relationships prototypes. The Padua hackathon prototype is `spatialdata_elements_graph` with `from`, `to`, `method`, and `params`; the Venice hackathon prototype is `element_relationships` with `join_strategy` and `sjoin_suggestions`. The value is `{"version": "0.1", "edges": [...]}`, and every edge has the same shape. The edge schema, the meaning of `join` and `sjoin`, and the storage rule are specified in [Elements are linked by joins or spatial joins](joinable-components.md#elements-are-linked-by-joins-or-spatial-joins) ([D9](design-decisions.md#d9-relationships-are-an-edge-list-stored-on-the-lowest-node-that-contains-both-endpoints)). In short, each edge is stored on the lowest collection whose subtree contains both endpoints, with names relative to that collection. The well group carries the `t`-level edges when no sidecar is written. The example below is the `t2` collection of tile `f0`.

```json
{
  "sp-ops:relationships": {
    "version": "0.1",
    "edges": [
      {"from": "cell_bbox", "to": "cell_seg", "method": "join",
       "params": {"how": "inner", "left_on": ["index"], "right_on": ["value"]},
       "status": "computed", "cardinality": "1:1"},
      {"from": "bases", "to": "cell_seg", "method": "sjoin",
       "params": {"how": "left", "predicate": "within", "target_coordinate_system": "A/1/f0/t2",
                  "result_column": "cell_label"},
       "status": "computed", "cardinality": "n:1"}
    ]
  }
}
```

### The node types `sp-ops:shapes`, `sp-ops:points`, and `sp-ops:table` wrap spatialdata elements

RFC-8 defines three node types, `collection`, `multiscale`, and `singlescale`, and lists tables among "future possibilities". This specification adds three node types, one per spatialdata model that RFC-8 does not cover. Images and label images use the core `multiscale` node type, with the core `labels` attribute for label images. Each node follows the RFC-8 `Node` schema.

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `type` | string | MUST | `sp-ops:shapes`, `sp-ops:points`, or `sp-ops:table` |
| `id` | string | MUST | matches `[a-zA-Z0-9-_.]+`; unique within the document; the element name with `/` replaced by `-` |
| `name` | string | MUST | the last path component of the element name; unique within the enclosing collection |
| `path` | `Path` object | MUST | type `zarr`; the element's Zarr group |
| `attributes` | object | MAY | `sp-ops:table` on table nodes; MUST be present there |

A node of these types MUST carry `path` and MUST NOT carry `nodes`; the element is a leaf. RFC-8 makes `id` optional in general, but this specification requires it because `sp-ops:tileLayout`, `sp-ops:table.region`, and `labels.source` refer to nodes by id.

| Node type | spatialdata model | On disk (spatialdata v0.8.0, existing behaviour) |
| --- | --- | --- |
| `sp-ops:shapes` | `ShapesModel` (GeoDataFrame) | Zarr group with `shapes.parquet`, readable with `geopandas.read_parquet`; group attributes `encoding-type: "ngff:shapes"`, `axes`, `coordinateTransformations`, `spatialdata_attrs` (probe-verified, recorded in [D3](design-decisions.md#d3-a-tile-is-a-collection-of-per-timepoint-collections-and-the-layout-is-a-shapes-element)) |
| `sp-ops:points` | `PointsModel` (dask DataFrame) | Zarr group written by spatialdata |
| `sp-ops:table` | `TableModel` (AnnData) | AnnData Zarr group; `spatialdata_attrs` in `uns` |

```json
{"type": "sp-ops:points", "id": "A-1-f0-t2-bases", "name": "bases",
 "path": {"type": "zarr", "path": "./f0-t2-bases"}}
```

### No path type and no transformation type are added

RFC-8 defines two path types. For `zarr`, "Implementations MUST append `zarr.json` to the path to access the metadata of the referenced node". The `json` type "is used for paths that reference nodes in a JSON file". Every sp-ops element, including shapes and points, is a Zarr group written by spatialdata. The `zarr` type therefore reaches every node, and `json` links the plate document to the well documents. A `sp-ops:parquet` or geoparquet path type was rejected. The parquet file is never referenced directly, and the Zarr group that holds it carries the axes and transformations a reader needs.

RFC-5 transformation types cover registration and stitching. `affine` maps "N-dimensional inputs to M-dimensional outputs" as an `(M)x(N+1)` matrix. `byDimension` applies "lower dimensional transformations on subsets of dimensions" through items with `input_axes`, `output_axes`, and `transformation`. `translation` places each registered frame in the well and each well in the plate. `scale` in the multiscale `datasets` gives the pixel size. No prefixed transformation type is needed.

A `json` path from the plate document to a well document.

```json
{"type": "collection", "id": "A-1", "name": "A/1",
 "path": {"type": "json", "path": "./A/1/collection.json"}}
```

A `zarr` path to a shapes element.

```json
{"type": "sp-ops:shapes", "id": "A-1-tiles", "name": "tiles",
 "path": {"type": "zarr", "path": "./tiles"}}
```

## Complete example

The running example is one RFC-8 collection stored as two kinds of document. `ops_plate.zarr/collection.json` is the plate collection; it references one well document per well through the `json` path type. `ops_plate.zarr/A/1/collection.json` is the well collection. It inlines the tile collections, each tile inlines one collection per `t`, and each `t` collection lists its images, labels, points, shapes, and the scene. Relative paths are interpreted relative to the document that contains them, as RFC-8 requires. `"0.x"` is the placeholder version that RFC-8 uses in its own examples; the released number is not yet known. Affine values and the phenotypic stain names are illustrative.

Plate document, `ops_plate.zarr/collection.json`. The two acquisition arrays are truncated to three of the eighty entries, one per (kind, `t`, `r`). The `scene` defines the OPTIONAL coordinate system `plate` and one `translation` per well from the well frame into it ([D5](design-decisions.md#d5-cycles-are-registered-to-the-dapi-channel-of-the-first-iss-cycle-at-each-timepoint)). Each well frame is defined in its own well document, so every `input` is a cross-document RFC-8 `Reference` and MUST carry both `id` and `path`. The translation is `[y, x]` in micrometres. The values are illustrative; they exceed the 34 millimetre width of the real stitched well image, so the wells do not overlap.

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
      ],
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

Well document, `ops_plate.zarr/A/1/collection.json`. The document is truncated as follows.

- Tiles `f1` to `f3` and timepoints `t3` to `t10` repeat the pattern of `f0` and `t2`.
- Cycles `r3` to `r10` (there is no cycle 6) repeat the pattern of `r2`, each with its own affine edge in the scene.
- The well scene holds one translation per (tile, `t`) frame, with values from that tile's `tiles` row; only the `f0`, `t2` edge is shown.
- The derived images `spots/max` and `spots/std` carry no `acquisition` and map into the registered frame by a `byDimension` identity like `r1`; their channel names are illustrative.

```json
{
  "ome": {
    "version": "0.x",
    "type": "collection",
    "id": "A-1",
    "name": "A/1",
    "attributes": {
      "well": {
        "row": {"id": "A", "path": {"type": "json", "path": "../../collection.json"}},
        "column": {"id": "1", "path": {"type": "json", "path": "../../collection.json"}}
      },
      "sp-ops:tileLayout": {"id": "A-1-tiles"},
      "scene": {
        "coordinateSystems": [
          {"id": "A-1", "name": "A/1",
           "axes": [{"name": "y", "type": "space", "unit": "micrometer"},
                    {"name": "x", "type": "space", "unit": "micrometer"}]}
        ],
        "coordinateTransformations": [
          {"type": "translation", "translation": [0.0, 0.0],
           "input": {"id": "A-1-f0-t2"}, "output": {"id": "A-1"}}
        ]
      },
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
      {"type": "sp-ops:table", "id": "A-1-fov_features", "name": "fov_features",
       "path": {"type": "zarr", "path": "./fov_features"},
       "attributes": {"sp-ops:table": {"type": "feature_table", "tableVersion": "1",
                                       "granularity": "image", "region": {"id": "A-1-footprints"}}}},
      {"type": "sp-ops:table", "id": "A-1-cells", "name": "cells",
       "path": {"type": "zarr", "path": "./cells"},
       "attributes": {"sp-ops:table": {"type": "feature_table", "tableVersion": "1", "granularity": "cell"}}},
      {"type": "sp-ops:table", "id": "A-1-reads", "name": "reads",
       "path": {"type": "zarr", "path": "./reads"},
       "attributes": {"sp-ops:table": {"type": "generic_table", "tableVersion": "1", "granularity": "read"}}},
      {"type": "collection", "id": "A-1-f0", "name": "f0",
       "attributes": {"sp-ops:tile": {"index": 0}},
       "nodes": [
         {"type": "collection", "id": "A-1-f0-t2", "name": "t2",
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
                 ]},
                {"type": "identity",
                 "input": {"id": "intrinsic", "path": {"type": "zarr", "path": "./f0-t2-pheno/labels/nuclear_seg"}},
                 "output": {"id": "A-1-f0-t2"}},
                {"type": "identity",
                 "input": {"id": "intrinsic", "path": {"type": "zarr", "path": "./f0-t2-pheno/labels/cell_seg"}},
                 "output": {"id": "A-1-f0-t2"}}
              ]
            },
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
          },
          "nodes": [
            {"type": "collection", "id": "A-1-f0-t2-iss", "name": "iss", "nodes": [
              {"type": "multiscale", "id": "A-1-f0-t2-iss-r1", "name": "r1",
               "path": {"type": "zarr", "path": "./f0-t2-iss-r1"},
               "attributes": {
                 "acquisition": {"id": "iss-t2-r1", "path": {"type": "json", "path": "../../collection.json"}},
                 "sp-ops:channels": [
                   {"name": "DAPI", "role": "nuclear"},
                   {"name": "A", "role": "base", "base": "A"},
                   {"name": "G", "role": "base", "base": "G"},
                   {"name": "C", "role": "base", "base": "C"},
                   {"name": "T", "role": "base", "base": "T"}
                 ]}},
              {"type": "multiscale", "id": "A-1-f0-t2-iss-r2", "name": "r2",
               "path": {"type": "zarr", "path": "./f0-t2-iss-r2"},
               "attributes": {
                 "acquisition": {"id": "iss-t2-r2", "path": {"type": "json", "path": "../../collection.json"}},
                 "sp-ops:channels": [
                   {"name": "DAPI", "role": "nuclear"},
                   {"name": "A", "role": "base", "base": "A"},
                   {"name": "G", "role": "base", "base": "G"},
                   {"name": "C", "role": "base", "base": "C"},
                   {"name": "T", "role": "base", "base": "T"}
                 ]}}
            ]},
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
               ]}},
            {"type": "multiscale", "id": "A-1-f0-t2-nuclear_seg", "name": "nuclear_seg",
             "path": {"type": "zarr", "path": "./f0-t2-pheno/labels/nuclear_seg"},
             "attributes": {"labels": {"source": [{"id": "A-1-f0-t2-pheno"}]}}},
            {"type": "multiscale", "id": "A-1-f0-t2-cell_seg", "name": "cell_seg",
             "path": {"type": "zarr", "path": "./f0-t2-pheno/labels/cell_seg"},
             "attributes": {"labels": {"source": [{"id": "A-1-f0-t2-pheno"}]}}},
            {"type": "collection", "id": "A-1-f0-t2-spots", "name": "spots", "nodes": [
              {"type": "multiscale", "id": "A-1-f0-t2-spots-max", "name": "max",
               "path": {"type": "zarr", "path": "./f0-t2-spots-max"},
               "attributes": {"sp-ops:channels": [
                 {"name": "A", "role": "base", "base": "A"}, {"name": "G", "role": "base", "base": "G"},
                 {"name": "C", "role": "base", "base": "C"}, {"name": "T", "role": "base", "base": "T"}]}},
              {"type": "multiscale", "id": "A-1-f0-t2-spots-std", "name": "std",
               "path": {"type": "zarr", "path": "./f0-t2-spots-std"},
               "attributes": {"sp-ops:channels": [{"name": "std", "role": "other"}]}},
              {"type": "sp-ops:points", "id": "A-1-f0-t2-spots-peaks", "name": "peaks",
               "path": {"type": "zarr", "path": "./f0-t2-spots-peaks"}}
            ]},
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

Two node shapes are not shown in the document. First, an acquisition whose channels are co-registered is one `multiscale` node (`r1`, `pheno` above). When its channels are unaligned, the acquisition becomes a `collection` node that carries the `acquisition` reference. It holds one single-channel `multiscale` child per channel, named after the channel (D4 rule 3). Each child carries a one-entry `sp-ops:channels` array. RFC-8 allows this. The `acquisition` attribute "MAY be set on individual `multiscale` nodes within a well or on a `collection` sub-node grouping all images from a single acquisition". The scene then carries one `byDimension` edge per child. The block shows an unaligned cycle `r2`, truncated to two of its five channels; the [phenotypic rounds](phenotypic-rounds.md#rfc-8-extension-draft) page shows the same shape for `pheno`.

```json
{"type": "collection", "id": "A-1-f0-t2-iss-r2", "name": "r2",
 "attributes": {"acquisition": {"id": "iss-t2-r2", "path": {"type": "json", "path": "../../collection.json"}}},
 "nodes": [
   {"type": "multiscale", "id": "A-1-f0-t2-iss-r2-DAPI", "name": "DAPI",
    "path": {"type": "zarr", "path": "./f0-t2-iss-r2-DAPI"},
    "attributes": {"sp-ops:channels": [{"name": "DAPI", "role": "nuclear"}]}},
   {"type": "multiscale", "id": "A-1-f0-t2-iss-r2-A", "name": "A",
    "path": {"type": "zarr", "path": "./f0-t2-iss-r2-A"},
    "attributes": {"sp-ops:channels": [{"name": "A", "role": "base", "base": "A"}]}}
 ]}
```

Second, resampled products (MAY, D6) sit under a `collection` named `reg` inside the `t` collection. It holds a nested `collection` named `iss` with one `multiscale` per cycle, id `A-1-f0-t2-reg-iss-r2` and path `./f0-t2-reg-iss-r2`. These nodes carry `sp-ops:channels` and no `acquisition`; the `images` table links them to their source (D4, D6).

Points to check when implementing the example.

- Node ids are the hierarchical element names with `/` replaced by `-`, so they satisfy the RFC-8 pattern `[a-zA-Z0-9-_.]+` and are unique within the document. Names are the last path component and are unique within each enclosing collection.
- `iss` is a collection because a cycle is one image. `pheno` is a `multiscale` node because the phenotypic round of the running example is one co-registered image.
- Label nodes point at the nested 0.5 path `./f0-t2-pheno/labels/cell_seg` but are siblings of `pheno` in the collection, as RFC-8's wide example places them. `labels.source` is written as an array of `Reference` objects, the form of RFC-8's wide example. RFC-8's schema table says "array of strings" and its tall example mixes both forms, so a reader SHOULD accept either.
- The `t2` collection node and its registered frame share the id `A-1-f0-t2`, and the well node and its frame share `A-1`. RFC-8 requires node ids and coordinate system ids each to be unique within the document. It does not say whether the two sets share one namespace, so this page keeps the shared spelling of the design record.
- `well.row`, `well.column`, and `acquisition` refer to objects defined in the plate document. RFC-8 requires `path` for external references, so each carries `{"type": "json", "path": "../../collection.json"}` (D5).
- Scene references to a coordinate system in another document carry both `id` and `path`, as RFC-8 requires; the plate scene does so for `A-1`, `A-2`, and `A-3`. 0.5 images declare no named coordinate system, so a reader synthesises `intrinsic` from the image `axes` and the multiscale `scale`. Points and shapes are placed by spatialdata's own element metadata and have no RFC-5 coordinate system, so the scene does not list them (D5).
- The 0.5 metadata is authoritative for rows, columns, wells, acquisitions, and image paths. The documents above MUST agree with it, and a validator MUST report any disagreement.

## OME-NGFF 0.5 carries only part of the extension's information

The table lists where each extension identifier's information lives in a released OME-NGFF 0.5 HCS store today. "No equivalent" means that 0.5 plate and well metadata cannot carry the fact. The sp-ops key is then a sibling of `ome` in the Zarr group attributes, and a 0.5 reader ignores it. RFC-8 itself notes that "some information currently represented by HCS or bioformats2raw.layout is not yet represented in the proposed structures". That gap is why the 0.5 metadata stays authoritative for plate geometry.

The excerpt shows the sibling placement on an image group (existing 0.5 behaviour plus the [D1](design-decisions.md#d1-the-extension-prefix-is-sp-ops-with-nine-attribute-keys-and-three-node-types) rule). The plate and well `zarr.json` blocks, with `sp-ops:spec` and `sp-ops:acquisitions` carrying integer ids, are shown under [D2](design-decisions.md#d2-plates-and-wells-stay-valid-ome-ngff-05-the-rfc-8-view-is-a-sidecar).

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

| Extension identifier | Where the same information lives in OME-NGFF 0.5 HCS today |
| --- | --- |
| `sp-ops:spec` | No equivalent. `ome.version` names the NGFF version, not the profile or this specification. |
| `sp-ops:acquisitions` | Partial. `ome.plate.acquisitions[]` requires an integer `id`; `name` and `maximumfieldcount` are SHOULD; `description`, `starttime`, and `endtime` are MAY. `kind`, `t`, and `r` are readable only from the `name` string by this specification's naming rule; `anchor` has no equivalent. |
| `sp-ops:tile` | Partial. 0.5 records only field counts (`field_count` on the plate, `maximumfieldcount` per acquisition) and has no tile identity. The tile is the leading component of `well.images[].path` (`f0-t2-iss-r1`) by this specification's flattening rule. |
| `sp-ops:tileLayout`, `tiles`, `footprints` | No equivalent. 0.5 stores no field positions. The ngio `roi_table` with `x_micrometer` and `len_x_micrometer` columns is a Fractal convention outside the 0.5 specification. |
| `sp-ops:timepoint` | No equivalent. The `t` label is readable only from the acquisition `name`. The 0.5 `starttime` and `endtime` are epoch timestamps of the acquisition, not fixation labels. |
| `sp-ops:registration` | No equivalent. 0.5 stores only the per-image `scale` in `multiscales[].datasets[].coordinateTransformations`. |
| `sp-ops:channels` | No equivalent in plate or well metadata. The audited store keeps channel names in a non-standard `channels_metadata` sibling of `ome` on the plate group. |
| `sp-ops:table` and the node type `sp-ops:table` | No equivalent. 0.5 defines no tables. The table is an extra Zarr group in the well or plate that `well.images` does not list. |
| `sp-ops:shapes`, `sp-ops:points` | No equivalent. Extra Zarr groups written by spatialdata, named by the flattening rule (`f0-t2-bases`). |
| `sp-ops:relationships` | No equivalent. In the 0.5 layout the plate and well group attributes carry the key. The `t`-level edges live in the well `collection.json`; when no sidecar is written, the well group carries them with well-relative names such as `f0/t2/bases` (D9). |

Core RFC-8 identifiers used by the example and their 0.5 counterparts.

| RFC-8 core identifier | OME-NGFF 0.5 HCS today |
| --- | --- |
| `plate.rows`, `plate.columns`, `plate.acquisitions` with string ids | `ome.plate.rows[].name`, `columns[].name`, `acquisitions[].id` (integer), plus `wells[]` entries with `path`, `rowIndex`, and `columnIndex`, and the plate-level `field_count`; RFC-8 carries none of these extra keys |
| `well.row`, `well.column` as `Reference` objects | implicit in the well group path `A/1`; `ome.well.images[]` lists each image `path` and integer `acquisition` |
| `acquisition` on a `multiscale` node | `ome.well.images[].acquisition` |
| `labels.source` | the `labels` child group of the source image with an `ome.labels` name list, as in the audited store; how 0.5 label metadata records its source image is outside the source material of this specification |
| `scene` | none; only the per-image `scale` in the multiscale datasets |
| `Path` of type `json` | none |

## Sources

- [OME-NGFF RFC-8: Collections and Extensibility](https://ngff.openmicroscopy.org/rfc/8/index.html#high-content-screening-hcs-metadata): status D1. Source of the `Node`, `Path`, and `Reference` interfaces, the `scene`, `labels`, `plate`, `well`, and `acquisition` attributes, the HCS examples, the extension points and prefixed naming, and the compatibility note.
- [OME-NGFF RFC index](https://ngff.openmicroscopy.org/rfc/index.html): entry point for RFC-5 (coordinate systems and transformation types `identity`, `translation`, `scale`, `affine`, `byDimension`, scene storage, time units; status S4, version 0.6.dev3).
- [OME-NGFF dev specification, plate metadata](https://ngff.openmicroscopy.org/specifications/dev/index.html#plate-metadata): `acquisitions` with `id`, `name`, `maximumfieldcount`, `description`, `starttime`, `endtime`; `columns`, `rows`, `wells`, `field_count`, `name`.
- [OME-NGFF dev specification, well metadata](https://ngff.openmicroscopy.org/specifications/dev/index.html#well-metadata): `well.images[].path` and `acquisition`, path character rules.
- [OME-NGFF 0.5](https://ngff.openmicroscopy.org/0.5/) and its [HCS layout](https://ngff.openmicroscopy.org/0.5/#hcs-layout): the released version that the OPS data standard requires.
- [scallops and Biohub OPS layout (HackMD)](https://hackmd.io/@D9GB-ZDcTQyFd7U5aMmk5g/r18soYBuzx): real names for wells, cycles, `t=` folders, labels, peaks, bases, reads, and the `read` join column.
- Chan Zuckerberg Initiative (CZI) OPS data standard v0.1.0 (draft) and the conformance check of a public Biohub submission: the OME-NGFF 0.5 HCS requirement, the `channels_metadata` sibling key, the passing plate root, and the label names. No public URL appears in the source material.
- [ngio table specifications](https://biovisioncenter.github.io/ngio/stable/table_specs/overview/): the five table types, their group attributes, `roi_table` columns, the generic table definition, and the read-time recognition rule.
- [Padua hackathon issue 6](https://github.com/scverse/2026_04_hackathon_padua/issues/6) and its [scverse project view](https://github.com/orgs/scverse/projects/70/views/1?reload=1&pane=issue&itemId=169148807&issue=scverse%7C2026_04_hackathon_padua%7C6): the `spatialdata_elements_graph` prototype with `from`, `to`, `method`, `params`.
- [Venice hackathon relationships prototype](https://github.com/BiocCodingCollaborations/VeniceHackathon2026/tree/main/interoperability/relationships): `element_relationships`, `join_strategy`, `sjoin_suggestions`.
- [spatialdata documentation](https://spatialdata.scverse.org/en/stable/): v0.8.0 models `ShapesModel`, `PointsModel`, `TableModel`, `spatialdata_attrs`, and on-disk element metadata.
- [geopandas documentation](https://geopandas.org/en/stable/): `read_parquet` for the GeoParquet file inside a shapes group.
- [anndata documentation](https://anndata.readthedocs.io): `uns` storage that the `sp-ops` dictionary relies on.
- [Hierarchical SpatialData slides](https://raw.githubusercontent.com/LucaMarconato/spatialdata/refs/heads/vibecoded-experiment/hierarchical-spatialdata/slides-hierarchical-spatialdata.html): element names containing `/`, which the `from` and `to` fields and the node ids derive from.
- [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119.txt): the meaning of MUST, SHOULD, and MAY.
