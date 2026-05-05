from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.engine import URL


@dataclass(frozen=True)
class Settings:
    database_host: str = "localhost"
    database_port: int = 5432
    database_name: str = "transcription_demo"
    database_user: str = "demo"
    database_password: str = "demo"
    artifact_root: Path = Path("./data/artifacts")
    worker_poll_interval_seconds: float = 2.0

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            database_host=os.getenv("DATABASE_HOST", "localhost"),
            database_port=int(os.getenv("DATABASE_PORT", "5432")),
            database_name=os.getenv("DATABASE_NAME", "transcription_demo"),
            database_user=os.getenv("DATABASE_USER", "demo"),
            database_password=os.getenv("DATABASE_PASSWORD", "demo"),
            artifact_root=Path(os.getenv("ARTIFACT_ROOT", "./data/artifacts")),
            worker_poll_interval_seconds=float(os.getenv("WORKER_POLL_INTERVAL_SECONDS", "2")),
        )

    def sqlalchemy_url(self) -> URL:
        return URL.create(
            "postgresql+psycopg",
            username=self.database_user,
            password=self.database_password,
            host=self.database_host,
            port=self.database_port,
            database=self.database_name,
        )


def build_settings() -> Settings:
    return Settings.from_env()
