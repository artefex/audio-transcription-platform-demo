from __future__ import annotations

from pathlib import Path

from api_app.main import create_app
from audio_transcription_demo.db import create_engine_for_url
from fastapi.testclient import TestClient


def wav_bytes() -> bytes:
    return b"RIFF\x24\x00\x00\x00WAVEfmt " + b"\x00" * 32


def client(tmp_path: Path) -> TestClient:
    engine = create_engine_for_url("sqlite:///:memory:")
    app = create_app(engine=engine, artifact_root=tmp_path / "artifacts")
    return TestClient(app)


def test_duplicate_upload_auto_reuses_existing_job(tmp_path: Path) -> None:
    test_client = client(tmp_path)
    files = {"file": ("sample.wav", wav_bytes(), "audio/wav")}
    first = test_client.post("/api/jobs", files=files)
    second = test_client.post("/api/jobs", files=files)

    assert first.status_code == 201
    assert second.status_code == 200
    assert second.json()["reused_job"] is True
    assert second.json()["job"]["id"] == first.json()["job"]["id"]


def test_duplicate_upload_force_new_reuses_audio_but_creates_job(tmp_path: Path) -> None:
    test_client = client(tmp_path)
    files = {"file": ("sample.wav", wav_bytes(), "audio/wav")}
    first = test_client.post("/api/jobs", files=files)
    second = test_client.post("/api/jobs?idempotency=force_new", files=files)

    assert first.status_code == 201
    assert second.status_code == 201
    assert second.json()["reused_job"] is False
    assert second.json()["reused_audio"] is True
    assert second.json()["audio"]["id"] == first.json()["audio"]["id"]
    assert second.json()["job"]["id"] != first.json()["job"]["id"]


def test_non_wav_upload_rejected(tmp_path: Path) -> None:
    test_client = client(tmp_path)
    files = {"file": ("note.txt", b"not audio", "text/plain")}

    response = test_client.post("/api/jobs", files=files)

    assert response.status_code == 415


def test_artifact_path_is_under_configured_storage_root(tmp_path: Path) -> None:
    test_client = client(tmp_path)
    files = {"file": ("sample.wav", wav_bytes(), "audio/wav")}

    response = test_client.post("/api/jobs", files=files)

    storage_path = Path(response.json()["audio"]["storage_path"]).resolve()
    assert storage_path.is_relative_to((tmp_path / "artifacts").resolve())
