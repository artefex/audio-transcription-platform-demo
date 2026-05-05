from __future__ import annotations

import logging
import time

from audio_transcription_demo.artifacts import LocalArtifactStore
from audio_transcription_demo.config import build_settings
from audio_transcription_demo.db import create_engine_for_url, create_schema
from audio_transcription_demo.provider import FakeTranscriptionProvider
from audio_transcription_demo.repository import JobRepository
from audio_transcription_demo.worker import ProcessOutcome, process_next_job

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("transcription-demo-worker")


def main() -> None:
    settings = build_settings()
    engine = create_engine_for_url(settings.sqlalchemy_url())
    create_schema(engine)
    repo = JobRepository(engine)
    artifact_store = LocalArtifactStore(settings.artifact_root)
    provider = FakeTranscriptionProvider()

    logger.info("worker_started fake_provider=true")
    while True:
        outcome = process_next_job(repo=repo, artifact_store=artifact_store, provider=provider)
        if outcome == ProcessOutcome.NO_JOB:
            time.sleep(settings.worker_poll_interval_seconds)
        else:
            logger.info("worker_outcome=%s", outcome.value)


if __name__ == "__main__":
    main()
