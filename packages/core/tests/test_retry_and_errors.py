from __future__ import annotations

import pytest
from audio_transcription_demo.error_classification import classify_error
from audio_transcription_demo.retry import RetryPolicy, retry_call


def test_retry_call_retries_retryable_error() -> None:
    attempts = {"count": 0}

    def flaky() -> str:
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise TimeoutError("temporary")
        return "ok"

    result = retry_call(flaky, policy=RetryPolicy(max_attempts=2), sleep=lambda _: None)

    assert result == "ok"
    assert attempts["count"] == 2


def test_retry_call_stops_on_non_retryable_error() -> None:
    attempts = {"count": 0}

    def invalid() -> str:
        attempts["count"] += 1
        raise ValueError("invalid")

    with pytest.raises(ValueError):
        retry_call(invalid, policy=RetryPolicy(max_attempts=3), sleep=lambda _: None)

    assert attempts["count"] == 1


def test_error_classification_marks_timeout_retryable() -> None:
    result = classify_error(TimeoutError("temporary"))

    assert result.retryable is True
    assert result.suggested_action == "retry"


def test_error_classification_marks_value_error_non_retryable() -> None:
    result = classify_error(ValueError("bad request"))

    assert result.retryable is False
    assert result.suggested_action == "mark_failed"
