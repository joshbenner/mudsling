import re
import os
import logging
import inspect
from urlparse import urlparse

import yoyo
import yoyo.connections

import sqlite3
import unqlite

import sqlalchemy.dialects as dialects
from sqlalchemy import table, column
from sqlalchemy.sql import not_, and_, or_
import sqlalchemy

import schematics.types as schematics_types

from twisted.enterprise import adbapi
from twisted.internet.defer import inlineCallbacks, returnValue

import mudsling.errors
from mudsling.utils.object import dict_inherit
from mudsling.utils import specifications as specs


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
    pending = migrations.to_apply()
    if len(pending):
        logging.info('Applying %s migrations to %s' % (len(pending), db_uri))
        pending.apply()
    conn.commit()
    conn.close()


DB_DRIVERS = {}


class DatabaseDriverMetaClass(type):
    """
    A meta-class to auto-register data driver classes.
    """
    def __new__(mcs, name, bases, dct):
        cls = super(DatabaseDriverMetaClass, mcs).__new__(mcs, name, bases, dct)
        cls.init_driver()
        DB_DRIVERS[cls.uri_scheme] = cls
        return cls


class DatabaseDriver(object):
    """
    A base delegate for handling specific database implementations. Used to
    implement strategy pattern by ExternalDatabase class.
    """
    __metaclass__ = DatabaseDriverMetaClass

    uri_scheme = None

    def __new__(cls, *args, **kwargs):
        raise RuntimeError('Cannot instantiate static class.')

    @classmethod
    def init_driver(cls):
        """
        Called by metaclass to do any setup of the driver itself.
        """
        pass

    @classmethod
    def connect(cls, uri):
        """
        Connect to the database.

        :return: A connection object.
        """
        raise NotImplementedError()


class DocumentCollection(object):
    """
    Generic interface to a simple document collection.
    """
    def all(self):
        raise NotImplementedError()

    def filter(self, filter_fn):
        raise NotImplementedError()

    def last_record_id(self):
        raise NotImplementedError()

    def __len__(self):
        raise NotImplementedError()

    def __index__(self):
        raise NotImplementedError()

    def store(self, record):
        raise NotImplementedError()

    def fetch(self, record_id):
        raise NotImplementedError()

    def update(self, record_id, record):
        raise NotImplementedError()

    def delete(self, record_id):
        raise NotImplementedError()


class NoSQLDatabaseDriver(DatabaseDriver):
    """
    Generic driver for NoSQL databases.
    """

    @classmethod
    def store(cls, conn, key, value):
        raise NotImplementedError()

    @classmethod
    def fetch(cls, conn, key):
        raise NotImplementedError()

    @classmethod
    def delete(cls, conn, key):
        raise NotImplementedError()

    @classmethod
    def exists(cls, conn, key):
        """:rtype: bool"""
        raise NotImplementedError()

    @classmethod
    def iterkeys(cls, conn):
        """:returns: Key generator"""
        raise NotImplementedError()

    @classmethod
    def itervalues(cls, conn):
        """:returns: Value generator"""
        raise NotImplementedError()

    @classmethod
    def iteritems(cls, conn):
        """:returns: (key, value) generator"""
        raise NotImplementedError

    @classmethod
    def collection(cls, conn, name):
        """:rtype: DocumentCollection"""
        raise NotImplementedError()


class UnQliteDriver(NoSQLDatabaseDriver):
    uri_scheme = 'unqlite'

    @classmethod
    def connect(cls, uri):
        return unqlite.UnQLite(uri)

    @classmethod
    def store(cls, conn, key, value):
        return conn.store(key, value)

    @classmethod
    def fetch(cls, conn, key):
        return conn.fetch(key)

    @classmethod
    def delete(cls, conn, key):
        return conn.delete(key)

    @classmethod
    def exists(cls, conn, key):
        return conn.exists(key)

    @classmethod
    def iterkeys(cls, conn):
        return conn.keys()

    @classmethod
    def itervalues(cls, conn):
        return conn.values()

    @classmethod
    def iteritems(cls, conn):
        return conn.items()

    @classmethod
    def collection(cls, conn, name):
        return conn.collection(name)


class RelationalDatabaseDriver(DatabaseDriver):
    """
    Generic driver for relational DB-API drivers, using Twisted's DB-API
    integration.
    """
    dbapi_module = None

    #: :type: sqlalchemy.engine.interfaces.Dialect
    dialect = None  # Set to dialect instance, or metaclass will do for you.

    # Set by metaclass based on dbapi_module if None.
    paramstyle = None

    @classmethod
    def init_driver(cls):
        if cls.paramstyle is None and cls.dbapi_module is not None:
            mod = __import__(cls.dbapi_module)
            cls.paramstyle = mod.paramstyle
        if cls.dialect is None and cls.uri_scheme is not None:
            cls.dialect = dialects.registry.load(cls.uri_scheme)()

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


class SQLiteDriver(RelationalDatabaseDriver):
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
        :type db: ExternalRelationalDatabase
        """
        self.db = db

    def all(self, limit=None):
        """
        Get the list of all entities.

        :param limit: Optional limit to how many to return.
        :type limit: int

        :rtype: twisted.internet.defer.Deferred
        """
        raise NotImplementedError()

    def get_by_id(self, id, callback=None):
        """
        Wrapper around _get that accepts a callback and returns a deferred.

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

    @inlineCallbacks
    def _factory(self, entities):
        """:rtype: twisted.internet.defer.Deferred"""
        factory = self._entity_factory
        if not callable(factory):
            raise NotImplementedError()
        # Funky syntax b/c we need to yield at least once. Passing non-deferred
        # just returns the object back.
        entities = yield [factory(entity) for entity in entities]
        returnValue(entities)

    @inlineCallbacks
    def before_save(self, entity):
        """
        :param entity: The entity to insert/update.

        :rtype: twisted.internet.defer.Deferred
        """
        yield
        returnValue(entity)

    @inlineCallbacks
    def after_save(self, entity):
        """
        :param entity: The entity to insert/update.

        :rtype: twisted.internet.defer.Deferred
        """
        yield
        returnValue(entity)

    def save(self, entity):
        """
        :param entity: The entity to insert/update.

        :rtype: twisted.internet.defer.Deferred
        """
        d = self.before_save(entity)
        d.addCallback(self._save)
        d.addCallback(self.after_save)
        return d

    def _save(self, entity):
        raise NotImplementedError()

    def delete(self, entity):
        """
        :param entity: The entity to delete.
        :rtype: twisted.internet.defer.Deferred
        """
        raise NotImplementedError()

    def find(self, specification, limit=None):
        """
        Find all entities that satisfy the specification.

        :param specification: The specification to satisfy.
        :type specification: mudsling.utils.specifications.Specification

        :param limit: Maximum result count.
        :type limit: int

        :rtype: twisted.internet.defer.Deferred
        """
        raise NotImplementedError()


class SchematicsSQLRepository(EntityRepository):
    """
    A generic repository for storing models built atop the schematics Model
    class in a relational database.
    """

    # The model handled by this repository.
    #: :type: schematics.Model
    model = None

    # The model fields to ignore when auto-generating the schema.
    ignore_fields = ()

    # The table that stores model instances.
    table = None

    # The field that acts as the id
    id_field = 'id'

    # If the DB generates an ID, then we know its new if None. Otherwise, we
    # need to take more steps to determine if a record is new or not.
    db_generates_ids = True

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

    @classmethod
    def build_model_schema(cls, table_name, model, ignore=()):
        schema = table(table_name)
        for field_name, field_type in model.fields.iteritems():
            if field_name in ignore:
                continue
            sqla_type = cls.map_data_type(field_type)
            if sqla_type is None:
                raise TypeError('Cannot find an SQLAlchemy type for %s.'
                                % field_type.__class__.__name__)
            sql_name = field_type.serialized_name or field_name
            schema.append_column(column(sql_name, sqla_type))
        return schema

    def column(self, field_name):
        return getattr(self.schema.c, field_name)

    col = column

    @property
    def id_column(self):
        return getattr(self.schema.c, self.id_field)

    @property
    def schema(self):
        if '_schema' not in self.__class__.__dict__:
            cls = self.__class__
            cls._schema = self.build_model_schema(table_name=self.table,
                                                  model=self.model,
                                                  ignore=self.ignore_fields)
        # noinspection PyUnresolvedReferences
        return self._schema

    def _select(self, *a, **kw):
        """:rtype: sqlalchemy.sql.selectable.Select"""
        return self.schema.select(*a, **kw)

    def _update(self, *a, **kw):
        """:rtype: sqlalchemy.sql.dml.Update"""
        return self.schema.update(*a, **kw)

    def _delete(self, *a, **kw):
        """:rtype: sqlalchemy.sql.dml.Delete"""
        return self.schema.delete(*a, **kw)

    def _insert(self, **kw):
        """
        Inserts a row in this repository's table.

        Will set the row's auto ID as the deferred's return value.

        :rtype: twisted.internet.defer.Deferred
        """
        return self.db.interaction(self._insert_interaction, **kw)

    def _insert_interaction(self, txn, **kw):
        query = self.schema.insert().values(**kw)
        sql, params = self.db.compile(query)
        txn.execute(sql, params)
        return txn.lastrowid

    def _query(self, query, *a, **kw):
        return self.db.query(query, *a, **kw)

    def _get(self, id):
        id = getattr(self.model, self.id_field).to_primitive(id)
        return self._query(self._select().where(self.id_column == id))

    @property
    def _entity_factory(self):
        return self.model

    @inlineCallbacks
    def _factory(self, entities):
        """:rtype: twisted.internet.defer.Deferred"""
        entities = map(dict, entities)
        entities = yield super(SchematicsSQLRepository, self)._factory(entities)
        returnValue(entities)

    @inlineCallbacks
    def _save(self, entity):
        """
        Saves the entity.

        On insert, the ID of the inserted row will be the deferred's return
        value when possible.

        :type entity: schematics.models.Model
        :rtype: twisted.internet.defer.Deferred
        """
        id = getattr(entity, self.id_field, None)
        if id is not None and not self.db_generates_ids:
            # Non-db ID is present -- we don't know if it's insert or update.
            # So we need to check for existing record.
            found = yield self._get(id)
            insert = (len(found) == 0)
        else:
            insert = id is None
        if insert:
            r = yield self._insert_entity(entity)
        else:
            r = yield self._update_entity(entity)
        returnValue(r)

    def _insert_entity(self, entity):
        fields = {k: v for k, v in entity.to_primitive().iteritems()
                  if k not in self.ignore_fields}
        return self._insert(**fields)

    def _update_entity(self, entity):
        id_col = self.id_column
        fields = {k: v for k, v in entity.to_primitive().iteritems()
                  if k not in self.ignore_fields}
        id = fields.get(self.id_field, None)
        stmt = self._update().values(**fields).where(id_col == id)
        return self.db.operation(stmt)

    def delete(self, entity):
        """
        :type entity: schematics.models.Model
        """
        id = getattr(entity, self.id_field, None)
        assert id is not None
        stmt = self._delete().where(self.id_column == id)
        return self.db.operation(stmt)

    @inlineCallbacks
    def all(self, limit=None):
        query = self._select()
        if limit is not None:
            query = query.limit(limit)
        results = yield self._query(query)
        objects = yield self._factory(map(dict, results))
        returnValue(objects)

    @inlineCallbacks
    def find(self, specification, limit=None):
        """
        Specification-driven entity retrieval.

        Converts a specification into an SQLAlchemy condition.

        :param specification: The specification to satisfy.
        :type specification: mudsling.utils.specifications.Specification

        :param limit: Maximum result count.
        :type limit: int

        :return: The list of entities that satisfy the specification.
        :rtype: twisted.internet.defer.Deferred
        """
        constraints = self._specification_to_condition(specification)
        query = self._select().where(constraints)
        if limit is not None:
            query = query.limit(limit)
        results = yield self._query(query)
        objects = yield self._factory(map(dict, results))
        returnValue(objects)

    @classmethod
    def _specification_to_condition(cls, specification):
        """
        Convert a specification to an SQLAlchemy condition.

        :param specification: The specification to convert.
        :type specification: mudsling.utils.specifications.Specification

        :return: The SQLAlchemy condition clause.
        """
        try:
            converter = dict_inherit(cls, 'specification_converters',
                                     specification.__class__)
        except KeyError:
            raise UnsupportedSpecificationInSQL("Cannot convert %r to SQL"
                                                % specification)
        return converter(specification)

    @classmethod
    def _not_spec_to_condition(cls, not_spec):
        return not_(cls._specification_to_condition(not_spec.spec))

    @classmethod
    def _or_spec_to_condition(cls, or_spec):
        return or_(cls._specification_to_condition(or_spec.left),
                   cls._specification_to_condition(or_spec.right))

    @classmethod
    def _and_spec_to_condition(cls, and_spec):
        return and_(cls._specification_to_condition(and_spec.left),
                    cls._specification_to_condition(and_spec.right))

    specification_converters = {
        specs.NotSpecification: _not_spec_to_condition,
        specs.OrSpecification: _or_spec_to_condition,
        specs.AndSpecification: _and_spec_to_condition
    }

    @inlineCallbacks
    def _one_or_none(self, where_clause):
        results = yield self._query(self._select().where(where_clause))
        if len(results):
            entities = yield self._factory(results)
            returnValue(entities[0])
        else:
            returnValue(None)

    @inlineCallbacks
    def find_by_field_value(self, field_name, value, op='='):
        """
        Find entities by the value of the given field.

        :param field_name: The field to query.
        :param value: The value to look for.
        :param op: The operator to use.

        :return: The query results (as deferred value).
        :rtype: twisted.internet.defer.Deferred
        """
        value = getattr(self.model, field_name).to_primitive(value)
        query = self._select().where(self.col(field_name).op(op)(value))
        results = yield self._query(query)
        entities = yield self._factory(results)
        returnValue(entities)

    @inlineCallbacks
    def field_is_unique(self, entity, field_name):
        """
        Check if the value the provided entity has for a specific field is
        unique among the set of entities managed by this repository.

        :param entity: An entity whose value to use.
        :param field_name: The name of the field whose value to use.

        :return: Whether the value is unique (as deferred return value).
        :rtype: twisted.internet.defer.Deferred
        """
        value = getattr(entity, field_name)
        found = yield self.find_by_field_value(field_name, value)
        returnValue(len(found) > 0)


class UnsupportedSpecificationInSQL(mudsling.errors.Error):
    pass


class ExternalDatabase(object):
    """
    Generic external datastore.
    """
    _uri = None
    _pool = None

    def __init__(self, uri):
        """
        Initialize the connection in child implementations.
        :return:
        """
        self._uri = urlparse(uri)
        self.connect()

    def connect(self):
        self._pool = self.db_driver.connect(self._uri)

    @property
    def db_driver(self):
        """:rtype: RelationalDatabaseDriver"""
        return DB_DRIVERS[self._uri.scheme]


class ExternalRelationalDatabase(ExternalDatabase):
    """
    Generic external database that handles its own connection, migrations, etc.

    :cvar migrations_path: Path to the migrations to execute against this kind
        of database.
    :type migrations_path: str
    """

    migrations_path = None

    _yoyo_uri_re = re.compile(r'^([^:]+):/(?!/)')

    def __init__(self, uri):
        """
        Initialize the connection in child implementations.
        :return:
        """
        self._uri = urlparse(uri)
        if self.migrations_path is not None:
            self.run_migrations(self.migrations_path)
        super(ExternalRelationalDatabase, self).__init__(uri)

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
        logging.debug(error.getErrorMessage())
        if sql is not None:
            logging.debug('SQL failed: %s', sql)
        if params is not None:
            logging.debug('Params: %r', params)
        return error  # We don't trap the error.

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
    _db_class = ExternalRelationalDatabase
    _db_uri = None
    _db = None
    _repositories = {}

    def _init_db(self):
        """
        Create the database connection pool.
        """
        if self._db is None:
            self._db = self._db_class(self._db_uri)
        for attr, cls in self._repositories.iteritems():
            if attr not in self.__dict__ or getattr(self, attr) is None:
                setattr(self, attr, cls(self._db))
