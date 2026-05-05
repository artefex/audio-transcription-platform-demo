from __future__ import annotations

from pathlib import Path

from audio_transcription_demo.artifacts import LocalArtifactStore
from audio_transcription_demo.db import create_engine_for_url, create_schema
from audio_transcription_demo.jobs import create_job_from_upload
from audio_transcription_demo.provider import FakeTranscriptionProvider
from audio_transcription_demo.repository import JobRepository
from audio_transcription_demo.worker import ProcessOutcome, process_job_by_id, process_next_job


class FailingProvider:
    def transcribe(self, audio_bytes: bytes, *, job_id: str) -> dict[str, object]:
        raise RuntimeError("provider failed")


def wav_bytes() -> bytes:
    return b"RIFF\x24\x00\x00\x00WAVEfmt " + b"\x00" * 32


def fixture(tmp_path: Path) -> tuple[JobRepository, LocalArtifactStore]:
    engine = create_engine_for_url("sqlite:///:memory:")
    create_schema(engine)
    repo = JobRepository(engine)
    store = LocalArtifactStore(tmp_path / "artifacts")
    return repo, store


def create_job(repo: JobRepository, store: LocalArtifactStore) -> dict[str, object]:
    result = create_job_from_upload(
        repo=repo,
        artifact_store=store,
        data=wav_bytes(),
        filename="sample.wav",
        content_type="audio/wav",
        idempotency="force_new",
    )
    return result.job


def test_worker_claims_queued_job_and_marks_processing(tmp_path: Path) -> None:
    repo, store = fixture(tmp_path)
    job = create_job(repo, store)

    claimed = repo.claim_next_job()

    assert claimed is not None
    assert claimed["id"] == job["id"]
    assert claimed["status"] == "processing"
    assert claimed["attempts"] == 1


def test_success_writes_transcript_row_and_artifact(tmp_path: Path) -> None:
    repo, store = fixture(tmp_path)
    create_job(repo, store)

    outcome = process_next_job(
        repo=repo,
        artifact_store=store,
        provider=FakeTranscriptionProvider(),
    )

    assert outcome == ProcessOutcome.SUCCEEDED
    job = repo.find_reusable_job_for_audio_hash(next(iter(store.audio_dir.glob("*.wav"))).stem)
    assert job is not None
    assert job["status"] == "succeeded"
    transcript = repo.get_transcript(str(job["transcript_id"]))
    assert transcript is not None
    assert Path(str(transcript["text_path"])).exists()
    assert Path(str(transcript["json_path"])).exists()


def test_provider_failure_increments_attempts_and_records_error(tmp_path: Path) -> None:
    repo, store = fixture(tmp_path)
    job = create_job(repo, store)

    outcome = process_next_job(repo=repo, artifact_store=store, provider=FailingProvider())

    updated = repo.get_job(str(job["id"]))
    assert outcome == ProcessOutcome.FAILED
    assert updated is not None
    assert updated["status"] == "failed"
    assert updated["attempts"] == 1
    assert updated["last_error"]


def test_terminal_jobs_are_skipped(tmp_path: Path) -> None:
    repo, store = fixture(tmp_path)
    job = create_job(repo, store)
    outcome = process_next_job(
        repo=repo,
        artifact_store=store,
        provider=FakeTranscriptionProvider(),
    )

    skipped = process_job_by_id(
        repo=repo,
        artifact_store=store,
        provider=FakeTranscriptionProvider(),
        job_id=str(job["id"]),
    )

    assert outcome == ProcessOutcome.SUCCEEDED
    assert skipped == ProcessOutcome.SKIPPED


def test_no_queued_jobs_returns_cleanly(tmp_path: Path) -> None:
    repo, store = fixture(tmp_path)

    outcome = process_next_job(
        repo=repo,
        artifact_store=store,
        provider=FakeTranscriptionProvider(),
    )

    assert outcome == ProcessOutcome.NO_JOB
