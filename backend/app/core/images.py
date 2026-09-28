import struct
import warnings
from dataclasses import dataclass
from io import BytesIO

from PIL import Image, UnidentifiedImageError

MAX_IMAGE_SIDE_PIXELS = 8000
MAX_IMAGE_PIXELS = 40_000_000
IMAGE_SPATIAL_EXTENT_BOX = b"ispe"
IMAGE_SPATIAL_EXTENT_OFFSET = 8
IMAGE_SPATIAL_EXTENT_SIZE = 8
ISO_MEDIA_IMAGE_TYPES = frozenset({"image/heic", "image/avif"})


@dataclass(frozen=True)
class ImageSize:
    width: int
    height: int

    @property
    def within_limits(self) -> bool:
        return (
            self.width <= MAX_IMAGE_SIDE_PIXELS
            and self.height <= MAX_IMAGE_SIDE_PIXELS
            and self.width * self.height <= MAX_IMAGE_PIXELS
        )


OVERSIZED = ImageSize(MAX_IMAGE_SIDE_PIXELS + 1, MAX_IMAGE_SIDE_PIXELS + 1)


def _spatial_extents(content: bytes) -> list[ImageSize]:
    extents: list[ImageSize] = []
    start = content.find(IMAGE_SPATIAL_EXTENT_BOX)
    while start != -1:
        offset = start + IMAGE_SPATIAL_EXTENT_OFFSET
        field = content[offset : offset + IMAGE_SPATIAL_EXTENT_SIZE]
        if len(field) == IMAGE_SPATIAL_EXTENT_SIZE:
            extents.append(ImageSize(*struct.unpack(">II", field)))
        start = content.find(IMAGE_SPATIAL_EXTENT_BOX, start + 1)
    return extents


def _largest(sizes: list[ImageSize]) -> ImageSize | None:
    return max(sizes, key=lambda size: size.width * size.height, default=None)


def image_size(content: bytes, mime_type: str) -> ImageSize | None:
    if mime_type in ISO_MEDIA_IMAGE_TYPES:
        return _largest(_spatial_extents(content))
    with warnings.catch_warnings():
        warnings.simplefilter("error", Image.DecompressionBombWarning)
        try:
            with Image.open(BytesIO(content)) as image:
                return ImageSize(*image.size)
        except (Image.DecompressionBombError, Image.DecompressionBombWarning):
            return OVERSIZED
        except (UnidentifiedImageError, OSError, ValueError, SyntaxError):
            return None


def image_within_limits(content: bytes, mime_type: str) -> bool:
    size = image_size(content, mime_type)
    return size is not None and size.within_limits
