"""On-demand WebP thumbnails for uploaded images.

Product photos are uploaded as-is (PNG up to ~3 MB).  Browsers only need a
~400px WebP for a product card, so we generate it once and serve the small file:

    MEDIA_ROOT/thumbs/<width>/<original path>.webp

* Generated on first use, then just a file-exists check (cheap ``stat``).
* Regenerated automatically when the original file is replaced (mtime check).
* Any error -> the original URL is returned, so a page never breaks because of
  a bad image.
* ``python manage.py warm_thumbnails`` pre-generates everything after a deploy.
"""
import logging
import os
from pathlib import Path

from django.conf import settings
from django.utils.encoding import filepath_to_uri
from PIL import Image, ImageOps

logger = logging.getLogger(__name__)

ALLOWED_WIDTHS = (160, 240, 320, 480, 640, 800, 1200, 1600, 1920)
WEBP_QUALITY = 80

Image.MAX_IMAGE_PIXELS = 40_000_000  # refuse decompression bombs


def _snap_width(width):
    """Round requested width up to a known size (limits the number of variants)."""
    for allowed in ALLOWED_WIDTHS:
        if width <= allowed:
            return allowed
    return ALLOWED_WIDTHS[-1]


def thumbnail_paths(name, width):
    width = _snap_width(int(width))
    rel = Path(getattr(settings, "THUMBNAIL_DIR", "thumbs")) / str(width) / (name + ".webp")
    return width, Path(settings.MEDIA_ROOT) / rel, "/" + settings.MEDIA_URL.strip("/") + "/" + filepath_to_uri(rel.as_posix())


def build_thumbnail(source, target, width):
    with Image.open(source) as img:
        img = ImageOps.exif_transpose(img)
        if img.mode not in ("RGB", "RGBA"):
            img = img.convert("RGBA" if "transparency" in img.info or img.mode in ("LA", "P") else "RGB")
        if img.width > width:
            height = round(img.height * width / img.width)
            img = img.resize((width, height), Image.LANCZOS)

        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_name(f".{target.name}.{os.getpid()}.tmp")
        img.save(tmp, "WEBP", quality=WEBP_QUALITY, method=5)
        os.replace(tmp, target)  # atomic: concurrent workers never see half a file


def thumbnail_url(field, width):
    """URL of a WebP version of ``field`` (an ImageFieldFile) at most ``width`` px wide."""
    if not field:
        return ""
    name = getattr(field, "name", "") or ""
    try:
        source = Path(field.path)
    except Exception:  # storage without local paths
        return field.url

    if name.lower().endswith(".svg"):
        return field.url

    try:
        width, target, url = thumbnail_paths(name, width)
        src_mtime = source.stat().st_mtime
        try:
            fresh = target.stat().st_mtime >= src_mtime
        except FileNotFoundError:
            fresh = False
        if not fresh:
            build_thumbnail(source, target, width)
        return url
    except FileNotFoundError:
        return field.url
    except Exception:
        logger.warning("Thumbnail failed for %s", name, exc_info=True)
        try:
            return field.url
        except Exception:
            return ""
