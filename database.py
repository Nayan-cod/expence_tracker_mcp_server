import os
import psycopg2
from psycopg2.extras import RealDictCursor

# Default connection string, override with environment variable
# Notice: database is now expence_trecker
DB_URL = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/expence_trecker")

def get_db():
    return psycopg2.connect(DB_URL, cursor_factory=RealDictCursor)

def add_column_if_not_exists(c, table, column, definition):
    c.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name='{table}' and column_name='{column}'")
    if not c.fetchone():
        c.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

def init_db():
    try:
        with get_db() as conn:
            with conn.cursor() as c:
                c.execute("""
                    CREATE TABLE IF NOT EXISTS expenses(
                        id SERIAL PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        date TEXT NOT NULL,
                        amount REAL NOT NULL,
                        category TEXT NOT NULL,
                        subcategory TEXT DEFAULT '',
                        note TEXT DEFAULT ''
                    )
                """)
                add_column_if_not_exists(c, 'expenses', 'user_id', "TEXT NOT NULL DEFAULT 'default_user'")
                
                c.execute("""
                    CREATE TABLE IF NOT EXISTS credits(
                        id SERIAL PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        date TEXT NOT NULL,
                        amount REAL NOT NULL,
                        source TEXT NOT NULL,
                        note TEXT DEFAULT ''
                    )
                """)
                add_column_if_not_exists(c, 'credits', 'user_id', "TEXT NOT NULL DEFAULT 'default_user'")
                
                c.execute("""
                    CREATE TABLE IF NOT EXISTS budgets(
                        id SERIAL PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        month TEXT NOT NULL,
                        category TEXT NOT NULL,
                        amount REAL NOT NULL,
                        UNIQUE(user_id, month, category)
                    )
                """)
                add_column_if_not_exists(c, 'budgets', 'user_id', "TEXT NOT NULL DEFAULT 'default_user'")
                # Recreate unique constraint if it was altered but that's complex, so we'll just ignore for now if it already existed.
            conn.commit()
    except psycopg2.OperationalError as e:
        print(f"Warning: Could not connect to PostgreSQL at startup. Please check DATABASE_URL. Details: {e}")

init_db()
