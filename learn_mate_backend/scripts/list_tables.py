"""Script to list all tables in the database."""

import os
import psycopg2

# Get database URL from environment
postgres_url = os.getenv("POSTGRES_URL", "postgresql://zuozuo:@localhost:5432/learn_mate_dev")

# Connect to database
conn = psycopg2.connect(postgres_url)
cur = conn.cursor()

try:
    # Get all table names
    cur.execute("""
        SELECT tablename 
        FROM pg_tables 
        WHERE schemaname = 'public'
        ORDER BY tablename
    """)

    tables = cur.fetchall()

    print("Tables in database:")
    print("-" * 30)
    for table in tables:
        print(f"  {table[0]}")
    print("-" * 30)
    print(f"Total tables: {len(tables)}")

finally:
    cur.close()
    conn.close()
