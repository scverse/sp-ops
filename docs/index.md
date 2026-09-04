# sp-ops: a SpatialData specification for optical pooled screening data

```{note}
This is an experiment built during the [scverse cellpainting hackathon](https://github.com/scverse/2026_08_hackathon_cellpainting) in Berlin Buch, 2026. The content is manually designed, with AI used for formatting over several rounds of iteration. It is not ready for production and is intended for discussion and experimentation.
```

This specification lays out one optical pooled screening (OPS) screen as one OME-Zarr store that opens as one hierarchical [SpatialData](https://github.com/scverse/spatialdata) object. A screen holds plate collections, one per physical plate and processing stage. Each covers in situ sequencing (ISS) rounds and phenotyping rounds over the wells of the plate, imaged as tiles and stitched into a merged well image, together with the labels, points, and tables that link pixels to perturbations.

The store is described with [RFC-8](https://ngff.openmicroscopy.org/rfc/8/index.html) collections and [RFC-5](https://ngff.openmicroscopy.org/rfc/5/index.html) coordinate transformations. Both are drafts. The assumptions this implies are listed on the design decisions page.

```{toctree}
:maxdepth: 2

layout.md
features.md
joinable-components.md
design-decisions.md
extension.md
open-questions.md
store-audit.md
references.md
```

- [](layout.md). The hierarchy from plate to channel, the RFC-8 metadata at each level, registration, and the SpatialData view.
- [](features.md). Feature tables at cell, tile, and well granularity, and merged against split tables.
- [](joinable-components.md). The library, reads, peaks, labels, and feature tables, and the edges that join them.
- [](design-decisions.md). Assumptions, nine decisions with their rejected alternatives, and the mapping from scallops vocabulary.
- [](extension.md). The `sp-ops` attribute keys and node types, with one complete example.
- [](open-questions.md). The `experimentC`, `biohub_example`, `experimentC_scallops`, and `cpg0021_sample` datasets written as stores, and the fifty-one questions those exercises raised.
- [](store-audit.md). Ten further entries from reading the rebuilt `experimentC_scallops` and `biohub_example` stores back against the requirement text, none of which the validator tests.

Keywords MUST, SHOULD, and MAY follow [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119.txt), see assumption A1.
