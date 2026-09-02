# References

This page lists every external resource the sp-ops specification cites, grouped by kind, with one line on what each one contributes. It covers every link in the author's draft and every source the design record used. The assay acronyms used below are optical pooled screening (OPS) and in situ sequencing (ISS). The format acronyms are high-content screening (HCS), Open Microscopy Environment (OME), Next-Generation File Format (NGFF), and request for comments (RFC). Items that depend on unreleased work are marked "(proposed)".

:::{admonition} Status
:class: note
Released standards are OME-NGFF 0.5 and Zarr v3. RFC-8 (status D1, an early draft) and RFC-5 (status S4, version 0.6.dev3) are proposals of the OME-NGFF community. The hierarchical SpatialData slides and the two hackathon relationship prototypes are unreleased design explorations. The Venice README states that its code is "AI-generated, unverified, and must not be used in production". The Chan Zuckerberg Initiative (CZI) OPS data standard v0.1.0 carries the document status Draft; this specification treats its field names as fixed inputs, not as a released standard.
:::

## Standards split into released versions and RFC proposals

### OME-NGFF 0.5 is released; RFC-5 and RFC-8 are proposals

- [OME-NGFF 0.5](https://ngff.openmicroscopy.org/0.5/): the released version of the format that the OPS data standard pins for the image store.
- [OME-NGFF 0.5 HCS layout](https://ngff.openmicroscopy.org/0.5/#hcs-layout): the plate, well, and field of view directory hierarchy that the OPS data standard requires for the image store.
- [OME-NGFF dev specification, plate metadata](https://ngff.openmicroscopy.org/specifications/dev/index.html#plate-metadata): the `plate` object with `acquisitions`, `columns`, `rows`, `wells`, `field_count`, and `name`, with the two-acquisition example; 0.5 uses the same keys.
- [OME-NGFF dev specification, well metadata](https://ngff.openmicroscopy.org/specifications/dev/index.html#well-metadata): the `well.images` array with `path` and `acquisition`, and the rule that a path MUST NOT contain `/`.
- [OME-NGFF RFC-8, HCS metadata](https://ngff.openmicroscopy.org/rfc/8/index.html#high-content-screening-hcs-metadata) (proposed): the `Node`, `Collection`, `Path`, and `Reference` interfaces and the prefixed extension naming scheme. It also gives the `scene` and `labels` attributes, string-id plate and well attributes, and the wide and tall well examples.
- [OME-NGFF RFC index](https://ngff.openmicroscopy.org/rfc/index.html): the entry point for RFC-5 (proposed). RFC-5 defines named coordinate systems, scene storage, and eleven transformation types: `identity`, `mapAxis`, `translation`, `scale`, `affine`, `rotation`, `sequence`, `displacements`, `coordinates`, `bijection`, and `byDimension`.
- [OME-NGFF specification release 0.6.dev3](https://github.com/ome/ngff-spec/releases/tag/0.6.dev3): the RFC-5 document version read for this specification, cited on the overview page; its history table lists 0.6.dev4 as published 2026-04-28.

### Zarr v3, Parquet, ngio tables, and RFC 2119 are released

- [Zarr v3 core specification](https://zarr-specs.readthedocs.io/en/latest/v3/core/v3.0.html): the chunked array format under OME-NGFF 0.5, with `zarr.json` metadata and `zarr_format` 3.
- [Apache Parquet file format](https://parquet.apache.org/docs/file-format/): the columnar table format that the OPS data standard requires for `cell_data.parquet` and that scallops uses for features, reads, and bases.
- [ngio table specifications](https://biovisioncenter.github.io/ngio/stable/table_specs/overview/): the table types `generic_table`, `roi_table`, `masking_roi_table`, `feature_table`, and `condition_table`, their group attributes, required columns, and the feature type vocabulary.
- [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119.txt): the meaning of MUST, SHOULD, and MAY in this specification and in the OPS data standard.

## spatialdata v0.8.0 and its libraries supply the in-memory model

- [spatialdata documentation](https://spatialdata.scverse.org/en/stable/): the v0.8.0 public application programming interface (API) used in the examples, including `rasterize`, `transform`, `set_transformation`, `get_transformation`, `get_transformation_between_coordinate_systems`, `join_spatialelement_table`, `filter_by_table_query`, and `TableModel.parse`.
- [spatialdata tables tutorial](https://spatialdata.scverse.org/en/stable/tutorials/notebooks/notebooks/examples/tables.html): the `region`, `region_key`, `instance_key` model by which a table annotates labels or shapes.
- [anndata documentation](https://anndata.readthedocs.io): the `X`, `obs`, `var`, `uns`, `obsm`, and `obsp` slots that every spatialdata table carries.
- [geopandas documentation](https://geopandas.org/en/stable/): the GeoDataFrame behind spatialdata shapes elements and the `read_parquet` call that opens their GeoParquet files.
- [annsel documentation](https://annsel.readthedocs.io/en/latest/): the package whose `Predicates` type spatialdata v0.8.0 imports for the `obs_expr` and `x_expr` arguments of `filter_by_table_query`, cited on the features page.

## The prototypes and discussions are unreleased

- [Hierarchical SpatialData slides](https://raw.githubusercontent.com/LucaMarconato/spatialdata/refs/heads/vibecoded-experiment/hierarchical-spatialdata/slides-hierarchical-spatialdata.html) (proposed): `/` in element names, `sdata["prefix"]` sub-views, the `elements=` constructor, the tree repr, and the flat Zarr layout read through `spatialdata_attrs.element_type`.
- [Padua hackathon issue 6](https://github.com/scverse/2026_04_hackathon_padua/issues/6) (proposed): the design discussion on linking tables and spatial elements and the `spatialdata_elements_graph` prototype with `from`, `to`, `method`, and `params`.
- [scverse project view of Padua issue 6](https://github.com/orgs/scverse/projects/70/views/1?reload=1&pane=issue&itemId=169148807&issue=scverse%7C2026_04_hackathon_padua%7C6): the same issue as tracked on the scverse project board, linked from the author's draft.
- [Venice hackathon relationships prototype](https://github.com/BiocCodingCollaborations/VeniceHackathon2026/tree/main/interoperability/relationships) (proposed): `element_relationships` groups with `join_strategy` values `index`, `value`, or a column name, `sjoin_suggestions`, and the `query()` and `check_relationships()` API sketch.
- [VeniceInterop pull request 2](https://github.com/HelenaLC/VeniceInterop/pull/2): the hackathon pull request in which the Venice prototype was written, cited by its README.

## Two real datasets and one draft standard anchor the running example

- [scallops and Biohub OPS layout (HackMD)](https://hackmd.io/@D9GB-ZDcTQyFd7U5aMmk5g/r18soYBuzx): the real OPS pipeline output for well `A1`. It shows ISS cycle files, `t=` transform folders, per-compartment features with `-objects.parquet` bounding boxes, and `segment.zarr` labels. It also shows spot detection images and peaks, and reads and bases joined by the uint64 `read` column.
- CZI OPS data standard, version 0.1.0 (document status Draft), and the `ops-schema-validator` 0.1.0 used in the conformance check. It defines `cell_data.parquet` (`cell_uid`, `perturbation_id`), `perturbation_library.csv` (`barcode`, `perturbation_id`, `role`, `control_type`), and requires an OME-NGFF 0.5 HCS image store. No public URL appears in the source material, so none is given here.
- Public Biohub OPS submission, audited 2026-09-02 against the standard above. It is an OME-NGFF 0.5 HCS plate with wells `A/1` to `A/3` and one stitched field per well; its channel count, pixel size, and array shape are tabulated in the [running example](design-decisions.md#running-example). Its label groups, 11 to 12 per field, include `nuclear_seg`, `cell_seg`, `gfp_seg`, `iss_gene_image`, and `grid_overlay`. The bucket path and plate identifier are withheld because this repository is public, as the design record requires.

## The draft itself is hosted on GitHub

- [sp-ops on GitHub](https://github.com/scverse/sp-ops): the public repository that hosts this draft, its Sphinx sources, and its issue tracker, linked from the index page.

## Bibliography

The two peer-reviewed papers behind the released dependencies. The [overview page](overview.md#six-released-and-four-unreleased-dependencies) cites both where it introduces OME-Zarr and SpatialData; the entries come from `references.bib`.

```{bibliography}
:all:
```

## Sources

Every list on this page is a source of this specification. The URLs are taken from the author's draft and from the source files; a resource with no public URL in the source material is listed without a link.
