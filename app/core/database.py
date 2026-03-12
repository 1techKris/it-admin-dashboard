from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base


# -----------------------------------------------------------------------------
# Helpers to build a correct, absolute SQLite URL
# -----------------------------------------------------------------------------
def _build_absolute_sqlite_url(db_path: Path) -> str:
    """
    Return a SQLAlchemy-compatible absolute SQLite URL.
    Example: sqlite:////home/administrator/it-admin-dashboard/test.db
    """
    db_path = db_path.resolve()
    # Note: for absolute paths SQLAlchemy expects 4 slashes after 'sqlite:'
    return f"sqlite:///{db_path.as_posix()}"  # yields sqlite:////... on POSIX


def _normalize_sqlite_url(url: str, project_root: Path) -> str:
    """
    Normalize a sqlite URL. If it points to a relative file, anchor it to project_root.
    Ensures correct number of slashes for absolute paths.
    """
    if not url.lower().startswith("sqlite"):
        return url

    # Strip driver prefix
    prefix = "sqlite:///"
    raw = url[len(prefix):] if url.startswith(prefix) else url.split("sqlite:", 1)[-1].lstrip("/")

    # If raw starts with '/', it's already absolute
    if raw.startswith("/"):
        return f"sqlite:///{raw}"

    # Otherwise treat as relative to project root
    abs_path = (project_root / raw).resolve()
    return _build_absolute_sqlite_url(abs_path)


# -----------------------------------------------------------------------------
# Resolve the effective DATABASE_URL with the following precedence:
#   1) Environment var: SQLALCHEMY_DATABASE_URI
#   2) app.core.config.settings.SQLALCHEMY_DATABASE_URI (if available)
#   3) Default absolute path: <project_root>/test.db
# -----------------------------------------------------------------------------
def _resolve_database_url() -> str:
    # project_root = <repo_root>, e.g. /home/administrator/it-admin-dashboard
    # current file is app/core/database.py  -> parents[2] = project_root
    project_root = Path(__file__).resolve().parents[2]

    # 1) env var
    env_url: Optional[str] = os.getenv("SQLALCHEMY_DATABASE_URI")

    # 2) settings (optional)
    settings_url: Optional[str] = None
    try:
        from app.core.config import settings  # optional import
        settings_url = getattr(settings, "SQLALCHEMY_DATABASE_URI", None)
    except Exception:
        pass

    # 3) default absolute sqlite file under project root
    default_sqlite_url = _build_absolute_sqlite_url(project_root / "test.db")

    chosen = env_url or settings_url or default_sqlite_url

    # Normalize sqlite URL to ensure absolute path (avoid duplicates across CWDs/systemd)
    if chosen.lower().startswith("sqlite"):
        return _normalize_sqlite_url(chosen, project_root)

    return chosen


DATABASE_URL = _resolve_database_url()

# SQLite needs special connect args; others usually don't
connect_args = {"check_same_thread": False} if DATABASE_URL.lower().startswith("sqlite") else {}

engine = create_engine(
    DATABASE_URL,
    future=True,
    echo=False,
    connect_args=connect_args,
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    future=True,
)

Base = declarative_base()


# -----------------------------------------------------------------------------
# FastAPI dependency
# -----------------------------------------------------------------------------
def get_db():
    """
    Usage:
        db: Session = Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()