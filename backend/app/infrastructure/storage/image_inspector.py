"""ImageInspector backed by Pillow: identifies the real format from the bytes and fully decodes
the image so truncated, malformed or decompression-bomb files are rejected before storage."""

import io
import warnings

from PIL import Image, UnidentifiedImageError

from app.domain.entities.media import ImageInfo
from app.domain.errors import MediaValidationError, UnsupportedMediaTypeError

_FORMAT_TO_MIME = {
    "JPEG": "image/jpeg",
    "PNG": "image/png",
    "WEBP": "image/webp",
    "AVIF": "image/avif",
}
MAX_PIXELS = 40_000_000  # ~40 MP is far beyond any product photo
MAX_EDGE = 12_000


class PillowImageInspector:
    def inspect(self, data: bytes) -> ImageInfo:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            try:
                with Image.open(io.BytesIO(data)) as image:
                    fmt = image.format or ""
                    width, height = image.size
                    if fmt not in _FORMAT_TO_MIME:
                        raise UnsupportedMediaTypeError(f"Unsupported image format: {fmt or '?'}.")
                    if width * height > MAX_PIXELS or max(width, height) > MAX_EDGE:
                        raise MediaValidationError("Image dimensions are too large.")
                    image.load()  # full decode: catches truncated / corrupt payloads
            except MediaValidationError:
                raise
            except (
                UnidentifiedImageError,
                Image.DecompressionBombError,
                Image.DecompressionBombWarning,
            ) as exc:
                raise UnsupportedMediaTypeError("File is not a supported image.") from exc
            except (OSError, ValueError, SyntaxError) as exc:
                raise MediaValidationError("Image file is corrupt or truncated.") from exc
        if width < 1 or height < 1:
            raise MediaValidationError("Image has no pixels.")
        return ImageInfo(content_type=_FORMAT_TO_MIME[fmt], width=width, height=height)
