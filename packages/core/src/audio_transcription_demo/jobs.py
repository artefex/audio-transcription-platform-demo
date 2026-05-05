from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from audio_transcription_demo.artifacts import ArtifactStore
from audio_transcription_demo.audio import sha256_hex, validate_wav_upload
from audio_transcription_demo.repository import JobRepository
from audio_transcription_demo.time import utc_now

IdempotencyMode = Literal["auto", "force_new"]


@dataclass(frozen=True)
class JobCreationResult:
    status_code: int
    job: dict[str, object]
    audio: dict[str, object]
    reused_job: bool
    reused_audio: bool


def create_job_from_upload(
    *,
    repo: JobRepository,
    artifact_store: ArtifactStore,
    data: bytes,
    filename: str,
    content_type: str | None,
    idempotency: IdempotencyMode,
) -> JobCreationResult:
    if idempotency not in {"auto", "force_new"}:
        raise ValueError("idempotency must be auto or force_new")
    validate_wav_upload(data, filename, content_type)

    digest = sha256_hex(data)
    if idempotency == "auto":
        reusable_job = repo.find_reusable_job_for_audio_hash(digest)
        if reusable_job is not None:
            audio = repo.get_audio_by_id(str(reusable_job["audio_artifact_id"]))
            if audio is None:
                raise RuntimeError("reusable job has no audio artifact")
            return JobCreationResult(
                status_code=200,
                job=reusable_job,
                audio=audio,
                reused_job=True,
                reused_audio=True,
            )

    existing_audio = repo.get_audio_by_sha256(digest)
    reused_audio = existing_audio is not None
    if existing_audio is None:
        created_at = utc_now()
        storage_path = artifact_store.write_audio(digest, data)
        _assert_path_under_root(storage_path, artifact_store.root)
        audio = repo.create_audio_artifact(
            sha256_hex=digest,
            original_filename=Path(filename).name,
            content_type=content_type or "audio/wav",
            storage_path=storage_path,
            size_bytes=len(data),
            created_at=created_at,
        )
    else:
        audio = existing_audio

    job = repo.create_job(
        audio_artifact_id=str(audio["id"]),
        status="queued",
        idempotency_key=digest if idempotency == "auto" else None,
        created_at=utc_now(),
    )
    return JobCreationResult(
        status_code=201,
        job=job,
        audio=audio,
        reused_job=False,
        reused_audio=reused_audio,
    )


def _assert_path_under_root(storage_path: str, root: Path) -> None:
    path = Path(storage_path).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError("artifact path is outside configured storage root")
