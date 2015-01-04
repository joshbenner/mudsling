import yoyo
import yoyo.connections
import sqlite3


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


class ExternalDatabase(object):
    """
    Generic external database that handles its own connection, migrations, etc.

    :cvar migrations_path: Path to the migrations to execute against this kind
        of database.
    :type migrations_path: str
    """

    migrations_path = None

    def __init__(self):
        """
        Initialize the connection in child implementations.
        :return:
        """
        self.run_migrations(self.migrations_path)

    @property
    def db_uri(self):
        """
        A yoyo-migrations database URI for this database.
        :rtype: str
        """
        raise NotImplementedError()

    def run_migrations(self, migrations_path):
        """
        Execute migrations found at the specified path against this database.

        :param migrations_path: The filesystem path to the yoyo files.
        :type migrations_path: str
        """
        self._before_migration()
        migrate(self.db_uri, migrations_path)
        self._after_migration()

    def _before_migration(self):
        """
        Optional logic before migrations. Might be useful to disconnect.
        """
        pass

    def _after_migration(self):
        """
        Optional logic after migrations. Probably useful to reestablish
        connection.
        """
        pass


class SQLiteDB(ExternalDatabase):
    """
    Encapsulate the connection to an SQLite database.
    """

    def __init__(self, filepath):
        self.filepath = filepath
        self.connection = sqlite3.connect(filepath)
        super(SQLiteDB, self).__init__()

    @property
    def db_uri(self):
        return 'sqlite:///%s' % self.filepath
