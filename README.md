# sp-ops

> **Disclaimer:** This is an experiment built during the [scverse proteomics hackathon](https://github.com/scverse/2026_08_hackathon_cellpainting) in Berlin Buch, 2026. The content is manually designed, with AI used for formatting over several rounds of iteration. It is not ready for production and is intended for discussion and experimentation.

SpatialData specification for optical pooled screening (OPS) data.

The specification lives in `docs/` and builds with Sphinx.

```bash
uv sync --group docs
uv run make --directory docs html
open docs/_build/html/index.html
```

`uv run sphinx-autobuild docs docs/_build/html` serves a live-reloading copy while editing.
