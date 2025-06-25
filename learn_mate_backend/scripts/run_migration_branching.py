"""Run database migration for message branching feature."""

import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.database import DatabaseService
from app.core.config import get_settings


async def run_migration():
    """Run the message branching migration."""
    settings = get_settings()
    db_service = DatabaseService(settings.database_url)

    migration_file = Path(__file__).parent.parent / "migrations" / "add_message_branching.sql"

    if not migration_file.exists():
        print(f"Migration file not found: {migration_file}")
        return False

    try:
        print("Initializing database connection...")
        await db_service.init()

        print("Reading migration SQL...")
        with open(migration_file, "r") as f:
            migration_sql = f.read()

        print("Executing migration...")
        async with db_service.engine.begin() as conn:
            # Split SQL statements and execute them one by one
            statements = [stmt.strip() for stmt in migration_sql.split(";") if stmt.strip()]

            for i, statement in enumerate(statements):
                if statement:
                    print(f"Executing statement {i + 1}/{len(statements)}...")
                    await conn.execute(statement)

        print("Migration completed successfully!")
        return True

    except Exception as e:
        print(f"Migration failed: {e}")
        return False
    finally:
        await db_service.close()


if __name__ == "__main__":
    success = asyncio.run(run_migration())
    sys.exit(0 if success else 1)
