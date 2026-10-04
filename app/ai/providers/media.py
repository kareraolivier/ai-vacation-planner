from typing import Optional, Set

from .base import SpeechToTextError, VisionError

AUDIO_CONTENT_TYPES = {
    "audio/mpeg",
    "audio/mp3",
    "audio/wav",
    "audio/x-wav",
    "audio/wave",
    "audio/webm",
    "audio/ogg",
    "audio/flac",
    "audio/mp4",
    "audio/x-m4a",
    "audio/m4a",
}

IMAGE_CONTENT_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/gif",
    "image/webp",
}

IMAGE_MAGIC = (
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"GIF87a", "image/gif"),
    (b"GIF89a", "image/gif"),
    (b"RIFF", "image/webp"),
)


def _extensions(allowed_formats: str) -> Set[str]:
    return {item.strip().lower().lstrip(".") for item in allowed_formats.split(",") if item.strip()}


def _suffix(filename: Optional[str]) -> str:
    if not filename or "." not in filename:
        return ""
    return filename.rsplit(".", 1)[-1].lower()


def validate_audio(
    audio: bytes,
    filename: Optional[str],
    content_type: Optional[str],
    max_bytes: int,
    allowed_formats: str,
) -> None:
    if not audio:
        raise SpeechToTextError("Audio file is empty", code="empty")
    if len(audio) > max_bytes:
        raise SpeechToTextError("Audio file is too large", code="too_large")

    allowed = _extensions(allowed_formats)
    suffix = _suffix(filename)
    normalized_type = (content_type or "").split(";")[0].strip().lower()
    type_ok = normalized_type in AUDIO_CONTENT_TYPES
    suffix_ok = suffix in allowed
    if not suffix_ok and not type_ok:
        raise SpeechToTextError(
            "Unsupported audio format. Use mp3, wav, m4a, webm, ogg, or flac.",
            code="unsupported",
        )


def detect_image_type(image: bytes) -> Optional[str]:
    for signature, mime in IMAGE_MAGIC:
        if image.startswith(signature):
            if mime == "image/webp" and b"WEBP" not in image[:16]:
                return None
            return mime
    return None


def validate_image(
    image: bytes,
    filename: Optional[str],
    content_type: Optional[str],
    max_bytes: int,
    allowed_formats: str,
) -> str:
    if not image:
        raise VisionError("Image file is empty", code="empty")
    if len(image) > max_bytes:
        raise VisionError("Image file is too large", code="too_large")

    allowed = _extensions(allowed_formats)
    suffix = _suffix(filename)
    detected = detect_image_type(image)
    normalized_type = (content_type or "").split(";")[0].strip().lower()
    if normalized_type == "image/jpg":
        normalized_type = "image/jpeg"

    if detected is None and suffix not in allowed and normalized_type not in IMAGE_CONTENT_TYPES:
        raise VisionError("Invalid or unsupported image. Use jpeg, png, gif, or webp.", code="invalid")

    format_name = (detected or normalized_type or f"image/{suffix}").split("/")[-1]
    if format_name == "jpg":
        format_name = "jpeg"
    if format_name not in allowed and suffix not in allowed:
        raise VisionError("Unsupported image format. Use jpeg, png, gif, or webp.", code="unsupported")
    return detected or normalized_type or f"image/{format_name}"
