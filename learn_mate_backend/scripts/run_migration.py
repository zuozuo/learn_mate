#!/usr/bin/env python3
"""Run database migration directly without alembic command line."""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from app.core.config import settings  # noqa: E402


def run_migration():
    """Run the database migration."""
    # Create alembic config
    alembic_cfg = Config(str(project_root / "alembic.ini"))

    # Set the database URL in the config
    alembic_cfg.set_main_option("sqlalchemy.url", settings.POSTGRES_URL)

    # Run the migration
    print("Running migration to latest version...")
    command.upgrade(alembic_cfg, "head")
    print("Migration completed successfully!")


if __name__ == "__main__":
    run_migration()
