# Overview

This page sets the scope of the sp-ops specification and the three status categories used on every page. It then lists the external specifications the sp-ops specification builds on, the axis notation, and the structure that every specification page shares. Acronyms are expanded at first use and collected in the [glossary](glossary.md). The names and numbers of the running example are fixed in the [design decisions](design-decisions.md#running-example). This page repeats only the few that explain the axis letters and the diagram.

## The specification covers one plate from pixels to perturbations

The subject is one optical pooled screening (OPS) plate. The plate holds wells, each well holds fields of view (FOV, called tiles), and each tile is imaged at several fixation timepoints. At each timepoint the tile is imaged once per in situ sequencing (ISS) cycle and once in a phenotypic round. ISS is also called sequencing by synthesis (SBS). The specification covers the following.

- The plate, its wells, and its acquisitions as Open Microscopy Environment Next-Generation File Format (OME-NGFF) 0.5 high-content screening (HCS) metadata. An OME-NGFF request for comments 8 (RFC-8) collection view sits alongside it (proposed) ([Hierarchy](hierarchy.md)).
- Tiles, the per-well `tiles` layout element, and the per-well `footprints` element ([Fields of view](fields-of-view.md)).
- ISS cycles and the phenotypic round as separate image elements. They are registered into one frame per tile and timepoint and resampled on a common area ([ISS rounds](iss-rounds.md), [Phenotypic rounds](phenotypic-rounds.md)).
- Label images, spot images, base calls, and cell bounding boxes as labels, images, points, and shapes ([ISS rounds](iss-rounds.md), [Phenotypic rounds](phenotypic-rounds.md), [Joinable components](joinable-components.md)).
- Feature tables at cell, FOV, and well granularity, each typed with the ngio table vocabulary, and the export to the OPS data standard's `cell_data.parquet` ([Features](features.md)).
- Reads, the perturbation library, and the edge list that records how elements join ([Joinable components](joinable-components.md)).
- The `sp-ops` extension prefix and its keys ([Extension](extension.md)).

## Four things are out of scope

- How registration, stitching, segmentation, spot detection, base calling, or feature extraction are computed. The specification defines only where their outputs live and how they join.
- Cross-timepoint registration, because different fixation timepoints are different fixed cells. A coordinate in the well frame locates an object on the plate but does not align cells across timepoints.
- New OME-NGFF primitives. The specification introduces no path type and no coordinate transformation type, only prefixed attribute keys and node types.
- The OPS data standard v0.1.0 files other than the image store, from `experimental_metadata.yaml` to `cell_data.parquet`, which keep their own schemas. This specification says only how `perturbation_library.csv` relates to the `library` table and how `cell_data.parquet` and `feature_definitions.csv` relate to the `cells` table.

## Every statement is normative, existing behaviour, or a proposal

Each page separates three kinds of statements and marks them as shown.

| Category | What it means | How it is marked |
| --- | --- | --- |
| Normative | A requirement of this specification | MUST, MUST NOT, SHOULD, SHOULD NOT, MAY in capitals, in the sense of RFC 2119 |
| Existing behaviour | What released software and released standards do today, namely the rows marked released in the dependency table below, chiefly OME-NGFF 0.5 HCS, spatialdata v0.8.0, and the ngio table specifications | Plain prose that names the software and its version; "probe-verified" marks a behaviour that was tested against the release |
| Proposal | Depends on unreleased work, namely OME-NGFF RFC-8 (collections), RFC-5 (coordinate transformations), hierarchical SpatialData, or element relationships | A `Status` note, an inline "(proposed)" tag, or a `# proposed API` comment on a code line, where API is an application programming interface |

The words MUST, SHOULD, and MAY carry their RFC 2119 meaning only when written in capitals. A normative sentence names what it binds. The subject is a writer (the software that produces a store), a reader, or a validator. It can also be a stored object such as an element, a column, or a metadata key. Where a page relies on a proposal, it says which unreleased dependency the proposal needs and what a spatialdata v0.8.0 user does instead today.

## Six released and four unreleased dependencies

The specification rests on released standards and software and on four pieces of unreleased work. The two released foundations have peer-reviewed descriptions. OME-Zarr, the OME-NGFF format stored in Zarr, is described in {cite}`moore2023omezarr`, and the SpatialData framework in {cite}`marconato2024spatialdata`. Versions below are the ones the source material states.

| Dependency | Version or status | Category | What this specification takes from it |
| --- | --- | --- | --- |
| [Zarr](https://zarr-specs.readthedocs.io/en/latest/v3/core/v3.0.html) | v3 | released | Every group and array in the store; `zarr.json` group metadata |
| [OME-NGFF](https://ngff.openmicroscopy.org/0.5/) with the [HCS layout](https://ngff.openmicroscopy.org/0.5/#hcs-layout) | 0.5, pinned by the OPS data standard v0.1.0 | released | `plate`, `well`, `multiscales`, and `labels` metadata; the [plate](https://ngff.openmicroscopy.org/specifications/dev/index.html#plate-metadata) and [well](https://ngff.openmicroscopy.org/specifications/dev/index.html#well-metadata) wording is quoted from the dev specification, which uses the same keys |
| [OME-NGFF RFC-8, collections](https://ngff.openmicroscopy.org/rfc/8/index.html#high-content-screening-hcs-metadata) | D1; "This proposal is early" | proposal | `collection` nodes, `Path` and `Reference`, HCS attributes with string ids, `labels`, and prefixed extension identifiers |
| [OME-NGFF RFC-5, coordinate transformations](https://ngff.openmicroscopy.org/rfc/index.html) | S4 (Update implementations); the document read states version 0.6.dev3, and its history lists 0.6.dev4 as published 2026-04-28 | proposal | Named coordinate systems, the `scene` attribute, and the `identity`, `scale`, `translation`, `affine`, and `byDimension` transformation types |
| [spatialdata](https://spatialdata.scverse.org/en/stable/) | v0.8.0 | released | Models, `TableModel.parse` with `region`, `region_key`, and `instance_key`, transformations, `rasterize`, `join_spatialelement_table`, and the on-disk element metadata |
| [Hierarchical SpatialData](https://raw.githubusercontent.com/LucaMarconato/spatialdata/refs/heads/vibecoded-experiment/hierarchical-spatialdata/slides-hierarchical-spatialdata.html) | experimental branch; "The API may evolve" | proposal | `/` in element names, `sdata["A/1"]` sub-views, the `elements=` constructor, and the tree printed representation (repr) |
| [ngio table specifications](https://biovisioncenter.github.io/ngio/stable/table_specs/overview/) | table specifications V1 | released | The five table types and the feature type vocabulary |
| GeoParquet, via [geopandas](https://geopandas.org/en/stable/) | as written by `GeoDataFrame.to_parquet` | released | The `shapes.parquet` file that spatialdata writes inside every shapes group |
| [Parquet](https://parquet.apache.org/docs/file-format/) | v2.6, pinned by the OPS data standard v0.1.0 | released | The `cell_data.parquet` export |
| Element relationships ([Padua issue 6](https://github.com/scverse/2026_04_hackathon_padua/issues/6), [Venice prototype](https://github.com/BiocCodingCollaborations/VeniceHackathon2026/tree/main/interoperability/relationships)) | hackathon prototypes; the Venice README marks the code unverified | proposal | The `from`, `to`, `method`, `params` edge shape and the `query()` and `check_relationships()` names |

:::{admonition} Status
:class: note
The four proposal rows are unreleased. RFC-8 is at status D1, and its own text says "This proposal is early." RFC-5 is at S4, which its status line calls "Update implementations". The hierarchical SpatialData branch and the relationships prototypes have no release. Every page marks what depends on them. The OME-NGFF 0.5 layout, mapping (a) of [design decision D2](design-decisions.md#d2-plates-and-wells-stay-valid-ome-ngff-05-the-rfc-8-view-is-a-sidecar), depends on none of them. Some MUST rules name RFC-8 nodes, such as `sp-ops:tileLayout` and `sp-ops:timepoint` in the [extension key registry](design-decisions.md#extension-key-registry). They bind only the RFC-8 view, which is itself a proposal.
:::

## Five letters name the axes on every page

The specification uses the letters `t`, `r`, `c`, `y`, and `x` in element names, in table columns, and in array shapes. Their meanings are fixed.

| Letter | Meaning | Where it appears | Is it a tensor axis? |
| --- | --- | --- | --- |
| `t` | Fixation timepoint. The values `2, 3, 4, 5, 7, 8, 9, 10` are folder labels from the scallops layout, not measured times | Element name component `t<index>`; `images.obs["t"]`; `sp-ops:timepoint` | No. Each `t` is a separate element, because different timepoints are different fixed cells |
| `r` | ISS cycle, one microscope pass that reads one barcode position | Element name component `r<index>`; `images.obs["r"]`, null for phenotypic rounds; `sp-ops:acquisitions[].r` | No. Each cycle is a separate element until registration, and a coordinate system, not an array, is shared afterwards |
| `c` | Channel | The first axis of every image, `(c, y, x)`; names from `sp-ops:channels`; `images.obs["c"]` when an element holds one channel | Yes, when every plane shares one pixel grid. Unaligned channels are separate `(1, y, x)` elements |
| `y`, `x` | Space, in micrometres after the multiscale `scale` | Every image, label, point, shape, and coordinate system | Yes. Order is `y` then `x`, matching spatialdata `Image2DModel` dims `(c, y, x)` |

Images are two-dimensional, a scope rule of this specification, so `z` is not used. The rule behind the last column is mechanical and comes from [design decision D4](design-decisions.md#d4-timepoints-and-cycles-are-separate-elements-only-aligned-channels-are-stacked). A varying quantity is a tensor axis only when it is `c` and its planes share one pixel grid. Everything else is a separate element, and the per-well `images` table records the value per element. The reason is existing behaviour. The spatialdata `Image2DModel` has dims `(c, y, x)` and no `t` or `r` axis. RFC-5 admits at most one `channel` or custom axis per image.

```text
A/1/f0/t2/iss/r2              # well A/1, tile f0, timepoint t=2, ISS cycle r=2
A/1/f0/t2/pheno               # same tile and timepoint, phenotypic round (no r)
(c, y, x) = (5, 2048, 2048)   # one ISS image, illustrative size; c names DAPI, A, G, C, T
scale = [1.0, 0.325, 0.325]   # along (c, y, x); y and x in micrometres per pixel, real value from the audited store
```

## Each data page shows the same views of the same data

The six pages from Hierarchy to Joinable components present their part of the plate in the same order. The order follows the author's outline. It asked every section for a file format example, an RFC-8 extension draft, and a SpatialData repr. It asked the ISS, phenotypic, and joinable components sections for API examples and a graph as well. The [Extension](extension.md) page is a key registry and uses its own order.

| View | Contents | Category |
| --- | --- | --- |
| On-disk layout | A directory tree of the OME-NGFF 0.5 HCS store with box-drawing characters and the `zarr.json` metadata, including the `sp-ops:` keys as siblings of `ome` | Normative rules on top of existing behaviour |
| RFC-8 collection view | The `collection.json` sidecar with `collection` nodes, `Reference` objects, and `sp-ops:` attributes | Proposal; depends on RFC-8, and on RFC-5 for `scene` |
| SpatialData view | The hierarchical repr with `/` in element names, and the flattened v0.8.0 names with `-` in place of `/` | Proposal for the repr; existing behaviour for the flat names |
| APIs | spatialdata v0.8.0 code that reads, joins, transforms, or resamples the elements; lines that need unreleased work carry `# proposed API` | Existing behaviour unless marked |
| Diagram | A mermaid graph of the coordinate transformations (ISS rounds, Phenotypic rounds) or of the join and spatial join edges (Joinable components); the Hierarchy page adds a graph of its containers and the Features page a graph of its tables and their regions | Same category as the view it illustrates |

Every page ends with a Sources section that lists each external resource it used. The [design decisions](design-decisions.md) page records why each choice was made and what was rejected; the specification pages state the result.

## One plate holds wells, tiles, timepoints, and the tables that join them

The diagram shows the running example from the plate down to the tables, with the elements of one tile at one timepoint. Arrows run from a container to its contents and from an element to the table that describes it. The last two arrows run from a table to the table it joins.

```{mermaid}
graph TD
  P["plate ops_plate.zarr"] --> W["well A/1"]
  P --> LIB["library (table)"]
  P --> WF["wells, well_features (MAY)"]
  W --> TL["tiles, footprints (shapes)"]
  W --> F0["tile f0"]
  F0 --> T2["timepoint t2 (registered frame A/1/f0/t2)"]
  subgraph T2G ["one tile at one timepoint"]
    T2 --> ISS["ISS cycles iss/r1 to iss/r10 (no r6)"]
    T2 --> PH["phenotypic round pheno"]
    ISS --> SP["spots/max, spots/std, spots/peaks, bases"]
    PH --> SEG["nuclear_seg, cell_seg, cell_bbox"]
  end
  TL --> IMG["images, fov_features (MAY) (tables)"]
  SEG --> CELLS["cells (table)"]
  SP --> READS["reads (table)"]
  CELLS --> LIB
  READS --> LIB
```

Reading the diagram from the top, a plate lists its wells and holds the perturbation `library`. A well holds the `tiles` layout, the `footprints` of every acquisition image, and one container per tile. A tile holds one container per fixation timepoint, which is also one registered coordinate system. In the RFC-8 view these containers are `collection` nodes (proposed). In the OME-NGFF 0.5 layout the well is flat, and the tile and timepoint are only components of each image name. Inside one timepoint container, the ISS cycles feed spot detection and base calling, and the phenotypic round feeds segmentation. The `cells` and `reads` tables gather the results per well and join to `library` by `barcode`.

## Sources

- [OME-NGFF 0.5](https://ngff.openmicroscopy.org/0.5/) and its [HCS layout](https://ngff.openmicroscopy.org/0.5/#hcs-layout): the released version this specification pins for the image store.
- [OME-NGFF dev specification, plate metadata](https://ngff.openmicroscopy.org/specifications/dev/index.html#plate-metadata) and [well metadata](https://ngff.openmicroscopy.org/specifications/dev/index.html#well-metadata): the plate and well wording, using the same keys as 0.5.
- [OME-NGFF RFC-8: Collections and Extensibility](https://ngff.openmicroscopy.org/rfc/8/index.html#high-content-screening-hcs-metadata): collection nodes, references, HCS attributes, and the prefixed extension naming scheme; status D1.
- [OME-NGFF RFC index](https://ngff.openmicroscopy.org/rfc/index.html): entry point for RFC-5, coordinate systems and transformations; status S4. The RFC-5 text carries no URL of its own in the source material.
- [OME-NGFF specification release 0.6.dev3](https://github.com/ome/ngff-spec/releases/tag/0.6.dev3): the RFC-5 document version read for this specification; its history table lists 0.6.dev4 as published 2026-04-28.
- [Zarr v3 core specification](https://zarr-specs.readthedocs.io/en/latest/v3/core/v3.0.html): the storage layer; version pinned by the OPS data standard v0.1.0.
- [Apache Parquet file format](https://parquet.apache.org/docs/file-format/): the format of the `cell_data.parquet` export; version 2.6 pinned by the OPS data standard v0.1.0.
- [geopandas documentation](https://geopandas.org/en/stable/): `GeoDataFrame.to_parquet`, which writes the GeoParquet file inside every spatialdata shapes group.
- [spatialdata documentation](https://spatialdata.scverse.org/en/stable/): the v0.8.0 models and public API named on every page.
- [Hierarchical SpatialData slides](https://raw.githubusercontent.com/LucaMarconato/spatialdata/refs/heads/vibecoded-experiment/hierarchical-spatialdata/slides-hierarchical-spatialdata.html): `/` in element names, sub-views, `elements=` constructor, tree repr; experimental.
- [ngio table specifications](https://biovisioncenter.github.io/ngio/stable/table_specs/overview/): `generic_table`, `roi_table`, `masking_roi_table`, `feature_table`, `condition_table`, each at V1.
- [Padua hackathon issue 6](https://github.com/scverse/2026_04_hackathon_padua/issues/6) and the [Venice hackathon relationships prototype](https://github.com/BiocCodingCollaborations/VeniceHackathon2026/tree/main/interoperability/relationships): the element relationships prototypes.
- [scallops and Biohub OPS layout (HackMD)](https://hackmd.io/@D9GB-ZDcTQyFd7U5aMmk5g/r18soYBuzx): the pipeline output layout that supplies the `t` folder labels and the ISS cycle set.
- Chan Zuckerberg Initiative (CZI) OPS data standard v0.1.0 (draft): `cell_data.parquet`, `perturbation_library.csv`, `feature_definitions.csv`, `experimental_metadata.yaml`, and the pinned Zarr, OME-NGFF, and Parquet versions. No public URL appears in the source material.
- [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119.txt): the meaning of MUST, SHOULD, and MAY.
- The OME-Zarr and SpatialData papers cited above: full entries in the [bibliography](references.md#bibliography) of the references page.
