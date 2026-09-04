# sp-ops

> **Disclaimer:** This is an experiment built during the [scverse cellpainting hackathon](https://github.com/scverse/2026_08_hackathon_cellpainting) in Berlin Buch, 2026. The content is manually designed, with AI used for formatting over several rounds of iteration. It is not ready for production and is intended for discussion and experimentation.

SpatialData specification for optical pooled screening (OPS) data.

The specification lives in `docs/` and builds with Sphinx.

```bash
uv sync --group docs
uv run make --directory docs html
open docs/_build/html/index.html
```

`uv run sphinx-autobuild docs docs/_build/html` serves a live-reloading copy while editing.

A napari reader plugin for these stores is being built in `napari_plugin/`. See `napari_plugin/README.md` for install and status.

## Examples

The spec's `raw`/`processed` reference stores are runnable against an experimental
`spatialdata` branch that implements RFC-8 collection reading, `round`/`t` axes, and
`sp-ops:relationships`. See [`examples/`](examples/):

- [`try_sp_ops_rfc8.py`](examples/try_sp_ops_rfc8.py) reads both example stores and exercises
  the relationships and axis support, with its captured output alongside it in
  [`try_sp_ops_rfc8_output.txt`](examples/try_sp_ops_rfc8_output.txt).
- [`try_napari.py`](examples/try_napari.py) opens one of the stores in a real, interactive
  [napari](https://napari.org) window via
  [napari-spatialdata](https://github.com/scverse/napari-spatialdata).
