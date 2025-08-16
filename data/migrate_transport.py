import sqlite3

DB_PATH = "school.db"  # change if needed

def ensure_table(cur, create_sql):
    """Create table if it doesn't exist."""
    table_name = create_sql.split()[2]
    cur.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
    if not cur.fetchone():
        print(f"Creating table: {table_name}")
        cur.execute(create_sql)

def ensure_column(cur, table, column, col_type):
    """Add column if missing."""
    cur.execute(f"PRAGMA table_info({table})")
    cols = [row[1] for row in cur.fetchall()]
    if column not in cols:
        print(f"Adding column: {table}.{column}")
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")

def migrate():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # student_transport
    ensure_table(cur, """
        CREATE TABLE student_transport (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fk_route_id INTEGER,
            fk_student_id INTEGER,
            student_id TEXT,
            pickup_point TEXT,
            drop_point TEXT
        )
    """)
    ensure_column(cur, "student_transport", "fk_route_id", "INTEGER")
    ensure_column(cur, "student_transport", "fk_student_id", "INTEGER")
    ensure_column(cur, "student_transport", "student_id", "TEXT")
    ensure_column(cur, "student_transport", "pickup_point", "TEXT")
    ensure_column(cur, "student_transport", "drop_point", "TEXT")

    # transport_routes
    ensure_table(cur, """
        CREATE TABLE transport_routes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fk_school_id INTEGER,
            route_name TEXT,
            driver_name TEXT,
            driver_contact TEXT,
            vehicle_number TEXT,
            stops TEXT,
            timing TEXT
        )
    """)
    ensure_column(cur, "transport_routes", "fk_school_id", "INTEGER")
    ensure_column(cur, "transport_routes", "route_name", "TEXT")
    ensure_column(cur, "transport_routes", "driver_name", "TEXT")
    ensure_column(cur, "transport_routes", "driver_contact", "TEXT")
    ensure_column(cur, "transport_routes", "vehicle_number", "TEXT")
    ensure_column(cur, "transport_routes", "stops", "TEXT")
    ensure_column(cur, "transport_routes", "timing", "TEXT")

    # cafeteria_menu
    ensure_table(cur, """
        CREATE TABLE cafeteria_menu (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_name TEXT,
            price REAL,
            available INTEGER
        )
    """)
    ensure_column(cur, "cafeteria_menu", "item_name", "TEXT")
    ensure_column(cur, "cafeteria_menu", "price", "REAL")
    ensure_column(cur, "cafeteria_menu", "available", "INTEGER")

    # achievements
    ensure_table(cur, """
        CREATE TABLE achievements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT,
            title TEXT,
            description TEXT,
            date_awarded TEXT,
            awarded_by TEXT,
            file_url TEXT,
            timestamp TEXT
        )
    """)
    ensure_column(cur, "achievements", "student_id", "TEXT")
    ensure_column(cur, "achievements", "title", "TEXT")
    ensure_column(cur, "achievements", "description", "TEXT")
    ensure_column(cur, "achievements", "date_awarded", "TEXT")
    ensure_column(cur, "achievements", "awarded_by", "TEXT")
    ensure_column(cur, "achievements", "file_url", "TEXT")
    ensure_column(cur, "achievements", "timestamp", "TEXT")

    conn.commit()
    conn.close()
    print("✅ Migration completed successfully.")

if __name__ == "__main__":
    migrate()
