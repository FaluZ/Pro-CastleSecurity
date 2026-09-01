from __future__ import annotations

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from pegazus.core.config import settings


class Base(DeclarativeBase):
    pass


engine = create_engine(
    f"sqlite:///{settings.db_path}",
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def _run_light_migrations() -> None:
    """Agrega columnas nuevas a tablas ya existentes (no hay Alembic en este proyecto)."""
    inspector = inspect(engine)
    if "scans" not in inspector.get_table_names():
        return

    existing_columns = {col["name"] for col in inspector.get_columns("scans")}
    if "files_total" not in existing_columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE scans ADD COLUMN files_total INTEGER DEFAULT 0"))


def init_db() -> None:
    from pegazus.core import models  # noqa: F401 - registra los modelos en Base.metadata

    Base.metadata.create_all(bind=engine)
    _run_light_migrations()
