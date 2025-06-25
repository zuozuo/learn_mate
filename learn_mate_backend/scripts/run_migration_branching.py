"""Run database migration for message branching feature."""

import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlmodel import text

from app.services.database import DatabaseService
from app.core.config import settings


def run_migration():
    """Run the message branching migration."""
    db_service = DatabaseService()

    migration_file = Path(__file__).parent.parent / "migrations" / "add_message_branching.sql"

    if not migration_file.exists():
        print(f"Migration file not found: {migration_file}")
        return False

    try:
        print("Database connection initialized...")

        print("Reading migration SQL...")
        with open(migration_file, "r") as f:
            migration_sql = f.read()

        print("Executing migration...")
        with db_service.engine.begin() as conn:
            # Execute the entire migration as one block to handle multi-line statements correctly
            conn.execute(text(migration_sql))

        print("Migration completed successfully!")
        return True

    except Exception as e:
        print(f"Migration failed: {e}")
        return False
    finally:
        db_service.engine.dispose()


if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)
