# sp-ops: a SpatialData specification for optical pooled screening data

Optical pooled screening (OPS) combines a pooled clustered regularly interspaced short palindromic repeats (CRISPR) perturbation library with microscopy. Cells in a well carry guide RNAs, and a barcode in each guide identifies the perturbation. The barcode is read in place by in situ sequencing (ISS), also called sequencing by synthesis (SBS). Each sequencing cycle images one position of the barcode. It uses up to four base channels (A, G, C, T) plus a nuclear stain such as 4′,6-diamidino-2-phenylindole (DAPI). A separate phenotypic round images the same cells with morphological stains. Base calling then gives every cell a perturbation, and segmentation and feature extraction give it a set of measurements.

This specification defines how one OPS plate is stored on disk and how it appears in memory as a spatialdata object. On disk the plate is an Open Microscopy Environment Next-Generation File Format (OME-NGFF) 0.5 high-content screening (HCS) plate on Zarr v3. Points, shapes, and tables extend it. In memory it is one `SpatialData` object. Element names follow the plate, well, tile, and timepoint hierarchy. They are joined by `/` on the experimental hierarchical SpatialData branch (proposed), or by `-` in spatialdata v0.8.0. The pages cover the plate and well hierarchy, fields of view (FOV, also called tiles), ISS rounds, and phenotypic rounds. They then cover registration and resampling, feature tables, joinable components, and the `sp-ops` extension keys. Every page uses the same running example, well `A/1` of a plate stored as `ops_plate.zarr`, whose names and numbers are fixed in the [design decisions](design-decisions.md#running-example).

This document is a draft for review, version `0.1.0-draft`. It separates normative requirements (MUST, SHOULD, MAY) from the existing behaviour of released software and from proposals that depend on unreleased work. The unreleased work is OME-NGFF request for comments 8 (RFC-8, collections), RFC-5 (coordinate transformations), hierarchical SpatialData, and element relationships. Proposals carry a Status note or a "(proposed)" tag. Issues and pull requests are welcome on the [GitHub repository](https://github.com/scverse/sp-ops). Start with the [Overview](overview.md), then read the pages below in order.

## Eight pages cover the plate from the overview to the extension keys

````{grid} 1 2 2 3
:gutter: 3

```{grid-item-card} Overview
:link: overview
:link-type: doc

Scope, the three status categories (normative, existing behaviour, proposed), the released and unreleased dependencies, the axis letters, and the views every data page shares.
```

```{grid-item-card} Hierarchy
:link: hierarchy
:link-type: doc

Plate, wells, and acquisitions as OME-NGFF 0.5 HCS metadata, with the RFC-8 collection view as a sidecar document.
```

```{grid-item-card} Fields of view
:link: fields-of-view
:link-type: doc

Tiles as collections of per-timepoint collections (proposed, RFC-8), the `tiles` layout element, and the `footprints` element that tables annotate.
```

```{grid-item-card} ISS rounds
:link: iss-rounds
:link-type: doc

One image per sequencing cycle, registration to the nuclear channel of the anchor cycle, and resampling on the common area.
```

```{grid-item-card} Phenotypic rounds
:link: phenotypic-rounds
:link-type: doc

One `(c, y, x)` image per timepoint, aligned into the same registered frame as the ISS cycles of that timepoint.
```

```{grid-item-card} Features
:link: features
:link-type: doc

Cell, field of view, and well feature tables, and how the OPS `cell_data.parquet` export is derived from them.
```

```{grid-item-card} Joinable components
:link: joinable-components
:link-type: doc

Reads, base calls, bounding boxes, the perturbation library, and the `sp-ops:relationships` edge list that joins them.
```

```{grid-item-card} Extension
:link: extension
:link-type: doc

The `sp-ops` prefix, its nine attribute keys, its three node types, and where each lives in the 0.5 and RFC-8 layouts.
```
````

## Three appendix pages record the decisions, terms, and sources

````{grid} 1 2 2 3
:gutter: 3

```{grid-item-card} Design decisions
:link: design-decisions
:link-type: doc

The running example, the twelve decisions D1 to D12 with rationale and rejected alternatives, and the extension key registry. When a page and this page disagree, this page wins.
```

```{grid-item-card} Glossary
:link: glossary
:link-type: doc

Domain, geometry, table, format, and container terms, each labelled existing behaviour, this specification, or proposed, with the running-example object it names.
```

```{grid-item-card} References
:link: references
:link-type: doc

Every external resource the specification cites, grouped by kind, with one line on what each one contributes and its release status.
```
````

```{toctree}
:maxdepth: 2
:caption: Specification

overview
hierarchy
fields-of-view
iss-rounds
phenotypic-rounds
features
joinable-components
extension
```

```{toctree}
:maxdepth: 1
:caption: Appendix

design-decisions
glossary
references
```

## Sources

- [OME-NGFF 0.5](https://ngff.openmicroscopy.org/0.5/) and its [HCS layout](https://ngff.openmicroscopy.org/0.5/#hcs-layout): the released image format that the on-disk layout follows.
- [OME-NGFF RFC-8: Collections and Extensibility](https://ngff.openmicroscopy.org/rfc/8/index.html#high-content-screening-hcs-metadata): the collection view named on this page; status D1.
- [OME-NGFF RFC index](https://ngff.openmicroscopy.org/rfc/index.html): entry point for RFC-5, coordinate systems and transformations; status S4. The RFC-5 text carries no URL of its own in the source material.
- [Zarr v3 core specification](https://zarr-specs.readthedocs.io/en/latest/v3/core/v3.0.html): the storage format under OME-NGFF 0.5.
- [spatialdata documentation](https://spatialdata.scverse.org/en/stable/): the in-memory object and the v0.8.0 application programming interface (API) used in the examples.
- [Hierarchical SpatialData slides](https://raw.githubusercontent.com/LucaMarconato/spatialdata/refs/heads/vibecoded-experiment/hierarchical-spatialdata/slides-hierarchical-spatialdata.html): the experimental branch behind the `/` element names.
- [Padua hackathon issue 6](https://github.com/scverse/2026_04_hackathon_padua/issues/6) and the [Venice hackathon relationships prototype](https://github.com/BiocCodingCollaborations/VeniceHackathon2026/tree/main/interoperability/relationships): the element relationships prototypes behind `sp-ops:relationships`.
- Chan Zuckerberg Initiative (CZI) OPS data standard v0.1.0 (draft): `cell_data.parquet` and the pinned OME-NGFF 0.5 and Zarr v3 versions. No public URL appears in the source material.
- [sp-ops on GitHub](https://github.com/scverse/sp-ops): the repository that hosts this draft and its issue tracker.
