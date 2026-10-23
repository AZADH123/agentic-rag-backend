"""
File validation for uploads.

We check three things, in order:
1. Filename has a supported extension.
2. Declared Content-Type matches the extension.
3. File size is within MAX_UPLOAD_SIZE_MB.

We do NOT do magic-bytes sniffing in this minimal version. Add it before
trusting untrusted uploads in production — see magic-bytes section in docs.
"""

from __future__ import annotations

from app.core.config import get_settings
from app.core.exceptions import InvalidFileError

# Extension → expected MIME type
EXTENSION_TO_MIME = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".txt": "text/plain",
}


import os


def validate_filename(filename: str) -> str:
    cleaned = os.path.basename(filename.replace("\\", "/"))
    if not cleaned or ".." in cleaned:
        raise InvalidFileError("Invalid filename")
    ext = "." + cleaned.rsplit(".", 1)[-1].lower() if "." in cleaned else ""
    if ext not in EXTENSION_TO_MIME:
        raise InvalidFileError(
            f"Unsupported file type. Allowed: {', '.join(EXTENSION_TO_MIME.keys())}"
        )
    return ext


def validate_content_type(declared: str, ext: str) -> str:
    expected = EXTENSION_TO_MIME[ext]
    settings = get_settings()
    base_declared = declared.split(";")[0].strip().lower()
    allowed = [t.split(";")[0].strip().lower() for t in settings.allowed_content_types]
    if base_declared not in allowed:
        raise InvalidFileError(f"Unsupported content type: {declared}")
    if base_declared != expected.split(";")[0].strip().lower():
        raise InvalidFileError(
            f"Content-Type '{declared}' does not match extension '{ext}'"
        )
    return base_declared


def validate_size(size_bytes: int) -> int:
    settings = get_settings()
    if size_bytes <= 0:
        raise InvalidFileError("Empty file")
    if size_bytes > settings.max_upload_size_bytes:
        raise InvalidFileError(
            f"File too large: {size_bytes} bytes "
            f"(max {settings.max_upload_size_bytes} bytes)"
        )
    return size_bytes