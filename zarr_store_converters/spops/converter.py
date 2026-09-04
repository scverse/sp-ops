"""The shared skeleton of a store builder.

Deliberately thin. The datasets do not share a traversal -- one loops modalities
and stages, the other is straight-line over a single well -- so forcing a
`for well: for modality:` template on both would mean hooks that return nothing
for most of the grid. What they do share is the three-step dance every level of
the hierarchy performs: create the group, build the children (which need the
group), then write the parent's `ome` with those children as its `nodes`. That is
what `collection()` captures, and the named helpers below are three lines each
over it.

The element writers are re-exposed as methods only to bind the per-dataset
pixel size, chunking and coordinate-system id once instead of at every call.
"""

from __future__ import annotations

import abc
import logging
from collections.abc import Callable, Iterable, Sequence
from pathlib import Path
from typing import ClassVar

import zarr

from . import elements
from .rfc8 import (SPEC_VERSION, node, relationships, set_ome, well_attribute)

log = logging.getLogger("spops")

# A callable rather than a list, so a child can be written into the group its
# parent just created.
Children = Callable[[zarr.Group], list[dict]]


def _no_children(group: zarr.Group) -> list[dict]:
    return []


class ScreenConverter(abc.ABC):
    """One screen, written as one store whose root is an RFC-8 collection."""

    name: ClassVar[str]
    plate_id: ClassVar[str]
    pixel_size_um: ClassVar[float]
    # A default only. Both datasets vary levels within one store, so every
    # element writer takes an override.
    pyramid_levels: ClassVar[int] = 3
    cs_id: ClassVar[str] = "px"
    max_chunk: ClassVar[int] = 512
    shard_factor: ClassVar[int | None] = None

    def __init__(self, sources: dict[str, Path], out: Path) -> None:
        self.sources = {k: Path(v).expanduser() for k, v in sources.items()}
        self.out = Path(out).expanduser()
        self.root: zarr.Group

    # ------------------------------------------------------------------ build

    def build(self) -> None:
        self.load()
        self.root = zarr.create_group(str(self.out), zarr_format=3, overwrite=True)
        nodes = list(self.write_screen_elements(self.root))
        nodes += list(self.write_plates())
        set_ome(self.root, "collection", self.name,
                attributes={"sp-ops:spec": {"version": SPEC_VERSION},
                            **self.screen_attributes()},
                nodes=nodes)
        log.info("wrote %s", self.out)

    # ------------------------------------------------------------------ hooks

    @abc.abstractmethod
    def load(self) -> None:
        """Open the sources and read whatever metadata the build needs."""

    @abc.abstractmethod
    def write_plates(self) -> Iterable[dict]:
        """Write every plate collection; yield one node per plate."""

    def write_screen_elements(self, root: zarr.Group) -> Iterable[dict]:
        """Screen level elements, such as the library table."""
        return []

    def screen_attributes(self) -> dict:
        """Extra attributes on the screen collection, e.g. relationships."""
        return {}

    # -------------------------------------------------------------- structure

    def group(self, parent: zarr.Group | None, name: str) -> zarr.Group:
        """Create or reuse `name` under `parent`, one segment at a time.

        A well is named `A/1` and so spans two path segments; the intermediate
        row group is neither an RFC-8 node nor an sp-ops one, it is just a path
        segment. See Q14.
        """
        g = self.root if parent is None else parent
        for segment in name.split("/"):
            g = g.require_group(segment)
        return g

    def collection(self, parent: zarr.Group | None, name: str, *,
                   attributes: dict | None = None,
                   children: Children = _no_children,
                   node_name: str | None = None,
                   node_attributes: dict | None = None,
                   element_id: str | None = None) -> dict:
        """One RFC-8 collection, its children, and the node its parent lists it as.

        `children` may legitimately return an empty list: an intermediate stage
        has tile collections with no per-tile product, and dropping or padding
        them would erase a documented finding (Q33).
        """
        group = self.group(parent, name)
        child_nodes = children(group)
        set_ome(group, "collection", node_name or name,
                attributes=attributes, nodes=child_nodes)
        return node("collection", node_name or name, f"./{name}",
                    attributes=node_attributes, element_id=element_id)

    def plate(self, name: str, *, stage: str, rows: Sequence[str],
              columns: Sequence[str], acquisitions: list[dict],
              children: Children, attributes: dict | None = None,
              edges: list[dict] | None = None,
              with_names: bool = True) -> dict:
        """A plate collection: one physical plate at one processing stage.

        `rows` and `columns` are what the plate declares, which is not
        necessarily what has data -- a delivery may carry pixels for one well of
        three. See Q4. `with_names` is a per-dataset choice because RFC-8 makes
        a row's `name` optional and the two stores differ on it.
        """
        def axis(ids: Sequence[str]) -> list[dict]:
            return [{"id": i, "name": i} if with_names else {"id": i} for i in ids]

        attrs = {
            "sp-ops:plate": {"id": self.plate_id},
            "sp-ops:stage": stage,
            "plate": {
                "rows": axis(rows),
                "columns": axis(columns),
                "acquisitions": acquisitions,
            },
        }
        if edges is not None:
            attrs["sp-ops:relationships"] = relationships(edges)
        attrs.update(attributes or {})
        return self.collection(
            None, name, attributes=attrs, children=children,
            node_attributes={"sp-ops:plate": {"id": self.plate_id},
                             "sp-ops:stage": stage})

    def well(self, plate: zarr.Group, row: str, column: str, *,
             children: Children, scene: dict | None = None,
             edges: list[dict] | None = None) -> dict:
        """A well collection. The stitching transforms live here, not on the
        modality -- extension.md's complete example is the one that works, and
        the stores follow it. See Q15."""
        attrs = dict(well_attribute(row, column))
        if scene is not None:
            attrs["scene"] = scene
        if edges is not None:
            attrs["sp-ops:relationships"] = relationships(edges)
        return self.collection(plate, f"{row}/{column}", attributes=attrs,
                               children=children,
                               node_attributes=well_attribute(row, column))

    def modality(self, well: zarr.Group, name: str, *, children: Children,
                 acquisition: str | None = None) -> dict:
        """An `iss` or `pheno` collection."""
        attrs: dict = {"sp-ops:modality": name}
        if acquisition is not None:
            attrs["acquisition"] = {"id": acquisition}
        return self.collection(well, name, attributes=attrs, children=children)

    def merged(self, modality: zarr.Group, *, source: list[dict],
               children: Children, edges: list[dict] | None = None) -> dict:
        """The stitched well image and what was computed on it.

        `source` is written even when empty: a merged-only delivery has no tiles
        to name, and `sp-ops:merged.source` is a MUST, so an empty list is the
        honest value and is what raises the advisory. Omitting the key instead
        would turn that advisory into a failure. See Q19.
        """
        attrs: dict = {"sp-ops:merged": {"source": source}}
        if edges is not None:
            attrs["sp-ops:relationships"] = relationships(edges)
        return self.collection(modality, "merged", attributes=attrs,
                               children=children)

    def tiles(self, modality: zarr.Group, *, layout_id: str,
              children: Children, edges: list[dict] | None = None) -> dict:
        """The tile layout and one collection per field of view."""
        attrs: dict = {"sp-ops:tiles": {"layout": {"id": layout_id}}}
        if edges is not None:
            attrs["sp-ops:relationships"] = relationships(edges)
        return self.collection(modality, "tiles", attributes=attrs,
                               children=children)

    def tile(self, tiles: zarr.Group, group_name: str, *, index: int,
             children: Children = _no_children,
             extra_attributes: dict | None = None,
             node_attributes: dict | None = None,
             element_id: str | None = None) -> dict:
        """One field of view.

        The group name is not derived from the index: a delivery may name its
        tiles by acquisition site while `sp-ops:tile.index` is the position in
        the modality's own grid. See Q5. `extra_attributes` carries whatever a
        delivery records beside the index, such as that site id.

        `children` may return nothing. A stitch stage has no per-tile product,
        so its tile collections are empty, and that is a finding rather than
        something to pad or drop. See Q33.
        """
        attrs: dict = {"sp-ops:tile": {"index": index}}
        attrs.update(extra_attributes or {})
        return self.collection(tiles, group_name, attributes=attrs,
                               children=children,
                               node_attributes=node_attributes,
                               element_id=element_id)

    # ---------------------------------------------------------------- elements

    def _ms(self, parent: zarr.Group, name: str, *, labels: bool, **kw) -> dict:
        kw.setdefault("pixel_size_um", self.pixel_size_um)
        kw.setdefault("cs_id", self.cs_id)
        kw.setdefault("levels", self.pyramid_levels)
        kw.setdefault("max_chunk", self.max_chunk)
        kw.setdefault("shard_factor", self.shard_factor)
        return elements.write_multiscale(parent, name, labels=labels, **kw)

    def image(self, parent: zarr.Group, name: str, **kw) -> dict:
        return self._ms(parent, name, labels=False, **kw)

    def labels(self, parent: zarr.Group, name: str, **kw) -> dict:
        return self._ms(parent, name, labels=True, **kw)

    def table(self, parent: zarr.Group, name: str, obs, **kw) -> dict:
        return elements.write_table(parent, name, obs, **kw)

    def points(self, parent: zarr.Group, name: str, df, **kw) -> dict:
        return elements.write_points(parent, name, df, **kw)

    def shapes(self, parent: zarr.Group, name: str, gdf, **kw) -> dict:
        return elements.write_shapes(parent, name, gdf, **kw)
