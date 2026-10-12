"""File-type detection and image preparation.

Video and audio are checked from a bounded header and otherwise kept as uploaded.
"""

import io

from django.conf import settings
from PIL import Image, ImageOps

MAX_IMAGE_EDGE = 2560
THUMB_EDGE = 960
HEADER_BYTES = 64 * 1024

EXT = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
    "video/mp4": ".mp4",
    "video/webm": ".webm",
    "video/quicktime": ".mov",
    "audio/mpeg": ".mp3",
    "audio/wav": ".wav",
    "audio/ogg": ".ogg",
    "audio/mp4": ".m4a",
    "audio/flac": ".flac",
    "audio/webm": ".webm",
}


class MediaError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.message = message
        self.status = status


NOT_READY = "ذخیره‌سازی فایل هنوز آماده نیست."
PERMISSION = "اجازه این کار را ندارید."
BAD_REQUEST = "درخواست نامعتبر است."
BAD_TYPE = "این قالب پشتیبانی نمی‌شود."
BAD_FILE = "این فایل قابل استفاده نیست."
EMPTY_FILE = "فایل خالی است."
TOO_LARGE = "حجم فایل بیش از حد مجاز است."
SIZE_MISMATCH = "حجم فایل با مقدار اعلام‌شده یکی نیست."
KIND_MISMATCH = "نوع فایل با انتخاب شما یکی نیست."
INCOMPLETE = "بارگذاری کامل نشده. دوباره تلاش کنید."
EXPIRED = "مهلت بارگذاری تمام شد. دوباره تلاش کنید."
MISSING = "فایل در ذخیره‌سازی پیدا نشد. دوباره تلاش کنید."
IMAGE_ONLY = "فقط تصویر مجاز است."
NEED_IMAGE = "تصویر پروژه را بارگذاری کنید."
NEED_FILE = "فایل را بارگذاری کنید."
NEED_LABEL = "عنوان را وارد کنید."
UPLOAD_USED = "این بارگذاری دیگر قابل استفاده نیست."
UPLOAD_WRONG = "این بارگذاری برای این بخش نیست."


def max_bytes(kind):
    return {
        "photo": settings.MEDIA_MAX_IMAGE_BYTES,
        "video": settings.MEDIA_MAX_VIDEO_BYTES,
        "audio": settings.MEDIA_MAX_AUDIO_BYTES,
    }[kind]


def _brand(data):
    found = data.find(b"ftyp", 0, 64)
    if found < 4:
        return b""
    return data[found + 4 : found + 8]


def detect(data, requested):
    if not data:
        raise MediaError(EMPTY_FILE)
    kind = ""
    content_type = ""
    if data.startswith(b"\xff\xd8\xff"):
        kind, content_type = "photo", "image/jpeg"
    elif data.startswith(b"\x89PNG\r\n\x1a\n"):
        kind, content_type = "photo", "image/png"
    elif data.startswith((b"GIF87a", b"GIF89a")):
        kind, content_type = "photo", "image/gif"
    elif data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        kind, content_type = "photo", "image/webp"
    elif data.startswith(b"RIFF") and data[8:12] == b"WAVE":
        kind, content_type = "audio", "audio/wav"
    elif data.startswith(b"OggS"):
        kind, content_type = "audio", "audio/ogg"
    elif data.startswith(b"fLaC"):
        kind, content_type = "audio", "audio/flac"
    elif data.startswith(b"ID3") or (len(data) > 2 and data[0] == 0xFF and data[1] & 0xE0 == 0xE0):
        kind, content_type = "audio", "audio/mpeg"
    elif data.startswith(b"\x1a\x45\xdf\xa3"):
        if requested == "audio":
            kind, content_type = "audio", "audio/webm"
        else:
            kind, content_type = "video", "video/webm"
    else:
        brand = _brand(data)
        if brand in {b"M4A ", b"M4B ", b"f4a "}:
            kind, content_type = "audio", "audio/mp4"
        elif brand == b"qt  ":
            kind, content_type = "video", "video/quicktime"
        elif brand:
            kind, content_type = "video", "video/mp4"
    if not kind:
        raise MediaError(BAD_TYPE)
    if kind != requested:
        raise MediaError(KIND_MISMATCH)
    return kind, content_type


def _limit_edge(image, edge):
    if max(image.size) > edge:
        image.thumbnail((edge, edge), Image.Resampling.LANCZOS)
    return image


def _jpeg_bytes(image, edge, quality):
    prepared = image.convert("RGB")
    _limit_edge(prepared, edge)
    output = io.BytesIO()
    prepared.save(output, format="JPEG", quality=quality, optimize=True, progressive=True)
    return output.getvalue(), prepared.size


def process_image(data, content_type):
    Image.MAX_IMAGE_PIXELS = 20_000_000
    try:
        image = Image.open(io.BytesIO(data))
        image.load()
    except Exception as exc:
        raise MediaError(BAD_FILE) from exc
    try:
        image = ImageOps.exif_transpose(image) or image
    except Exception as exc:
        raise MediaError(BAD_FILE) from exc

    if content_type == "image/gif":
        output = io.BytesIO()
        try:
            image.save(output, format="GIF", save_all=getattr(image, "is_animated", False), optimize=True)
        except Exception as exc:
            raise MediaError(BAD_FILE) from exc
        body = output.getvalue()
        frame = image.convert("RGB")
        thumb, _size = _jpeg_bytes(frame, THUMB_EDGE, 80)
        return body, "image/gif", thumb

    has_alpha = image.mode in {"RGBA", "LA"} or (image.mode == "P" and "transparency" in image.info)
    if content_type == "image/png" and has_alpha:
        prepared = image.convert("RGBA")
        _limit_edge(prepared, MAX_IMAGE_EDGE)
        output = io.BytesIO()
        prepared.save(output, format="PNG", optimize=True)
        thumb, _size = _jpeg_bytes(prepared, THUMB_EDGE, 80)
        return output.getvalue(), "image/png", thumb

    if content_type == "image/webp" and has_alpha:
        prepared = image.convert("RGBA")
        _limit_edge(prepared, MAX_IMAGE_EDGE)
        output = io.BytesIO()
        prepared.save(output, format="WEBP", quality=82, method=4)
        thumb, _size = _jpeg_bytes(prepared, THUMB_EDGE, 80)
        return output.getvalue(), "image/webp", thumb

    body, _size = _jpeg_bytes(image, MAX_IMAGE_EDGE, 82)
    thumb, _thumb_size = _jpeg_bytes(image, THUMB_EDGE, 80)
    return body, "image/jpeg", thumb
