# References

## Standards

- [OME-NGFF RFC-8, Collections and Extensibility](https://ngff.openmicroscopy.org/rfc/8/index.html). Draft, status D1. The `Node`, `Collection`, `Multiscale`, `Path`, and `Reference` interfaces, the `plate`, `well`, `acquisition`, `labels`, and `scene` attributes, and the prefixed extension naming scheme.
- [OME-NGFF RFC-5, Coordinate systems and transformations](https://ngff.openmicroscopy.org/rfc/5/index.html). Released in OME-NGFF 0.6. Named coordinate systems and the transformation types used here: `affine`, `translation`, `scale`, `byDimension`.
- [Zarr v3 core specification](https://zarr-specs.readthedocs.io/en/latest/v3/core/v3.0.html). The array format under every group in the store.
- [GeoParquet](https://geoparquet.org/) and [Apache Parquet](https://parquet.apache.org/docs/file-format/). The on-disk formats of shapes and points.
- [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119.txt). The meaning of MUST, SHOULD, and MAY, assumption A1 on the design decisions page.

## SpatialData

- [spatialdata documentation](https://spatialdata.scverse.org/en/stable/). The released API, including `rasterize`, `polygon_query`, and `join_spatialelement_table`, and the `region`, `region_key`, `instance_key` table annotation.
- [Hierarchical SpatialData](https://github.com/scverse/spatialdata/tree/vibecoded-experiment/hierarchical-spatialdata). Experimental branch. `/` in element names, sub-views by prefix, and the recursive reader.
- [Padua hackathon issue 6](https://github.com/scverse/2026_04_hackathon_padua/issues/6) and the [Venice relationships prototype](https://github.com/BiocCodingCollaborations/VeniceHackathon2026/tree/main/interoperability/relationships). The edge-list representation of element relationships and the `query` and `check_relationships` sketch. The Venice README describes its code as unverified and not for production use.

## Pipelines and data

- [scallops](https://github.com/Genentech/scallops), in particular [`scallops/registration`](https://github.com/Genentech/scallops/tree/main/scallops/registration), and its [preprint](https://www.biorxiv.org/content/10.64898/2026.05.22.727250v1.full). The source of the cycle labels, the label names, the `read` join key, and the evidence that its `t` axis is the ISS cycle.
- [scallops and Biohub OPS layout notes](https://hackmd.io/@D9GB-ZDcTQyFd7U5aMmk5g/r18soYBuzx). The pipeline output tree the scallops vocabulary table on the design decisions page maps from.
- `experimentC`, audited 2026-09-03. The dataset [](open-questions.md) is built from: one well, two fields of view, nine ISS rounds, one phenotyping round, and a 5738-guide library, delivered as Micro-Manager TIFF exports with no derived data. The plate identifier is withheld for the reason given below.
- `biohub_example`, audited 2026-09-03. The merged-only submission [](open-questions.md) is built from: three wells of one stitched image and twelve segmentations each, a 4211-guide library, 831587 barcode-assigned cells, and a YAML sidecar of experimental provenance. Delivered as an OME-NGFF 0.5 HCS plate with Parquet, CSV and YAML sidecars. The internal pipeline paths recorded in its metadata are not reproduced here.
- `experimentC_scallops`, audited 2026-09-03. `experimentC` after the scallops pipeline, and the source of everything on the `intermediate` stage: 10 stitched well images, a round-registered ISS stack, 39987 peaks, 15590 nine-base reads, five segmentations and 4706 cells of features. The elastix transform parameters it ships are the evidence for Q13. Local pipeline paths recorded in its Zarr metadata are not reproduced here.
- `cpg0021_sample`, audited 2026-09-03. A two-well subset of the public [cpg0021-periscope](https://github.com/broadinstitute/cellpainting-gallery) whole-genome screen, plate `CP186A` of `20200805_A549_WG_Screen`: 272 Nikon ND2 files over twelve ISS cycles and one phenotyping round, and an 82678-row guide table, with no derived data. It is the only delivery here whose raw images arrive in a vendor format with their acquisition metadata intact, and it is the source of everything on Q6, Q18–Q19, Q35–Q37, and Q49–Q51, and the second measurement of Q22.
- Public Biohub OPS submission, audited 2026-09-02. Source of the well set, pixel size, and library size. The plate identifier and bucket path are withheld because this repository is public.

## Bibliography

```{bibliography}
:all:
```
