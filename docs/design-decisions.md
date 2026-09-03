# Design decisions

This page lists the assumptions the specification rests on and the decisions that shape the layout. Each decision gives the choice, the reason, and the alternative that was rejected. When another page disagrees with this one, this page wins.

## Assumptions

| Id | Assumption | Status |
| --- | --- | --- |
| A1 | MUST, SHOULD, and MAY have the meaning given in [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119.txt). MUST is a requirement, SHOULD a strong recommendation, MAY an option. | released |
| A2 | Store metadata is written as [RFC-8](https://ngff.openmicroscopy.org/rfc/8/index.html) nodes only. No OME-NGFF 0.5 `plate` or `well` metadata is written. | RFC-8 is a draft (status D1); this specification tracks it |
| A3 | Coordinate systems and transformations follow [RFC-5](https://ngff.openmicroscopy.org/rfc/5/index.html). | released in OME-NGFF 0.6 |
| A4 | `SpatialData` is hierarchical: `/` in element names, sub-views by prefix, a reader that finds elements by recursing for `element_type`. | [experimental branch](https://github.com/scverse/spatialdata/tree/vibecoded-experiment/hierarchical-spatialdata) |
| A5 | `SpatialData` accepts any axis name, in particular `round` and `t` alongside `c, z, y, x`. | not in a release |
| A6 | Element relationships, including the link from a table to the element it describes, are stored as an edge list, following the [Padua](https://github.com/scverse/2026_04_hackathon_padua/issues/6) and [Venice](https://github.com/BiocCodingCollaborations/VeniceHackathon2026/tree/main/interoperability/relationships) prototypes. SpatialData intends to adopt this beyond OPS data and to retire the `region`, `region_key`, `instance_key` triple. | prototypes |

## Decisions

### D1. A plate collection is one physical plate at one stage

The store root is a screen collection. Its children are plate collections, and each describes one physical plate at one processing stage, tied together by `sp-ops:plate` and told apart by `sp-ops:stage`. The recommended stages are `raw`, `intermediate`, `processed`. A screen MAY include any subset of them and MAY add others.

Why. Each stage is written by a different step and has a different lifetime. Raw data is written once and never changed. Intermediates are tool-defined and can be deleted. Processed data is what analysts open. Making each stage its own plate collection lets a writer produce one without touching the others, and lets a screen reference plates in other stores.

Rejected. A `stage` level between plate and well, which forces every plate to carry every stage. Also `raw/` and `processed/` folders inside every tile and merged collection, which mixes lifetimes in one well and forces raw and processed data to share a tile grid.

### D2. Modality is split at the well, and tiles and merged are separate children of a modality

A well holds `iss/` and `pheno/`. Each modality holds `tiles/` (the `layout` shapes and one collection per field of view) and `merged/` (the stitched image and what was computed on it). The nesting replaces flat names such as `iss_tiles` and `iss_merged`.

Why. The two modalities are imaged at different magnifications, so they have different tile counts and footprints, and each is stitched on its own. A tile image and a merged image differ by two orders of magnitude in size and need different chunking, sharding, and pyramid depth, so they are not siblings in one list.

Rejected. `tile<i>/{iss, pheno}`, only valid when both modalities share one grid. Also `merged` as one more site next to `tile0`, `tile1`, which hides the size difference from a reader.

### D3. Names are opaque and attributes carry the meaning

Tiles are `tile0`, `tile1`, rounds `round0`, `round1`, channels `channel0`, `channel1`. The index, the acquisition label, and the channel name live in `sp-ops:tile`, `sp-ops:axis`, and `sp-ops:channels`. Names contain no `=` and no joined keys such as `t0-r1`. Nesting expresses structure.

Why. A reader parses one JSON attribute instead of a naming grammar. The gap in the running example, cycle 6 missing from ISS, is `round5` with `value: 7`, and no name has to encode it.

Rejected. `t=0/r=1/c=2` names. Their meaning is only recoverable by parsing strings, and `=` is not a permitted character: RFC-8 ids must match `[a-zA-Z0-9-_.]+`, and OME-NGFF path names are restricted to alphanumerics, `-`, and `_`.

### D4. There is no fixation timepoint level

Cells fixed at different times are different wells or different plates, so the plate hierarchy already separates them. ISS rounds imaged on different days are still rounds. The axis `t` is reserved for elapsed time inside a live phenotyping acquisition.

Why. The [scallops](https://github.com/Genentech/scallops) pipeline, whose folder names motivated an earlier `t` level, uses `t` for the ISS cycle. Its registration module documents `_align_within_t` as "Align data within each time point (cycle)" and `align_image` as "Align an image within cycles (timepoints) and then between cycles", and its transform folders `iss-transforms-t0/A1/t=2` to `t=10` match the cycle labels 2 to 10. So `t` there is this specification's `round`.

Rejected. `t<i>` collections between tile and round. They duplicated well identity and made every table carry a `t` column.

### D5. Raw channels are separate images with their own coordinate systems

In `raw`, every channel of every round is its own multiscale. Alignment is a coordinate transformation until `processed`, where one aligned array is written.

Why. Cameras and filter sets shift channels relative to each other. Scallops aligns channels within a cycle to a reference channel before aligning cycles, which means raw channels cannot be assumed co-registered. Writing raw data as acquired keeps it reprocessable.

Rejected. One `(c, y, x)` raw array with a per-channel transform list. RFC-5 transforms apply to a whole array, not to one channel of it.

### D6. Axes are a subset of `round, t, c, z, y, x` in that order, singleton axes are omitted, and rounds are always stacked

A processed image has exactly the axes its data varies along, in the fixed order above. Multi-round modalities are always stacked along `round`, and `sp-ops:rounds` records the acquisition behind every slice. When channel identity differs between rounds, `sp-ops:channels` is one array per round and shorter rounds are padded with `null` channels.

Why. A `(1, 5, 2048, 2048)` array with a length-one `t` axis says nothing that `(5, 2048, 2048)` does not, and every consumer has to squeeze it. A fixed order lets readers index by position. One array per modality is what analysis code reads; the per-slice provenance is what a batch-effect analysis needs.

Rejected. A fixed `(round, t, c, z, y, x)` shape for every image. Also one image per round when channels differ, which forces every reader to handle two layouts. Also a writer-chosen axis order: if a use case shows a measurable gain from another order, this specification will consider allowing it then.

### D7. Registration anchors are declared, with the nuclear channel as the default

Channels align to the anchor channel, rounds register to the first round through it, and the phenotyping merged image registers to the ISS merged image through a channel both share, with an affine that includes the magnification ratio. Both keep their native pixel size. The anchor is the nuclear channel when one is present. `sp-ops:registration` records the anchor and reference explicitly, per round when they differ.

Why. The nuclear channel is the usual anchor, but it is not always there: phase or brightfield phenotyping has no nuclear stain, and some protocols omit DAPI from ISS cycles after the first. Scallops registers cycles to cycle 0 through one configurable channel.

Rejected. A fixed DAPI anchor. Also the largest box contained in every round as the resampling target, which changes the grid every time a round is added.

### D8. Derived data lives at the tile or merged collection it was computed on

Labels, points, shapes, and tables are children of the tile or merged collection whose image they were computed from. A table is linked by an edge to the element at its own level: a feature table to labels, `tile_features` to the `layout` of its modality, and `well_features` to a `wells` shapes element on the plate collection. Tables are processed data and MAY be split or merged and stored at other levels. Compartments that nest inside a cell (nuclei, mitochondria) are not nested in the hierarchy; their feature table carries a `cell_label` column instead.

Why. A reader opening one tile or merged collection gets everything computed on it. Labels reference their source image with the RFC-8 `labels.source` attribute, which is only meaningful next to that image.

Rejected. A `features/` tree keyed by compartment at the well level, apart from the labels it annotates. Also nesting compartment labels under cells, which breaks for multinucleated cells and for compartments that cross cell boundaries.

### D9. Relationships are an edge list on the lowest collection that contains both ends

`sp-ops:relationships` holds `{from, to, method, on, status}` edges. Key joins are `computed`; spatial joins may be `suggested` until a writer stores the join column. Edges are also how a table is linked to the element it describes, replacing the SpatialData `region`, `region_key`, `instance_key` triple.

Why. The Padua and Venice prototypes converge on a flat, JSON-serialisable list. Placing it on the lowest common collection keeps a tile's edges readable without opening the plate.

Rejected. A single plate-level list, which grows with every tile and forces a full read.

## Scallops vocabulary

| Scallops | This specification |
| --- | --- |
| `t`, timepoint, cycle | `round` |
| `c` | `c` |
| `_align_within_t`, reference channel | channel alignment within a round, `sp-ops:registration.anchor` |
| `_align_between_t`, target `t=0` | round registration, `sp-ops:registration.reference` |
| `iss-transforms-t0/A1/t=<n>` affine | `scene.coordinateTransformations` on the tile collection |
| `stitch.zarr` | `merged/image` |
| `segment.zarr/labels/A1-cell` | `pheno/merged/cells` |
| `features/cell/A1.parquet` | `pheno/merged/cells_features` |
| `features/nuclei/A1.parquet` | `pheno/merged/nuclei_features`, with `cell_label` |
| `reads/reads/A1.parquet`, `reads/bases/A1.parquet` | `iss/merged/reads` |
| `spot-detect.zarr/points/A1-peaks.parquet` | `iss/tiles/tile<i>/peaks` |
