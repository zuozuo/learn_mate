"""Script to drop all tables in the database."""

import os
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Get database URL from environment
postgres_url = os.getenv("POSTGRES_URL", "postgresql://zuozuo:@localhost:5432/learn_mate_dev")

# Parse connection details
conn = psycopg2.connect(postgres_url)
conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
cur = conn.cursor()

try:
    # Get all table names
    cur.execute("""
        SELECT tablename 
        FROM pg_tables 
        WHERE schemaname = 'public'
    """)

    tables = cur.fetchall()

    # Drop all tables
    for table in tables:
        table_name = table[0]
        print(f"Dropping table: {table_name}")
        cur.execute(f'DROP TABLE IF EXISTS "{table_name}" CASCADE')

    # Get all custom types (enums, etc.)
    cur.execute("""
        SELECT typname 
        FROM pg_type 
        WHERE typnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public')
        AND typtype = 'e'
    """)

    types = cur.fetchall()

    # Drop all custom types
    for type_name in types:
        print(f"Dropping type: {type_name[0]}")
        cur.execute(f'DROP TYPE IF EXISTS "{type_name[0]}" CASCADE')

    print("All tables and types dropped successfully!")

finally:
    cur.close()
    conn.close()
