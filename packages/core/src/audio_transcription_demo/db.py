from __future__ import annotations

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, MetaData, Table, Text
from sqlalchemy.engine import URL, Engine, create_engine
from sqlalchemy.pool import StaticPool

metadata = MetaData()

audio_artifacts = Table(
    "audio_artifacts",
    metadata,
    Column("id", Text, primary_key=True),
    Column("sha256", Text, nullable=False, unique=True),
    Column("original_filename", Text, nullable=False),
    Column("content_type", Text, nullable=False),
    Column("storage_path", Text, nullable=False),
    Column("size_bytes", Integer, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
)

transcripts = Table(
    "transcripts",
    metadata,
    Column("id", Text, primary_key=True),
    Column("job_id", Text, nullable=False),
    Column("text", Text, nullable=False),
    Column("text_path", Text, nullable=False),
    Column("json_path", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
)

transcription_jobs = Table(
    "transcription_jobs",
    metadata,
    Column("id", Text, primary_key=True),
    Column("audio_artifact_id", Text, ForeignKey("audio_artifacts.id"), nullable=False),
    Column("status", Text, nullable=False),
    Column("attempts", Integer, nullable=False, default=0),
    Column("last_error", Text, nullable=True),
    Column("idempotency_key", Text, nullable=True),
    Column("transcript_id", Text, ForeignKey("transcripts.id"), nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)

Index("idx_audio_artifacts_sha256", audio_artifacts.c.sha256)
Index("idx_jobs_status_created", transcription_jobs.c.status, transcription_jobs.c.created_at)
Index("idx_jobs_audio_artifact", transcription_jobs.c.audio_artifact_id)


def create_engine_for_url(url: str | URL, *, echo: bool = False) -> Engine:
    url_text = str(url)
    connect_args = {"check_same_thread": False} if url_text.startswith("sqlite") else {}
    if url_text == "sqlite:///:memory:":
        return create_engine(
            url,
            echo=echo,
            future=True,
            connect_args=connect_args,
            poolclass=StaticPool,
        )
    return create_engine(url, echo=echo, future=True, connect_args=connect_args)


def create_schema(engine: Engine) -> None:
    metadata.create_all(engine)
