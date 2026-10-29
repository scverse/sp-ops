"""Shared machinery for building sp-ops conformant OME-Zarr stores.

`rfc8` holds the metadata primitives and touches no I/O; `elements` writes the
four element kinds. See docs/layout.md and docs/extension.md for the spec these
implement, and docs/open-questions.md for where the datasets do not fit it.
"""
