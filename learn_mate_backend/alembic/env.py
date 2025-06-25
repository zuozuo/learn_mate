"""Alembic environment configuration."""

import os
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config
from sqlalchemy import pool
from sqlmodel import SQLModel

from alembic import context

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

# Import all models to ensure they're registered with SQLModel
from app.models.user import User  # noqa: E402
from app.models.session import Session  # noqa: E402
from app.models.thread import Thread  # noqa: E402
from app.models.conversation import Conversation  # noqa: E402
from app.models.chat_message import ChatMessage  # noqa: E402
from app.models.message_branch import MessageBranch  # noqa: E402

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set up metadata for autogenerate support
target_metadata = SQLModel.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    # Get database URL from environment variable
    url = os.getenv("POSTGRES_URL")
    if not url:
        raise ValueError("POSTGRES_URL environment variable not set")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    # Get database URL from environment variable
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = os.getenv("POSTGRES_URL")

    if not configuration["sqlalchemy.url"]:
        raise ValueError("POSTGRES_URL environment variable not set")

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
