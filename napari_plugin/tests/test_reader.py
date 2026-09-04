from napari_ome_zarr._reader import napari_get_reader as upstream_get_reader
from npe2 import PluginManager

from napari_sp_ops import napari_get_reader


def test_manifest_registers_a_directory_reader_for_zarr():
    manager = PluginManager.instance()
    manager.discover()
    manifest = manager.get_manifest("napari-sp-ops")
    readers = manifest.contributions.readers
    assert len(readers) == 1
    assert "*.zarr" in readers[0].filename_patterns
    assert readers[0].accepts_directories


def test_declines_paths_that_are_not_zarr_groups(tmp_path):
    assert napari_get_reader(str(tmp_path / "missing.zarr")) is None
    assert napari_get_reader(str(tmp_path)) is None
    (tmp_path / "plain.txt").write_text("x")
    assert napari_get_reader(str(tmp_path / "plain.txt")) is None


def test_delegates_a_multiscale_group_to_napari_ome_zarr(synthetic_screen):
    path = str(synthetic_screen.image)
    ours = napari_get_reader(path)(path)
    theirs = upstream_get_reader(path)(path)
    assert len(ours) == len(theirs) == 1
    (our_data, our_meta, our_type), (their_data, their_meta, their_type) = ours[0], theirs[0]
    assert our_type == their_type
    assert our_meta.keys() == their_meta.keys()
    assert our_meta["axis_labels"] == their_meta["axis_labels"]
    assert [d.shape for d in our_data] == [d.shape for d in their_data]


def test_accepts_a_single_path_in_a_list(synthetic_screen):
    reader = napari_get_reader([str(synthetic_screen.image)])
    assert reader is not None
    assert len(reader(str(synthetic_screen.image))) == 1
