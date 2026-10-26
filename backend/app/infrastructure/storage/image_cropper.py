"""ImageCropper backed by Pillow: cuts a frame-shaped rectangle out of the original and stores
it as an optimised WebP, so the storefront downloads only the composition it shows."""

import io

from PIL import Image, ImageOps

from app.domain.entities.media import CropRect, FrameSpec, RenderedImage
from app.domain.errors import MediaValidationError

WEBP_QUALITY = 85


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def snap_to_ratio(
    rect: CropRect, image_width: int, image_height: int, ratio: float
) -> tuple[int, int, int, int]:
    """Pixel box (left, top, right, bottom) for ``rect``, trimmed around its centre to exactly
    ``ratio`` and kept inside the image. Editors send fractions, so rounding never distorts."""
    left = _clamp(rect.x, 0.0, 1.0) * image_width
    top = _clamp(rect.y, 0.0, 1.0) * image_height
    width = _clamp(rect.width, 0.0, 1.0) * image_width
    height = _clamp(rect.height, 0.0, 1.0) * image_height
    width = min(width, image_width - left)
    height = min(height, image_height - top)
    if width < 1 or height < 1:
        raise MediaValidationError("The crop area is empty.")

    centre_x, centre_y = left + width / 2, top + height / 2
    if width / height > ratio:
        width = height * ratio
    else:
        height = width / ratio
    left = _clamp(centre_x - width / 2, 0, image_width - width)
    top = _clamp(centre_y - height / 2, 0, image_height - height)

    box_left, box_top = round(left), round(top)
    box_width = max(1, min(round(width), image_width - box_left))
    box_height = max(1, min(round(height), image_height - box_top))
    return box_left, box_top, box_left + box_width, box_top + box_height


class PillowImageCropper:
    def render(self, data: bytes, rect: CropRect, spec: FrameSpec) -> RenderedImage:
        try:
            with Image.open(io.BytesIO(data)) as source:
                # Browsers show JPEGs rotated by their EXIF orientation, and the editor's
                # fractions refer to what the admin saw, so rotate before cutting.
                image = ImageOps.exif_transpose(source)
                image_width, image_height = image.size
                box = snap_to_ratio(rect, image_width, image_height, spec.ratio)
                cut = image.crop(box)
                out_width = min(spec.output_width, cut.width)
                out_height = max(1, round(out_width / spec.ratio))
                if cut.mode not in ("RGB", "RGBA"):
                    has_alpha = "A" in cut.getbands() or "transparency" in cut.info
                    cut = cut.convert("RGBA" if has_alpha else "RGB")
                if cut.size != (out_width, out_height):
                    cut = cut.resize((out_width, out_height), Image.Resampling.LANCZOS)
                buffer = io.BytesIO()
                cut.save(buffer, format="WEBP", quality=WEBP_QUALITY, method=4)
        except MediaValidationError:
            raise
        except (OSError, ValueError) as exc:
            raise MediaValidationError("The original image could not be cropped.") from exc

        left, top, right, bottom = box
        return RenderedImage(
            data=buffer.getvalue(),
            content_type="image/webp",
            width=out_width,
            height=out_height,
            rect=CropRect(
                x=left / image_width,
                y=top / image_height,
                width=(right - left) / image_width,
                height=(bottom - top) / image_height,
            ),
        )
