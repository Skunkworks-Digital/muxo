"""Alembic environment configuration."""

from __future__ import annotations

from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlalchemy.engine import Connection
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from backend.db import Base, engine

config = context.config

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=str(engine.url),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:  # pragma: no cover - alembic bootstrap
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():  # pragma: no cover - alembic bootstrap
    run_migrations_offline()
else:
    run_migrations_online()

