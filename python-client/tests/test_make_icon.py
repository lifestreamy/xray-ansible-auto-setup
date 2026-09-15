"""Icon pipeline contract (scripts/make_icon.py): grid files, PNG/ICO bytes, Piskel round-trip."""

from __future__ import annotations

import importlib.util
import struct
import zlib
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("make_icon", _ROOT / "scripts" / "make_icon.py")
assert _spec and _spec.loader
icon_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(icon_mod)


def _rgba(cell: str) -> tuple[int, int, int, int]:
    return struct.unpack("4B", bytes(icon_mod.PALETTE[cell]))


def _decode_png(data: bytes) -> tuple[int, int, bytes]:
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    width, height = struct.unpack(">II", data[16:24])
    raw = zlib.decompress(data[data.index(b"IDAT") + 4 : data.index(b"IEND") - 4])
    return width, height, raw


def test_grids_load_and_validate() -> None:
    maps = icon_mod.grids()
    assert len(maps[16]) == 16 and all(len(row) == 16 for row in maps[16])
    assert len(maps[64]) == 64 and all(len(row) == 64 for row in maps[64])
    cells = {c for row in maps[16] + maps[64] for c in row}
    assert cells <= set(icon_mod.PALETTE)


def test_grid_selection_and_nearest_sampling() -> None:
    maps = icon_mod.grids()
    assert icon_mod.pixel_at(maps, 16, 0, 13) == _rgba("T")
    assert icon_mod.pixel_at(maps, 16, 0, 0) is None
    assert icon_mod.pixel_at(maps, 64, 24, 5) == _rgba("W")
    assert icon_mod.pixel_at(maps, 64, 32, 32) == _rgba("T")
    assert icon_mod.pixel_at(maps, 256, 128, 128) == icon_mod.pixel_at(maps, 64, 32, 32)
    assert icon_mod.pixel_at(maps, 32, 0, 0) is None
    assert icon_mod.pixel_at(maps, 128, 64, 64) == icon_mod.pixel_at(maps, 64, 32, 32)


def test_png_dims_and_transparent_corner() -> None:
    maps = icon_mod.grids()
    for size in (32, 64, 256):
        width, height, raw = _decode_png(icon_mod.png_bytes(maps, size))
        assert (width, height) == (size, size)
        stride = 1 + size * 4
        off = 1 + 1 * stride + 1 * 4
        assert tuple(raw[off : off + 4]) == (0, 0, 0, 0)


def test_ico_directory() -> None:
    maps = icon_mod.grids()
    data = icon_mod.ico_bytes(maps)
    reserved, image_type, count = struct.unpack("<HHH", data[:6])
    assert (reserved, image_type) == (0, 1)
    assert count == len(icon_mod.SIZES)
    offset = 6 + 16 * count
    for index, size in enumerate(icon_mod.SIZES):
        entry = data[6 + 16 * index : 22 + 16 * index]
        edge_w, edge_h, colors, reserved_b, planes, bpp, length, start = struct.unpack(
            "<BBBBHHII", entry
        )
        assert (edge_w, edge_h, colors, reserved_b, planes, bpp) == (
            0 if size >= 256 else size,
            0 if size >= 256 else size,
            0,
            0,
            1,
            32,
        )
        assert start == offset
        assert data[start : start + 8] == b"\x89PNG\r\n\x1a\n"
        offset += length
    assert offset == len(data)


def test_committed_ico_matches_grids() -> None:
    committed = (_ROOT / "assets" / "xrayvpn.ico").read_bytes()
    assert committed == icon_mod.ico_bytes(icon_mod.grids())


def test_from_png_round_trip(tmp_path: Path) -> None:
    maps = icon_mod.grids()
    png = tmp_path / "export.png"
    png.write_bytes(icon_mod.png_bytes(maps, 64))
    assert icon_mod.grid_from_png(png) == maps[64]


def test_preview_lists_sizes_and_grids() -> None:
    html = icon_mod.preview_html(icon_mod.grids())
    for size in icon_mod.PREVIEW_SIZES:
        assert f"{size}px" in html
    assert "icon-16.grid" in html and "icon-64.grid" in html
