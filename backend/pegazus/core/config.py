from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    app_name: str = "Proyecto-Pegazus"
    backend_dir: Path = Path(__file__).resolve().parent.parent.parent
    db_path: Path = field(default_factory=lambda: Path(__file__).resolve().parent.parent.parent / "pegazus.db")
    max_file_size_bytes: int = 25 * 1024 * 1024
    excluded_dir_names: frozenset[str] = frozenset(
        {
            ".git",
            "node_modules",
            "venv",
            ".venv",
            "__pycache__",
            "dist",
            "build",
            ".mypy_cache",
            ".pytest_cache",
        }
    )
    cors_origins: tuple[str, ...] = ("http://localhost:5173", "http://127.0.0.1:5173")
    jsbridge_url: str = "http://localhost:4100"


settings = Settings()
