from yoyo import step


def create_tables(conn):
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE log (
            timestamp INTEGER,
            source TEXT,
            text TEXT
        );
    """)

step(create_tables)
