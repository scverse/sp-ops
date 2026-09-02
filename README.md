# sp-ops

SpatialData specification for optical pooled screening (OPS) data.

The specification lives in `docs/` and builds with Sphinx.

```bash
uv sync --group docs
uv run make --directory docs html
open docs/_build/html/index.html
```

`uv run sphinx-autobuild docs docs/_build/html` serves a live-reloading copy while editing.
