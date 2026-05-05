from __future__ import annotations

from typing import Protocol


class TranscriptionProvider(Protocol):
    def transcribe(self, audio_bytes: bytes, *, job_id: str) -> dict[str, object]: ...


class FakeTranscriptionProvider:
    def transcribe(self, audio_bytes: bytes, *, job_id: str) -> dict[str, object]:
        size = len(audio_bytes)
        return {
            "provider": "fake",
            "job_id": job_id,
            "text": f"Fake transcript for {job_id}. Received {size} bytes of WAV audio.",
        }
