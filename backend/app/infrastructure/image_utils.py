import io

from PIL import Image, ImageOps, UnidentifiedImageError


def prepare_image(raw: bytes, max_px: int = 1024) -> tuple[bytes, str]:
    """Fix phone rotation, shrink, and re-encode as JPEG. Returns (bytes, mime)."""
    try:
        img = Image.open(io.BytesIO(raw))
        img = ImageOps.exif_transpose(img).convert("RGB")
    except (UnidentifiedImageError, OSError) as e:
        raise ValueError("Could not read the image file.") from e
    img.thumbnail((max_px, max_px))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue(), "image/jpeg"