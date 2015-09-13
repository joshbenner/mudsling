import re
import os
import logging
import inspect
from urlparse import urlparse

import yoyo
import yoyo.connections

import sqlite3

import sqlalchemy.dialects as dialects
from sqlalchemy import table, column
import sqlalchemy

import schematics.types as schematics_types

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
    parsed_uri = yoyo.connections.parse_uri(db_uri)
    scheme, _, _, _, _, database, _ = parsed_uri
    if scheme == 'sqlite':
        directory = os.path.dirname(database)
        if not os.path.exists(directory):
            os.makedirs(directory)
    try:
        conn, paramstyle = yoyo.connections.connect(db_uri)
    except Exception:
        logging.debug('Failed migration URI: %s', db_uri)
        raise
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
        if cls.paramstyle is None and cls.dbapi_module is not None:
            mod = __import__(cls.dbapi_module)
            cls.paramstyle = mod.paramstyle
        if cls.dialect is None and cls.uri_scheme is not None:
            cls.dialect = dialects.registry.load(cls.uri_scheme)()
        DB_DRIVERS[cls.uri_scheme] = cls
        return cls


class DatabaseDriver(object):
    """
    A base delegate for handling specific database implementations. Used to
    implement strategy pattern by ExternalDatabase class.
    """
    __metaclass__ = DatabaseDriverMetaClass

    dbapi_module = None
    uri_scheme = None

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
            'cp_openfun': cls._configure_connection,
        }
        return (uri.path,), kw

    @staticmethod
    def _configure_connection(conn):
        conn.row_factory = sqlite3.Row
        conn.text_factory = str


class EntityRepository(object):
    """
    Base class for implementing entity repositories if leveraging the
    repository pattern.
    """
    _entity_factory = tuple

    def __init__(self, db):
        """
        :param db: The database to interact with.
        :type db: ExternalDatabase
        """
        self.db = db

    def all(self):
        """
        Get the list of all entities.

        :rtype: twisted.internet.defer.Deferred
        """
        raise NotImplementedError()

    def get(self, id, callback=None):
        """
        Wrapper around _get that accepts an callback and returns a deferred.

        :rtype: twisted.internet.defer.Deferred
        """
        d = self._get(id)
        if callable(self._entity_factory):
            d.addCallback(self._factory)
        d.addCallback(lambda results: results[0])
        if callable(callback):
            d.addCallback(callback)
        return d

    def _get(self, id):
        """
        Dispatch the actual get query.
        :rtype: twisted.internet.defer.Deferred
        """
        raise NotImplementedError()

    def _factory(self, entities):
        factory = self._entity_factory
        if not callable(factory):
            raise NotImplementedError()
        return [factory(entity) for entity in entities]

    def save(self, entity):
        """
        :param entity: The entity to insert/update.

        :rtype: twisted.internet.defer.Deferred
        """
        raise NotImplementedError()

    def delete(self, entity):
        """
        :param entity: The entity to delete.
        :rtype: twisted.internet.defer.Deferred
        """
        raise NotImplementedError()


class SchematicsModelRepository(EntityRepository):
    """
    A generic repository for storing models built atop the schematics Model
    class.
    """

    # The model handled by this repository.
    #: :type: schematics.Model
    model = None

    # The table that stores model instances.
    table = None

    # The field that acts as the id
    id_field = 'id'

    _schematics_to_sqlalchemy = {
        schematics_types.StringType: sqlalchemy.String,
        schematics_types.BooleanType: sqlalchemy.Boolean,
        schematics_types.NumberType: sqlalchemy.Numeric,
        schematics_types.IntType: sqlalchemy.Integer,
        schematics_types.LongType: sqlalchemy.BigInteger,
        schematics_types.FloatType: sqlalchemy.Float,
        schematics_types.DecimalType: sqlalchemy.DECIMAL,

        schematics_types.DateTimeType: sqlalchemy.DateTime,
        schematics_types.DateType: sqlalchemy.Date,

        schematics_types.HashType: sqlalchemy.String,
        schematics_types.MD5Type: sqlalchemy.String,
        schematics_types.SHA1Type: sqlalchemy.String,

        schematics_types.EmailType: sqlalchemy.String,
        schematics_types.URLType: sqlalchemy.String,
        schematics_types.IPv4Type: sqlalchemy.String,
        schematics_types.UUIDType: sqlalchemy.String
    }

    @classmethod
    def map_data_type(cls, schematics_type):
        """
        Map a schematics type to an SQLAlchemy type.
        """
        if not inspect.isclass(schematics_type):
            schematics_type = schematics_type.__class__
        type_map = cls._schematics_to_sqlalchemy
        sqla_type = getattr(schematics_type, 'sqlalchemy_type',
                            type_map.get(schematics_type, None))
        return sqla_type

    def column(self, field_name):
        return getattr(self.schema.c, field_name)

    col = column

    @property
    def id_column(self):
        return getattr(self.schema.c, self.id_field)

    @property
    def schema(self):
        if '_schema' not in self.__dict__:
            schema = table(self.table)
            for field_name, field_type in self.model.fields.iteritems():
                sqla_type = self.map_data_type(field_type)
                if sqla_type is None:
                    raise TypeError('Cannot find an SQLAlchemy type for %s.'
                                    % field_type.__class__.__name__)
                sql_name = field_type.serialized_name or field_name
                schema.append_column(column(sql_name, sqla_type))
            self._schema = schema
        return self._schema

    def _get(self, id):
        return self.db.query(self.schema.select().where(self.id_column == id))

    @property
    def _entity_factory(self):
        return self.model

    def _factory(self, entities):
        entities = map(dict, entities)
        return super(SchematicsModelRepository, self)._factory(entities)

    def save(self, entity):
        """
        :type entity: schematics.models.Model
        """
        id = getattr(entity, self.id_field, None)
        fields = entity.to_primitive()
        if id is None:
            d = self.db.insert(self.schema, **fields)
        else:
            id_col = self.id_column
            stmt = self.schema.update().values(**fields).where(id_col == id)
            d = self.db.operation(stmt)
        return d

    def delete(self, entity):
        """
        :type entity: schematics.models.Model
        """
        id = getattr(entity, self.id_field, None)
        assert id is not None
        stmt = self.schema.delete().where(self.id_column == id)
        return self.db.operation(stmt)

    @inlineCallbacks
    def all(self):
        results = yield self.db.query(self.schema.select())
        returnValue(self._factory(map(dict, results)))


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

    def _query_errback(self, error, sql=None, params=None):
        """
        :type error: twisted.python.failure.Failure
        :type sql: str
        :type params: tuple or dict
        """
        tb = error.getTracebackObject()
        exc_info = (error.type, error.value, tb)
        logging.debug(error.getErrorMessage(), exc_info=exc_info)
        if sql is not None:
            logging.debug('SQL failed: %s', sql)
        if params is not None:
            logging.debug('Params: %r', params)

    @inlineCallbacks
    def query(self, query, *a, **kw):
        """
        Query the database.

        :param query: The query object to run.
        :type query: sqlalchemy.sql.elements.ClauseElement

        :rtype: twisted.internet.defer.Deferred
        """
        sql, params = self.compile(query)
        d = self._pool.runQuery(sql, params, *a, **kw)
        d.addErrback(self._query_errback, sql, params)
        result = yield d
        returnValue(result)

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
        sql, params = self.compile(stmt)
        d = self._pool.runOperation(sql, params, *a, **kw)
        d.addErrback(self._query_errback, sql, params)
        return d

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
            params = tuple(compiled.params[p] for p in compiled.positiontup)
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
