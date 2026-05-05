from __future__ import annotations

import hashlib
from pathlib import Path


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def validate_wav_upload(data: bytes, filename: str, content_type: str | None) -> None:
    suffix_ok = Path(filename).suffix.lower() == ".wav"
    allowed_types = {None, "", "audio/wav", "audio/x-wav", "application/octet-stream"}
    content_type_ok = content_type in allowed_types
    header_ok = len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WAVE"
    if not suffix_ok or not content_type_ok or not header_ok:
        raise ValueError("Only WAV uploads are supported")
