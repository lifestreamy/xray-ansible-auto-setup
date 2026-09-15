"""Pixel-art icon pipeline for xrayvpn: grid files -> PNGs, multi-size ICO, HTML preview.

stdlib-only. The grids are data files and the source of truth:
``assets/icon-16.grid`` (simplified, used for the 16px entry) and
``assets/icon-64.grid`` (detail, nearest-sampled to 24..256). Each line is
one row of cells from ``.`` (transparent) ``D`` ``T`` ``W`` ``S``.

Re-run after editing a grid:  python scripts/make_icon.py
Piskel round-trip (draw 64x64, export PNG, then):
    python scripts/make_icon.py --from-png path/to/export.png
The PNG reader accepts 8-bit RGB/RGBA non-interlaced files (Piskel export);
anything else raises a clear error.
"""

from __future__ import annotations

import argparse
import base64
import struct
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PALETTE: dict[str, tuple[int, int, int, int] | None] = {
    ".": None,
    "D": (0x0B, 0x1F, 0x1A, 255),
    "T": (0x00, 0xD5, 0x87, 255),
    "W": (0xE8, 0xFE, 0xF4, 255),
    "S": (0x1B, 0x8A, 0x5A, 255),
}

GRID16 = ROOT / "assets" / "icon-16.grid"
GRID64 = ROOT / "assets" / "icon-64.grid"

SIZES: tuple[int, ...] = (16, 24, 32, 48, 64, 128, 256)
PREVIEW_SIZES: tuple[int, ...] = (16, 32, 48, 64, 128, 256)

OUT_ICO = ROOT / "assets" / "xrayvpn.ico"
OUT_PNG32 = ROOT / "assets" / "icon-32.png"
OUT_PNG64 = ROOT / "assets" / "icon-64.png"
OUT_PREVIEW = ROOT / "assets" / "icon-preview.html"


def load_grid(path: Path, side: int) -> tuple[str, ...]:
    lines = path.read_text(encoding="utf-8").splitlines()
    lines = [line for line in lines if line.strip()]
    if len(lines) != side:
        raise ValueError(f"{path.name}: expected {side} rows, got {len(lines)}")
    for line in lines:
        if len(line) != side:
            raise ValueError(f"{path.name}: rows must be {side} cells, got {len(line)}: {line!r}")
        unknown = set(line) - set(PALETTE)
        if unknown:
            raise ValueError(f"{path.name}: unknown cells {sorted(unknown)}")
    return tuple(lines)


def grids(grid16_path: Path = GRID16, grid64_path: Path = GRID64) -> dict[int, tuple[str, ...]]:
    return {16: load_grid(grid16_path, 16), 64: load_grid(grid64_path, 64)}


def pixel_at(grids_map: dict[int, tuple[str, ...]], size: int, y: int, x: int):
    side = 16 if size == 16 else 64
    grid = grids_map[side]
    return PALETTE[grid[y * side // size][x * side // size]]


def _chunk(tag: bytes, data: bytes) -> bytes:
    return (
        struct.pack(">I", len(data))
        + tag
        + data
        + struct.pack(">I", zlib.crc32(tag + data))
    )


def png_bytes(grids_map: dict[int, tuple[str, ...]], size: int) -> bytes:
    body = b"".join(
        b"\x00"
        + b"".join(
            struct.pack("4B", *(pixel_at(grids_map, size, y, x) or (0, 0, 0, 0)))
            for x in range(size)
        )
        for y in range(size)
    )
    return (
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0))
        + _chunk(b"IDAT", zlib.compress(body, 9))
        + _chunk(b"IEND", b"")
    )


def ico_bytes(grids_map: dict[int, tuple[str, ...]]) -> bytes:
    images = [png_bytes(grids_map, size) for size in SIZES]
    header = struct.pack("<HHH", 0, 1, len(images))
    entries = b""
    offset = 6 + 16 * len(images)
    for size, data in zip(SIZES, images):
        edge = 0 if size >= 256 else size
        entries += struct.pack("<BBBBHHII", edge, edge, 0, 0, 1, 32, len(data), offset)
        offset += len(data)
    return header + entries + b"".join(images)


def preview_html(grids_map: dict[int, tuple[str, ...]]) -> str:
    cells = []
    for size in PREVIEW_SIZES:
        src = "data:image/png;base64," + base64.b64encode(
            png_bytes(grids_map, size)
        ).decode("ascii")
        grid = "icon-16.grid" if size == 16 else "icon-64.grid"
        cells.append(
            f"<tr><th>{size}px ({grid})</th>"
            f'<td style="background:#ffffff"><img width="{min(size, 128)}" '
            f'src="{src}" alt="light {size}"></td>'
            f'<td style="background:#1f2430"><img width="{min(size, 128)}" '
            f'src="{src}" alt="dark {size}"></td></tr>'
        )
    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        "<title>xrayvpn icon preview</title>"
        "<style>body{font-family:monospace}table{border-collapse:collapse}"
        "td,th{padding:10px;border:1px solid #555;text-align:center}</style>"
        "</head><body><h2>xrayvpn icon — icon-16.grid (16px) + icon-64.grid (detail)</h2>"
        "<table><tr><th>size (grid)</th><th>light bg</th><th>dark bg</th></tr>"
        + "".join(cells)
        + "</table></body></html>"
    )


def _paeth(a: int, b: int, c: int) -> int:
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    return b if pb <= pc else c


def png_decode(data: bytes) -> list[tuple[int, int, int, int]]:
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("not a PNG file")
    pos = 8
    width = height = 0
    color_type = 0
    idat = b""
    while pos + 8 <= len(data):
        (length,) = struct.unpack(">I", data[pos : pos + 4])
        tag = data[pos + 4 : pos + 8]
        chunk = data[pos + 8 : pos + 8 + length]
        if tag == b"IHDR":
            width, height, depth, color_type, comp, filt, interlace = struct.unpack(
                ">IIBBBBB", chunk
            )
            if depth != 8 or interlace != 0 or comp != 0 or filt != 0:
                raise ValueError("only 8-bit non-interlaced deflate PNGs are supported")
            if color_type not in (2, 6):
                raise ValueError("only RGB and RGBA color types are supported")
        elif tag == b"IDAT":
            idat += chunk
        elif tag == b"IEND":
            break
        pos += 12 + length
    bpp = 4 if color_type == 6 else 3
    stride = width * bpp
    raw = zlib.decompress(idat)
    out = bytearray(height * stride)
    prev = bytearray(stride)
    pos = 0
    for y in range(height):
        f = raw[pos]
        pos += 1
        line = bytearray(raw[pos : pos + stride])
        pos += stride
        for i in range(stride):
            left = line[i - bpp] if i >= bpp else 0
            up = prev[i]
            upleft = prev[i - bpp] if i >= bpp else 0
            if f == 1:
                line[i] = (line[i] + left) & 255
            elif f == 2:
                line[i] = (line[i] + up) & 255
            elif f == 3:
                line[i] = (line[i] + ((left + up) >> 1)) & 255
            elif f == 4:
                line[i] = (line[i] + _paeth(left, up, upleft)) & 255
            elif f != 0:
                raise ValueError(f"unknown PNG filter {f}")
        out[y * stride : (y + 1) * stride] = line
        prev = line
    pixels = []
    for i in range(width * height):
        if bpp == 4:
            r, g, b, a = out[i * 4 : i * 4 + 4]
        else:
            r, g, b = out[i * 3 : i * 3 + 3]
            a = 255
        pixels.append((r, g, b, a))
    return pixels


def grid_from_png(path: Path) -> tuple[str, ...]:
    pixels = png_decode(path.read_bytes())
    side = int(len(pixels) ** 0.5)
    if side * side != len(pixels):
        raise ValueError("PNG pixel count is not a square")
    if side != 64:
        raise ValueError(f"expected a 64x64 Piskel export, got {side}x{side}")
    rows = []
    for y in range(side):
        chars = []
        for x in range(side):
            r, g, b, a = pixels[y * side + x]
            if a < 128:
                chars.append(".")
                continue
            best = "D"
            dist = None
            for cell, color in PALETTE.items():
                if cell == "." or color is None:
                    continue
                d = (color[0] - r) ** 2 + (color[1] - g) ** 2 + (color[2] - b) ** 2
                if dist is None or d < dist:
                    best, dist = cell, d
            chars.append(best)
        rows.append("".join(chars))
    return tuple(rows)


def write_outputs(grids_map: dict[int, tuple[str, ...]]) -> list[Path]:
    written = []
    for path, data in (
        (OUT_ICO, ico_bytes(grids_map)),
        (OUT_PNG32, png_bytes(grids_map, 32)),
        (OUT_PNG64, png_bytes(grids_map, 64)),
        (OUT_PREVIEW, preview_html(grids_map).encode("utf-8")),
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        written.append(path)
    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--from-png", help="rewrite icon-64.grid from a 64x64 Piskel PNG export")
    args = parser.parse_args(argv)
    if args.from_png:
        new_grid = grid_from_png(Path(args.from_png))
        old = GRID64.read_text(encoding="utf-8").splitlines()
        changed = sum(1 for new, old_line in zip(new_grid, old) if new != old_line)
        GRID64.write_text("\n".join(new_grid) + "\n", encoding="utf-8")
        print(f"icon-64.grid rewritten: {changed} rows changed")
    grids_map = grids()
    for path in write_outputs(grids_map):
        print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
