from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from audio_transcription_demo.retry import is_retryable_error

SuggestedAction = Literal["retry", "mark_failed"]


@dataclass(frozen=True)
class ErrorClassification:
    retryable: bool
    reason_code: str
    suggested_action: SuggestedAction


def classify_error(exc: Exception) -> ErrorClassification:
    if is_retryable_error(exc):
        return ErrorClassification(
            retryable=True,
            reason_code="transient_error",
            suggested_action="retry",
        )
    return ErrorClassification(
        retryable=False,
        reason_code="transcription_failed",
        suggested_action="mark_failed",
    )
