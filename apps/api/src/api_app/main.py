from __future__ import annotations

from pathlib import Path
from typing import Annotated, Literal

from audio_transcription_demo.artifacts import LocalArtifactStore
from audio_transcription_demo.config import build_settings
from audio_transcription_demo.db import create_engine_for_url, create_schema
from audio_transcription_demo.jobs import create_job_from_upload
from audio_transcription_demo.repository import JobRepository
from audio_transcription_demo.time import isoformat
from fastapi import FastAPI, File, HTTPException, Query, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.engine import Engine


def create_app(*, engine: Engine | None = None, artifact_root: Path | None = None) -> FastAPI:
    settings = build_settings()
    resolved_engine = engine or create_engine_for_url(settings.sqlalchemy_url())
    resolved_artifact_root = artifact_root or settings.artifact_root
    create_schema(resolved_engine)

    app = FastAPI(title="Audio Transcription Platform Demo")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.state.repository = JobRepository(resolved_engine)
    app.state.artifact_store = LocalArtifactStore(resolved_artifact_root)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/api/jobs")
    async def create_job(
        response: Response,
        file: Annotated[UploadFile, File()],
        idempotency: Annotated[Literal["auto", "force_new"], Query()] = "auto",
    ) -> dict[str, object]:
        data = await file.read()
        try:
            result = create_job_from_upload(
                repo=app.state.repository,
                artifact_store=app.state.artifact_store,
                data=data,
                filename=file.filename or "audio.wav",
                content_type=file.content_type,
                idempotency=idempotency,
            )
        except ValueError as exc:
            raise HTTPException(status_code=415, detail=str(exc)) from exc
        response.status_code = result.status_code
        return {
            "job": serialize_row(result.job),
            "audio": serialize_row(result.audio),
            "reused_job": result.reused_job,
            "reused_audio": result.reused_audio,
        }

    @app.get("/api/jobs/{job_id}")
    def get_job(job_id: str) -> dict[str, object]:
        job = app.state.repository.get_job(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="job not found")
        payload: dict[str, object] = {"job": serialize_row(job)}
        transcript_id = job.get("transcript_id")
        if transcript_id:
            transcript = app.state.repository.get_transcript(str(transcript_id))
            if transcript is not None:
                payload["transcript"] = serialize_row(transcript)
        return payload

    @app.get("/api/transcripts/{transcript_id}")
    def get_transcript(transcript_id: str) -> dict[str, object]:
        transcript = app.state.repository.get_transcript(transcript_id)
        if transcript is None:
            raise HTTPException(status_code=404, detail="transcript not found")
        return {"transcript": serialize_row(transcript)}

    return app


def serialize_row(row: dict[str, object]) -> dict[str, object]:
    return {key: isoformat(value) for key, value in row.items()}
