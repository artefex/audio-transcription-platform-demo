from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol


class ArtifactStore(Protocol):
    root: Path

    def write_audio(self, sha256_hex: str, data: bytes) -> str: ...

    def read_audio(self, storage_path: str) -> bytes: ...

    def write_transcript(
        self,
        transcript_id: str,
        text: str,
        payload: dict[str, object],
    ) -> tuple[str, str]: ...


class LocalArtifactStore:
    def __init__(self, root: Path | str) -> None:
        self.root = Path(root).resolve()
        self.audio_dir = self.root / "audio"
        self.transcript_dir = self.root / "transcripts"
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        self.transcript_dir.mkdir(parents=True, exist_ok=True)

    def write_audio(self, sha256_hex: str, data: bytes) -> str:
        path = self.audio_dir / f"{sha256_hex}.wav"
        path.write_bytes(data)
        return str(path)

    def read_audio(self, storage_path: str) -> bytes:
        path = self._resolve_under_root(storage_path)
        return path.read_bytes()

    def write_transcript(
        self,
        transcript_id: str,
        text: str,
        payload: dict[str, object],
    ) -> tuple[str, str]:
        text_path = self.transcript_dir / f"{transcript_id}.txt"
        json_path = self.transcript_dir / f"{transcript_id}.json"
        text_path.write_text(text, encoding="utf-8")
        json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        return str(text_path), str(json_path)

    def _resolve_under_root(self, storage_path: str) -> Path:
        path = Path(storage_path).resolve()
        if not path.is_relative_to(self.root):
            raise ValueError("artifact path is outside configured storage root")
        return path
