import struct
import zlib
from io import BytesIO

from PIL import Image


def raster(width: int, height: int, image_format: str = "PNG") -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (width, height)).save(buffer, format=image_format)
    return buffer.getvalue()


def png_chunk(kind: bytes, data: bytes) -> bytes:
    checksum = zlib.crc32(kind + data) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", checksum)


def decompression_bomb(side: int) -> bytes:
    header = struct.pack(">IIBBBBB", side, side, 8, 0, 0, 0, 0)
    compressor = zlib.compressobj(9)
    row = b"\x00" * (side + 1)
    pixels = b"".join(compressor.compress(row) for _ in range(side))
    pixels += compressor.flush()
    return (
        b"\x89PNG\r\n\x1a\n"
        + png_chunk(b"IHDR", header)
        + png_chunk(b"IDAT", pixels)
        + png_chunk(b"IEND", b"")
    )


def iso_media_image(brand: bytes, width: int, height: int) -> bytes:
    file_type = struct.pack(">I", 16) + b"ftyp" + brand + b"\x00\x00\x00\x00"
    extent = (
        struct.pack(">I", 20)
        + b"ispe"
        + b"\x00\x00\x00\x00"
        + struct.pack(">II", width, height)
    )
    return file_type + extent
