"""Script to check database triggers."""

import os
import psycopg2

# Get database URL from environment
postgres_url = os.getenv("POSTGRES_URL", "postgresql://zuozuo:@localhost:5432/learn_mate_dev")

# Connect to database
conn = psycopg2.connect(postgres_url)
cur = conn.cursor()

try:
    # Check triggers
    cur.execute("""
        SELECT 
            t.tgname AS trigger_name,
            c.relname AS table_name,
            p.proname AS function_name
        FROM pg_trigger t
        JOIN pg_class c ON t.tgrelid = c.oid
        JOIN pg_proc p ON t.tgfoid = p.oid
        WHERE t.tgisinternal = false
        AND c.relnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public')
        ORDER BY c.relname, t.tgname;
    """)

    triggers = cur.fetchall()

    print("Database Triggers:")
    print("-" * 60)
    print(f"{'Trigger Name':<40} {'Table':<20}")
    print("-" * 60)
    for trigger in triggers:
        print(f"{trigger[0]:<40} {trigger[1]:<20}")
    print("-" * 60)
    print(f"Total triggers: {len(triggers)}")

    # Check functions
    print("\nDatabase Functions:")
    print("-" * 40)
    cur.execute("""
        SELECT proname 
        FROM pg_proc 
        WHERE pronamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public')
        ORDER BY proname;
    """)

    functions = cur.fetchall()
    for func in functions:
        print(f"  {func[0]}")
    print("-" * 40)
    print(f"Total functions: {len(functions)}")

    # Check constraints
    print("\nCheck Constraints:")
    print("-" * 60)
    cur.execute("""
        SELECT 
            conname AS constraint_name,
            conrelid::regclass AS table_name,
            pg_get_constraintdef(oid) AS definition
        FROM pg_constraint
        WHERE contype = 'c'
        AND connamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public')
        ORDER BY conrelid::regclass::text, conname;
    """)

    constraints = cur.fetchall()
    for constraint in constraints:
        print(f"{constraint[0]}: {constraint[1]} - {constraint[2]}")
    print("-" * 60)
    print(f"Total check constraints: {len(constraints)}")

finally:
    cur.close()
    conn.close()
