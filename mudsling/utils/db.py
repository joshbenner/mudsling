from urlparse import urlparse

import yoyo
import yoyo.connections
import sqlite3
from twisted.enterprise import adbapi
from twisted.internet.defer import inlineCallbacks, returnValue


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


class DatabaseDriver(object):
    """
    A base delegate for handling specific database implementations. Used to
    implement strategy pattern by ExternalDatabase class.
    """
    dbapi_module = ''
    uri_scheme = ''

    def __new__(cls, *args, **kwargs):
        raise RuntimeError('Cannot instantiate static class.')

    @classmethod
    def connect(cls, uri):
        """
        Generate a Twisted ADAPI connection pool and return it.
        """
        a, kw = cls._connect_parameters(uri)
        return adbapi.ConnectionPool(cls.dbapi_module, *a, **kw)

    @classmethod
    def _connect_parameters(cls, uri):
        """
        Return the positional and keyword arguments to pass to the connect
        method for the database connection.

        :rtype: tuple of (tuple, dict)
        """
        raise NotImplementedError()


class SQLiteDriver(DatabaseDriver):
    """
    Encapsulate the connection to an SQLite database.
    """
    dbapi_module = 'sqlite3'
    uri_scheme = 'sqlite'

    @classmethod
    def _connect_parameters(cls, uri):
        parsed = urlparse(uri)
        kw = {
            'check_same_thread': False,
            'cp_openfun': cls._set_row_factory
        }
        return (parsed.path,), kw

    @staticmethod
    def _set_row_factory(conn):
        conn.row_factory = sqlite3.Row


class ExternalDatabase(object):
    """
    Generic external database that handles its own connection, migrations, etc.

    :cvar migrations_path: Path to the migrations to execute against this kind
        of database.
    :type migrations_path: str
    """

    migrations_path = None
    _dbtype = None
    _pool = None

    def __init__(self, *a, **kw):
        """
        Initialize the connection in child implementations.
        :return:
        """
        self.run_migrations(self.migrations_path)
        self.connect(*a, **kw)

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

    def connect(self, *a, **kw):
        self._pool = adbapi.ConnectionPool(self._dbtype, *a, **kw)

    @inlineCallbacks
    def query(self, sql, *a, **kw):
        result = yield self._pool.runQuery(sql, *a, **kw)
        returnValue(result)


class SQLiteDB(ExternalDatabase):
    """
    Encapsulate the connection to an SQLite database.
    """
    _dbtype = 'sqlite3'

    def __init__(self, filepath, *a, **kw):
        self.filepath = filepath
        super(SQLiteDB, self).__init__(filepath, *a, **kw)

    @property
    def db_uri(self):
        return 'sqlite:///%s' % self.filepath

    def connect(self, *a, **kw):
        kw['check_same_thread'] = False
        kw['cp_openfun'] = self._set_row_factory
        return super(SQLiteDB, self).connect(*a, **kw)

    @staticmethod
    def _set_row_factory(conn):
        conn.row_factory = sqlite3.Row
