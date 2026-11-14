"""Screenshots without an imaging library: QEMU's PPM -> raw RGB -> a minimal PNG (and back)."""
from __future__ import annotations

import base64
import re
import struct
import zlib

MAX_PIXELS = 1024 * 768
_PPM = re.compile(rb"P6\s+(\d{1,5})\s+(\d{1,5})\s+255\s")


def ppm(data: bytes) -> tuple[int, int, bytes]:
    m = _PPM.match(data)
    if not m:
        raise ValueError("not a PPM screenshot")
    w, h = int(m.group(1)), int(m.group(2))
    rgb = data[m.end():m.end() + w * h * 3]
    if not 0 < w * h <= MAX_PIXELS or len(rgb) != w * h * 3:
        raise ValueError("bad PPM size")
    return w, h, rgb


def _chunk(kind: bytes, body: bytes) -> bytes:
    return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body))


def png(w: int, h: int, rgb: bytes) -> bytes:
    rows = b"".join(b"\x00" + rgb[y * w * 3:(y + 1) * w * 3] for y in range(h))  # filter 0 on every row
    return (b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
            + _chunk(b"IDAT", zlib.compress(rows, 6)) + _chunk(b"IEND", b""))


def unpng(data: bytes) -> tuple[int, int, bytes]:
    """Inverse of png() only (8-bit RGB, filter 0): enough to read back our own screenshots."""
    w, h = struct.unpack(">II", data[16:24])
    if not 0 < w * h <= MAX_PIXELS:
        raise ValueError("bad PNG size")
    pos, idat = 8, b""
    while pos < len(data):
        (n,), kind = struct.unpack(">I", data[pos:pos + 4]), data[pos + 4:pos + 8]
        if kind == b"IDAT":
            idat += data[pos + 8:pos + 8 + n]
        pos += 12 + n
    rows = zlib.decompress(idat)
    step = w * 3 + 1
    return w, h, b"".join(rows[y * step + 1:(y + 1) * step] for y in range(h))


def shot(ppm_bytes: bytes) -> dict:
    """JSON-friendly screenshot: {"w", "h", "png": base64}."""
    w, h, rgb = ppm(ppm_bytes)
    return {"w": w, "h": h, "png": base64.b64encode(png(w, h, rgb)).decode()}


def pixels(s: dict) -> tuple[int, int, bytes]:
    return unpng(base64.b64decode(s["png"]))
