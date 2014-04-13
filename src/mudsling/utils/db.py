import yoyo
import yoyo.connections


def migrate(db_uri, migrations_path):
    """
    Perform yoyo migrations on the specified database using the specified
    migrations repository.

    :param db_uri: The URI path to the SQLite database file. May be any
        format that can be passed to yoyo.connections.connect.
    :type db_uri: str
    :param migrations_path: Filesystem path to directory containing the yoyo
        migration files.
    :type migrations_path: str
    """
    conn, paramstyle = yoyo.connections.connect(db_uri)
    migrations = yoyo.read_migrations(conn, paramstyle, migrations_path)
    migrations.to_apply().apply()
    conn.commit()
    conn.close()

