import warnings
from io import BytesIO
from uuid import uuid4

from PIL import Image, ImageOps, UnidentifiedImageError
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile


def optimize(upload):
    if upload.size > 2097152:
        raise ValidationError({"image": "L’image dépasse 2 Mio."})
    try:
        upload.seek(0)
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(upload) as image:
                if image.format not in {"JPEG", "PNG", "WEBP", "GIF"} or getattr(image, "n_frames", 1) != 1:
                    raise ValueError("Format ou animation refusé")
                if image.width * image.height > 20000000:
                    raise ValueError("Image trop complexe")
                image.load()
                image = ImageOps.exif_transpose(image)
                image.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
                if image.mode in ("RGBA", "LA") or "transparency" in image.info:
                    rgba = image.convert("RGBA")
                    output_image = Image.new("RGB", rgba.size, "white")
                    output_image.paste(rgba, mask=rgba.getchannel("A"))
                else:
                    output_image = image.convert("RGB")
                output = BytesIO()
                output_image.save(output, "JPEG", quality=82, optimize=True)
        return ContentFile(output.getvalue(), name=f"{uuid4().hex}.jpg")
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise ValidationError({"image": "Image invalide, animée ou trop complexe."}) from exc
    finally:
        upload.seek(0)
