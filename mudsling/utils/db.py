import re
from urlparse import urlparse

import yoyo
import yoyo.connections

import sqlite3

import sqlalchemy.dialects as dialects

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


DB_DRIVERS = {}


class DatabaseDriverMetaClass(type):
    """
    A meta-class to auto-register data driver classes.
    """
    def __new__(mcs, name, bases, dct):
        cls = super(DatabaseDriverMetaClass, mcs).__new__(mcs, name, bases, dct)
        mod = __import__(cls.dbapi_module)
        if cls.paramstyle is None:
            cls.paramstyle = mod.paramstyle
        if cls.dialect is None:
            cls.dialect = dialects.registry.load(cls.uri_scheme)()
        DB_DRIVERS[cls.uri_scheme] = cls
        return cls


class DatabaseDriver(object):
    """
    A base delegate for handling specific database implementations. Used to
    implement strategy pattern by ExternalDatabase class.
    """
    __metaclass__ = DatabaseDriverMetaClass

    dbapi_module = ''
    uri_scheme = ''

    #: :type: sqlalchemy.engine.interfaces.Dialect
    dialect = None  # Set to dialect instance, or metaclass will do for you.

    # Set by metaclass based on dbapi_module if None.
    paramstyle = None

    def __new__(cls, *args, **kwargs):
        raise RuntimeError('Cannot instantiate static class.')

    @classmethod
    def connect(cls, uri):
        """
        Generate a Twisted ADAPI connection pool and return it.

        :type uri: urlparse.ParseResult
        """
        a, kw = cls._connect_parameters(uri)
        return adbapi.ConnectionPool(cls.dbapi_module, *a, **kw)

    @classmethod
    def _connect_parameters(cls, uri):
        """
        Return the positional and keyword arguments to pass to the connect
        method for the database connection.

        :type uri: urlparse.ParseResult

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
        kw = {
            'check_same_thread': False,
            'cp_openfun': cls._set_row_factory
        }
        return (uri.path,), kw

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
    _uri = None

    _yoyo_uri_re = re.compile(r'^([^:]+):/(?!/)')

    tables = {}

    def __init__(self, uri):
        """
        Initialize the connection in child implementations.
        :return:
        """
        self._uri = urlparse(uri)
        if self.migrations_path is not None:
            self.run_migrations(self.migrations_path)
        self.connect()

    def run_migrations(self, migrations_path):
        """
        Execute migrations found at the specified path against this database.

        :param migrations_path: The filesystem path to the yoyo files.
        :type migrations_path: str
        """
        self._before_migration()
        # Yoyo URIs are so broken.
        uri = self._yoyo_uri_re.sub(r'\1:////', self._uri.geturl())
        migrate(uri, migrations_path)
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

    def connect(self):
        self._pool = self.db_driver.connect(self._uri)

    @property
    def db_driver(self):
        """:rtype: DatabaseDriver"""
        return DB_DRIVERS[self._uri.scheme]

    @property
    def dialect(self):
        """:rtype: sqlalchemy.engine.interfaces.Dialect"""
        return self.db_driver.dialect

    @inlineCallbacks
    def query(self, query, *a, **kw):
        """
        Query the database in a way that does not require callbacks.

        This is the easiest way to get data out of the database without having
        to write complicated callback chains.

        :param query: The query object to run.
        :type query: sqlalchemy.sql.elements.ClauseElement
        """
        sql, params = self.compile(query)
        result = yield self._pool.runQuery(sql, params, *a, **kw)
        returnValue(result)

    def deferred_query(self, query, *a, **kw):
        """
        Query the database asynchronously.

        Useful when you need more control over a Deferred callback chain on the
        query.

        :param query: The query object to run.
        :type query: sqlalchemy.sql.elements.ClauseElement

        :rtype: twisted.internet.defer.Deferred
        """
        sql, params = self.compile(query)
        return self._pool.runQuery(sql, params, *a, **kw)

    def interaction(self, interaction, *a, **kw):
        """
        Defer the run of the interaction callable in a thread.

        The result of the interaction function becomes the result of the
        Deferred that is returned from this method, useable in subsequent
        callbacks chained on the Deferred.

        See: twisted.enterprise.adbapi.ConnectionPool.runInteraction

        :param interaction: A callable whose first argument will be a
            transaction. Positional and keyword arguments are sent as well.

        :rtype: twisted.internet.defer.Deferred
        """
        return self._pool.runInteraction(interaction, *a, **kw)

    def operation(self, stmt, *a, **kw):
        """
        Run an SQL statement whose results we don't care about (ie: writes).

        :param stmt: The SQL statement to run.
        :type stmt: sqlalchemy.sql.elements.ClauseElement

        :rtype: twisted.internet.defer.Deferred
        """
        return self._pool.runOperation(*self.compile(stmt), *a, **kw)

    def table(self, name):
        return self.tables[name]

    def compile(self, stmt):
        """
        Compiles an SQLAlchemy statement.

        :param stmt: The statement to compile.
        :type stmt: sqlalchemy.sql.elements.ClauseElement

        :return: The SQL string and parameters to pass for execution.
        """
        # noinspection PyArgumentList
        compiled = stmt.compile(dialect=self.dialect)
        sql = str(compiled)
        if self.dialect.positional:
            params = compiled.positiontup
        else:
            params = compiled.params
        return sql, params

    def insert(self, table, **kw):
        """
        Convenience insert of a single row to the specified table.

        Executes as an operation, returning no value.

        :param table: The table to insert into.
        :param kw: The columns to insert and their values.

        :rtype: twisted.internet.defer.Deferred
        """
        return self.operation(table.insert().values(**kw))


class UsesExternalDatabase(object):
    """
    Mixin class to help other objects use external databases in consistent ways.
    """
    _db_class = ExternalDatabase
    _db_uri = None
    _db = None

    def _init_db(self):
        """
        Create the database connection pool.
        """
        if self._db is None:
            self._db = self._db_class(self._db_uri)
