from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from uuid import uuid4

from sqlalchemy import and_, insert, join, select, update
from sqlalchemy.engine import Engine

from audio_transcription_demo.db import audio_artifacts, transcription_jobs, transcripts
from audio_transcription_demo.time import utc_now

ACTIVE_OR_DONE = {"queued", "processing", "succeeded"}
TERMINAL_STATUSES = {"succeeded", "failed"}


def new_id(prefix: str) -> str:
    return f"{prefix}{uuid4().hex}"


class JobRepository:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def get_audio_by_sha256(self, sha256_hex: str) -> dict[str, object] | None:
        stmt = select(audio_artifacts).where(audio_artifacts.c.sha256 == sha256_hex)
        with self.engine.connect() as conn:
            row = conn.execute(stmt).mappings().one_or_none()
        return dict(row) if row else None

    def get_audio_by_id(self, audio_id: str) -> dict[str, object] | None:
        stmt = select(audio_artifacts).where(audio_artifacts.c.id == audio_id)
        with self.engine.connect() as conn:
            row = conn.execute(stmt).mappings().one_or_none()
        return dict(row) if row else None

    def create_audio_artifact(
        self,
        *,
        sha256_hex: str,
        original_filename: str,
        content_type: str,
        storage_path: str,
        size_bytes: int,
        created_at: datetime,
    ) -> dict[str, object]:
        audio_id = new_id("aud_")
        stmt = insert(audio_artifacts).values(
            id=audio_id,
            sha256=sha256_hex,
            original_filename=original_filename,
            content_type=content_type,
            storage_path=storage_path,
            size_bytes=size_bytes,
            created_at=created_at,
        )
        with self.engine.begin() as conn:
            conn.execute(stmt)
        audio = self.get_audio_by_id(audio_id)
        if audio is None:
            raise RuntimeError("audio artifact was not created")
        return audio

    def find_reusable_job_for_audio_hash(self, sha256_hex: str) -> dict[str, object] | None:
        joined = join(
            transcription_jobs,
            audio_artifacts,
            transcription_jobs.c.audio_artifact_id == audio_artifacts.c.id,
        )
        stmt = (
            select(transcription_jobs)
            .select_from(joined)
            .where(
                and_(
                    audio_artifacts.c.sha256 == sha256_hex,
                    transcription_jobs.c.status.in_(ACTIVE_OR_DONE),
                )
            )
            .order_by(transcription_jobs.c.created_at.asc())
            .limit(1)
        )
        with self.engine.connect() as conn:
            row = conn.execute(stmt).mappings().one_or_none()
        return dict(row) if row else None

    def create_job(
        self,
        *,
        audio_artifact_id: str,
        status: str,
        idempotency_key: str | None,
        created_at: datetime,
    ) -> dict[str, object]:
        job_id = new_id("job_")
        stmt = insert(transcription_jobs).values(
            id=job_id,
            audio_artifact_id=audio_artifact_id,
            status=status,
            attempts=0,
            last_error=None,
            idempotency_key=idempotency_key,
            transcript_id=None,
            created_at=created_at,
            updated_at=created_at,
        )
        with self.engine.begin() as conn:
            conn.execute(stmt)
        job = self.get_job(job_id)
        if job is None:
            raise RuntimeError("job was not created")
        return job

    def get_job(self, job_id: str) -> dict[str, object] | None:
        stmt = select(transcription_jobs).where(transcription_jobs.c.id == job_id)
        with self.engine.connect() as conn:
            row = conn.execute(stmt).mappings().one_or_none()
        return dict(row) if row else None

    def get_transcript(self, transcript_id: str) -> dict[str, object] | None:
        stmt = select(transcripts).where(transcripts.c.id == transcript_id)
        with self.engine.connect() as conn:
            row = conn.execute(stmt).mappings().one_or_none()
        return dict(row) if row else None

    def claim_next_job(self) -> dict[str, object] | None:
        now = utc_now()
        stmt = (
            select(transcription_jobs)
            .where(transcription_jobs.c.status == "queued")
            .order_by(transcription_jobs.c.created_at.asc())
            .limit(1)
        )
        with self.engine.begin() as conn:
            if conn.dialect.name == "postgresql":
                stmt = stmt.with_for_update(skip_locked=True)
            row = conn.execute(stmt).mappings().one_or_none()
            if row is None:
                return None
            conn.execute(
                update(transcription_jobs)
                .where(transcription_jobs.c.id == row["id"])
                .values(
                    status="processing",
                    attempts=int(row["attempts"]) + 1,
                    updated_at=now,
                )
            )
        claimed = dict(row)
        claimed["status"] = "processing"
        claimed["attempts"] = int(claimed["attempts"]) + 1
        claimed["updated_at"] = now
        return claimed

    def claim_job(self, job_id: str) -> dict[str, object] | None:
        now = utc_now()
        stmt = (
            select(transcription_jobs)
            .where(
                and_(
                    transcription_jobs.c.id == job_id,
                    transcription_jobs.c.status == "queued",
                )
            )
            .limit(1)
        )
        with self.engine.begin() as conn:
            if conn.dialect.name == "postgresql":
                stmt = stmt.with_for_update(skip_locked=True)
            row = conn.execute(stmt).mappings().one_or_none()
            if row is None:
                return None
            conn.execute(
                update(transcription_jobs)
                .where(transcription_jobs.c.id == row["id"])
                .values(
                    status="processing",
                    attempts=int(row["attempts"]) + 1,
                    updated_at=now,
                )
            )
        claimed = dict(row)
        claimed["status"] = "processing"
        claimed["attempts"] = int(claimed["attempts"]) + 1
        claimed["updated_at"] = now
        return claimed

    def create_transcript(
        self,
        *,
        job_id: str,
        text: str,
        text_path: str,
        json_path: str,
        created_at: datetime,
    ) -> dict[str, object]:
        transcript_id = new_id("trn_")
        stmt = insert(transcripts).values(
            id=transcript_id,
            job_id=job_id,
            text=text,
            text_path=text_path,
            json_path=json_path,
            created_at=created_at,
        )
        with self.engine.begin() as conn:
            conn.execute(stmt)
        transcript = self.get_transcript(transcript_id)
        if transcript is None:
            raise RuntimeError("transcript was not created")
        return transcript

    def mark_succeeded(self, job_id: str, transcript_id: str) -> dict[str, object]:
        return self._update_job(
            job_id,
            {
                "status": "succeeded",
                "transcript_id": transcript_id,
                "last_error": None,
                "updated_at": utc_now(),
            },
        )

    def mark_failed(self, job_id: str, last_error: str) -> dict[str, object]:
        return self._update_job(
            job_id,
            {
                "status": "failed",
                "last_error": last_error,
                "updated_at": utc_now(),
            },
        )

    def _update_job(self, job_id: str, values: Mapping[str, object]) -> dict[str, object]:
        stmt = update(transcription_jobs).where(transcription_jobs.c.id == job_id).values(**values)
        with self.engine.begin() as conn:
            conn.execute(stmt)
        job = self.get_job(job_id)
        if job is None:
            raise RuntimeError("job not found after update")
        return job
