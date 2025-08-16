"""Database setup using SQLAlchemy with optional SQLCipher support."""

from __future__ import annotations

import os

from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker


DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./muxo.db")

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)

SQLCIPHER_KEY = os.getenv("SQLCIPHER_KEY")

if SQLCIPHER_KEY:

    @event.listens_for(engine, "connect")
    def _set_sqlcipher_key(dbapi_connection, connection_record) -> None:  # pragma: no cover - simple pragma
        cursor = dbapi_connection.cursor()
        cursor.execute(f"PRAGMA key='{SQLCIPHER_KEY}';")
        cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_session():
    """FastAPI dependency that yields a SQLAlchemy session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

