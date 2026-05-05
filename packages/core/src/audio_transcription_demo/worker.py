from __future__ import annotations

from enum import StrEnum

from audio_transcription_demo.artifacts import ArtifactStore
from audio_transcription_demo.error_classification import classify_error
from audio_transcription_demo.provider import TranscriptionProvider
from audio_transcription_demo.repository import TERMINAL_STATUSES, JobRepository
from audio_transcription_demo.retry import RetryPolicy, retry_call
from audio_transcription_demo.time import utc_now


class ProcessOutcome(StrEnum):
    NO_JOB = "no_job"
    SKIPPED = "skipped"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


def process_next_job(
    *,
    repo: JobRepository,
    artifact_store: ArtifactStore,
    provider: TranscriptionProvider,
    retry_policy: RetryPolicy | None = None,
) -> ProcessOutcome:
    job = repo.claim_next_job()
    if job is None:
        return ProcessOutcome.NO_JOB
    return _process_claimed_job(
        repo=repo,
        artifact_store=artifact_store,
        provider=provider,
        job=job,
        retry_policy=retry_policy or RetryPolicy(),
    )


def process_job_by_id(
    *,
    repo: JobRepository,
    artifact_store: ArtifactStore,
    provider: TranscriptionProvider,
    job_id: str,
    retry_policy: RetryPolicy | None = None,
) -> ProcessOutcome:
    job = repo.get_job(job_id)
    if job is None:
        return ProcessOutcome.NO_JOB
    if str(job["status"]) in TERMINAL_STATUSES:
        return ProcessOutcome.SKIPPED
    claimed = repo.claim_job(job_id)
    if claimed is None:
        return ProcessOutcome.SKIPPED
    return _process_claimed_job(
        repo=repo,
        artifact_store=artifact_store,
        provider=provider,
        job=claimed,
        retry_policy=retry_policy or RetryPolicy(),
    )


def _process_claimed_job(
    *,
    repo: JobRepository,
    artifact_store: ArtifactStore,
    provider: TranscriptionProvider,
    job: dict[str, object],
    retry_policy: RetryPolicy,
) -> ProcessOutcome:
    job_id = str(job["id"])
    try:
        audio = repo.get_audio_by_id(str(job["audio_artifact_id"]))
        if audio is None:
            raise RuntimeError("audio artifact not found")
        audio_bytes = artifact_store.read_audio(str(audio["storage_path"]))
        payload = retry_call(
            lambda: provider.transcribe(audio_bytes, job_id=job_id),
            policy=retry_policy,
        )
        text = str(payload.get("text", ""))
        transcript_id_hint = f"pending-{job_id}"
        text_path, json_path = artifact_store.write_transcript(transcript_id_hint, text, payload)
        transcript = repo.create_transcript(
            job_id=job_id,
            text=text,
            text_path=text_path,
            json_path=json_path,
            created_at=utc_now(),
        )
        repo.mark_succeeded(job_id, str(transcript["id"]))
        return ProcessOutcome.SUCCEEDED
    except Exception as exc:
        classification = classify_error(exc)
        repo.mark_failed(job_id, f"{classification.reason_code}: {exc}")
        return ProcessOutcome.FAILED
