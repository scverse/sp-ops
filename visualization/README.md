# Visualizing sp-ops stores

Two graphs, read directly out of an sp-ops-conformant store's `zarr.json` metadata:

- **the relationships graph** -- every `sp-ops:relationships` edge (docs/extension.md,
  docs/joinable-components.md): which table, image, or labels element joins to which, by
  what method, and whether the join is `computed` or only `suggested`.
- **the transformations graph** -- every coordinate transformation that places an element
  into a shared frame. This is the group-level `scene` RFC-5 mechanism
  (docs/layout.md#registration) where a store writes it, and, since none of the example
  stores place tiles into a shared `well` frame that way yet, it also picks up the
  per-multiscale `coordinateSystems` + base pyramid level `coordinateTransformations` every
  image and labels node already carries -- e.g. a merged image mapping into its declared
  `well` coordinate system by a `scale` then a `translation`.

Reading is done with the standard library only (`json`, walking `zarr.json` files by hand),
so this runs against any conformant store without needing `zarr`, `ome-zarr`, or the
experimental `spatialdata` branch `examples/` depends on.

A reference that does not resolve to a real node in the store (a dangling `sp-ops:relationships`
edge, for instance) is not silently dropped: it is added to the graph as a distinctly
coloured "dangling" node, since that is itself a finding worth seeing rather than a bug to
hide -- see docs/open-questions.md Q16 and Q35 for real examples of a reference this shape
would catch.

## Running it

```bash
uv sync --group viz
uv run python visualization/render_graphs.py \
    --store /path/to/some_store.zarr \
    --out-dir visualization/output
```

Writes, per graph:

- `<name>.svg` -- static, via the system Graphviz `dot` binary (`brew install graphviz` /
  `apt install graphviz`; skipped with a warning, not an error, if `dot` is not on PATH).
- `<name>.html` -- self-contained and interactive (drag, zoom, hover an edge for its full
  `sp-ops:relationships`/transform payload), using [vis-network](https://visjs.github.io/vis-network/)
  loaded from a CDN. Open it in any browser, no server needed.

`--graphs relationships` or `--graphs transformations` renders one instead of both;
`--direction TB` lays out top-to-bottom instead of left-to-right.

## Prior art

The [Venice hackathon relationships prototype](https://github.com/BiocCodingCollaborations/VeniceHackathon2026/tree/main/interoperability/relationships)
(also cited in docs/references.md) explored the same idea -- an interactive graph of element
relationships -- against a different, ad hoc `sdata.attrs["element_relationships"]` model
rather than sp-ops's `sp-ops:relationships` edge list, and its own README marks it
AI-generated, unreviewed, and not to be reused as-is. The code here is a fresh
implementation against the actual sp-ops/RFC-8 on-disk schema, not a port of it.
