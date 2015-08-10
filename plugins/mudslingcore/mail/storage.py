import re
from collections import OrderedDict

from twisted.internet.defer import inlineCallbacks, returnValue

from mudsling.storage import ObjRef
from mudsling.utils.db import ExternalDatabase
from mudsling.utils.time import parse_datetime, unixtime
from mudsling.utils.string import split_quoted_words
from mudsling.objects import NamedObject

import mudslingcore
from mudslingcore.mail.errors import *


# noinspection PyUnusedLocal
class MailDB(ExternalDatabase):
    """
    Wrapper around the mail SQLite database.
    """
    migrations_path = mudslingcore.migrations_path('mail')

    #: :type: mudsling.core.MUDSling
    game = None

    def __init__(self, uri, game):
        """
        :type uri: str
        :type game: mudsling.core.MUDSling
        """
        self.game = game
        super(MailDB, self).__init__(uri)

        self.set_re = re.compile(
            r'(?P<explicit>(?:(?P<start>\d+)(?:(?:\.\.|-)(?P<end>\d+|\$))?))'
            r'|(?P<name>%s)' % ('|'.join(self.named_sets.keys())))
        self.filter_re = re.compile(r'(?P<filter>%s)(?::(?P<param>.*))?'
                                    % ('|'.join(self.sequence_filters.keys())))

    @inlineCallbacks
    def get_message(self, message_id):
        conditions = (('m.message_id = ?', message_id),)
        results = yield self.message_query(conditions)
        if len(results):
            returnValue(results[message_id])
        else:
            returnValue(None)

    def load_message_body(self, message_id):
        """:rtype: twisted.internet.defer.Deferred"""
        return self._pool.runInteraction(self._load_message_body, message_id)

    def _load_message_body(self, txn, message_id):
        query = "SELECT m.body FROM messages m WHERE m.message_id = ?"
        txn.execute(query, (message_id,))
        row = txn.fetchone()
        return row['body']

    def mark_message_read(self, message_id, recipient_id, read=True):
        """:rtype: twisted.internet.defer.Deferred"""
        val = 1 if read else 0
        sql = '''UPDATE message_recipient SET read = ?
                 WHERE message_id = ? AND recipient_id = ?'''
        return self._pool.runQuery(sql, (val, message_id, recipient_id))

    def _message_query(self, txn, conditions, joins=(), order=None,
                       limit=None):
        """
        Execute a query for messages using the provided conditions.

        :param conditions: Iterable whose members are iterables containing the
            string SQL condition, followed by any required qmark-style
            parameters.
        :type conditions: tuple or list

        :param joins: Any additional join clauses to include. Each clause tuple
            should include the query string and any parameters.
        :type joins: tuple of tuple

        :param order: The field and direction to order by.
        :type order: str

        :param limit: The maximum number of results (or an expression).
        :type limit: int or str

        :return: The cursor to the result set.
        :rtype: sqlite3.Cursor
        """
        query = """
             SELECT m.message_id,
                    m.timestamp,
                    m.from_id,
                    m.from_name,
                    m.subject,
                    mr.recipient_id,
                    mr.recipient_name,
                    mr.mailbox_index,
                    mr.read
               FROM messages m
         INNER JOIN message_recipient mr ON (mr.message_id = m.message_id)
        """
        params = []
        for join in joins:
            query += '\n ' + join[0]
            params.extend(join[1:])
        for cond in conditions:
            query += '\n                   %s' % cond[0]
            params.extend(cond[1:])
        if order is not None:
            query += ' ORDER BY %s' % order
        if limit is not None:
            if isinstance(limit, int):
                query += ' LIMIT %d' % limit
            elif isinstance(limit, str):
                query += ' LIMIT %s' % limit
        txn.execute(query, params)
        return txn.fetchall()

    @inlineCallbacks
    def message_query(self, conditions, joins=(), order=None, limit=None,
                      mailbox_id=None):
        """
        Execute a query for messages using the provided conditions.

        :param conditions: Iterable whose members are iterables containing the
            string SQL condition, followed by any required qmark-style
            parameters.
        :type conditions: tuple or list

        :param joins: Any additional join clauses to include. Each clause tuple
            should include the query string and any parameters.
        :type joins: tuple of tuple

        :param order: The field and direction to order by.
        :type order: str

        :param limit: The maximum number of results (or an expression).
        :type limit: int or str

        :param mailbox_id: The recipient whose index numbers and read states to
            load into the message objects.
        :type mailbox_id: int

        :rtype: twisted.internet.defer.Deferred
        """
        rows = yield self._pool.runInteraction(
            self._message_query, conditions, joins=joins, order=order,
            limit=limit)
        messages = OrderedDict()
        for row in rows:
            if row['message_id'] in messages:
                # This is an additional row for extra recipient.
                messages[row['message_id']].add_recipient(
                    row['recipient_id'], row['recipient_name'],
                    row['mailbox_index'])
            else:
                message = Message.from_row(row, self, mailbox_id=mailbox_id)
                message.add_recipient(row['recipient_id'],
                                      row['recipient_name'],
                                      row['mailbox_index'])
                messages[message.message_id] = message
        returnValue(messages)

    def max_mailbox_index(self, txn, recipient_id):
        r = txn.execute("""
                SELECT MAX(mailbox_index) max_index
                FROM message_recipient
                WHERE recipient_id = ?
            """, (recipient_id,))
        return r.fetchone()[0]

    def min_mailbox_index(self, txn, recipient_id):
        r = txn.execute("""
                SELECT MIN(mailbox_index) min_index
                FROM message_recipient
                WHERE recipient_id = ?
            """, (recipient_id,))
        return r.fetchone()[0]

    def parse_set(self, input, default='all'):
        """
        A message set specifies a group of messages, either by explicit index
        numbers, or via a special named set.
        """
        if default is not None and (input is None or not input.strip()):
            input = default
        m = self.set_re.match(input)
        if m:
            groups = m.groupdict()
            if groups['explicit'] is not None:
                return 'explicit', groups['start'], groups['end']
            else:
                return 'named', groups['name']
        else:
            raise InvalidMessageSet("Invalid message set: %s" % input)

    def parse_filter(self, filterstr):
        filters = []
        for filter_str in split_quoted_words(filterstr):
            m = self.filter_re.match(filter_str)
            if m:
                g = m.groupdict()
                filters.append((g['filter'], g['param']))
            else:
                raise InvalidMessageFilter('Invalid message filter: %s'
                                           % filter_str)
        return filters

    def sequence_query_params(self, recipient_id, set, filters):
        query = {
            'joins': [("""INNER JOIN message_recipient mailbox
                          ON (mailbox.message_id = m.message_id)""",)],
            'conditions': [('AND mailbox.recipient_id = ?', recipient_id)],
            'order': 'm.timestamp ASC',
            'limit': 15,
            'mailbox_id': recipient_id
        }
        if set[0] == 'explicit':
            self._explicit_set(query, *set[1:])
        elif set[0] == 'named':
            self.named_sets[set[1]](recipient_id, query)
        for filter in (filters if filters is not None else ()):
            self.sequence_filters[filter[0]](recipient_id, query, *filter[1:])
        return query

    def _explicit_set(self, query, start, end=None):
        start = int(start)
        if end is None:
            end = start
        elif end == '$':
            end = 9223372036854775807
        else:
            end = int(end)
        query['conditions'].append(
            ('AND mailbox.mailbox_index BETWEEN ? AND ?', start, end))

    def _named_set_first(self, recipient_id, query):
        query['conditions'].append(("""
            AND mailbox.mailbox_index = (
                SELECT MIN(mailbox_index)
                FROM message_recipient
                WHERE recipient_id = ?)
        """, recipient_id))

    def _named_set_last(self, recipient_id, query):
        query['conditions'].append(("""
            AND mailbox.mailbox_index = (
                SELECT MAX(mailbox_index)
                FROM message_recipient
                WHERE recipient_id = ?)
        """, recipient_id))

    def _named_set_unread(self, recipient_id, query):
        query['conditions'].append(('AND mailbox.read = 0',))

    def _named_set_next(self, recipient_id, query):
        query['limit'] = 1
        query['conditions'].append(('AND mailbox.read = 0',))

    def _named_set_all(self, recipient_id, query):
        pass

    @property
    def named_sets(self):
        return {
            'first': self._named_set_first,
            'last': self._named_set_last,
            'unread': self._named_set_unread,
            'next': self._named_set_next,
            'all': self._named_set_all
        }

    @property
    def sequence_filters(self):
        return {
            'before': self._filter_before,
            'after': self._filter_after,
            'since': self._filter_since,
            'until': self._filter_until,
            'from': self._filter_from,
            'to': self._filter_to,
            '%from': self._filter_fromstr,
            '%to': self._filter_tostr,
            'subject': self._filter_subject,
            'body': self._filter_body,
            'first': self._filter_first,
            'last': self._filter_last
        }

    def _parse_filter_date(self, input):
        return unixtime(parse_datetime(input))

    def _filter_before(self, recipient_id, query, datestr):
        ut = self._parse_filter_date(datestr)
        query['conditions'].append(('AND m.timestamp < ?', ut))

    def _filter_after(self, recipient_id, query, datestr):
        ut = self._parse_filter_date(datestr)
        query['conditions'].append(('AND m.timestamp > ?', ut))

    def _filter_since(self, recipient_id, query, datestr):
        ut = self._parse_filter_date(datestr)
        query['conditions'].append(('AND m.timestamp >= ?', ut))

    def _filter_until(self, recipient_id, query, datestr):
        ut = self._parse_filter_date(datestr)
        query['conditions'].append(('AND m.timestamp <= ?', ut))

    def _parse_recipient(self, recipient_id, whostr):
        if whostr == 'me':
            matches = (ObjRef(recipient_id),)
        else:
            from mudslingcore.mail.recipient import MailRecipient
            matches = self.game.db.match_descendants(whostr, MailRecipient)
        if len(matches) > 1:
            raise errors.AmbiguousMatch('Ambiguous recipient: %s' % whostr)
        elif not matches:
            raise errors.FailedMatch('No such recipient: %s' % whostr)
        return matches[0]

    def _filter_from(self, recipient_id, query, whostr):
        r = self._parse_recipient(recipient_id, whostr)
        query['conditions'].append(('AND m.from_id = ?', r.obj_id))

    def _filter_to(self, recipient_id, query, whostr):
        r = self._parse_recipient(recipient_id, whostr)
        query['conditions'].append(("""
            AND m.message_id IN (SELECT message_id
                                 FROM message_recipient mr_to
                                 WHERE mr_to.recipient_id = ?)
            """, r.obj_id))

    def _filter_fromstr(self, recipient_id, query, whostr):
        search = "%%%s%%" % whostr
        query['conditions'].append(('AND m.from_name LIKE ?', search))

    def _filter_tostr(self, recipient_id, query, whostr):
        search = "%%%s%%" % whostr
        query['conditions'].append(("""
            AND m.message_id IN (SELECT message_id
                                 FROM message_recipient mr_tostr
                                 WHERE mr_tostr.recipient_name LIKE ?)
            """, search))

    def _filter_subject(self, recipient_id, query, text):
        search = '%%%s%%' % text
        query['conditions'].append(('AND m.subject LIKE ?', search))

    def _filter_body(self, recipient_id, query, text):
        search = '%%%s%%' % text
        query['conditions'].append(('AND m.body LIKE ?', search))

    def _filter_first(self, recipient_id, query, num):
        query['limit'] = int(num)

    def _filter_last(self, recipient_id, query, num):
        query['limit'] = int(num)
        query['order'] = 'm.timestamp DESC'

    @inlineCallbacks
    def load_recipients(self, message_id):
        rows = yield self._pool.runQuery("""SELECT recipient_id AS id,
                                                   recipient_name AS name,
                                                   mailbox_index AS idx
                                              FROM message_recipient
                                             WHERE message_id = ?""",
                                         (message_id,))
        rcp = {r['id']: {'id': r['id'], 'name': r['name'], 'index': r['idx']}
               for r in rows}
        returnValue(rcp)

    @inlineCallbacks
    def save_message(self, message):
        """
        Save a message to the database.

        :param message: The message to save.
        :type message: Message

        :rtype: twisted.internet.defer.Deferred
        """
        def _insert_message(txn, message):
            sql = """
                INSERT INTO messages (
                    timestamp, from_id, from_name, subject, body)
                VALUES (:timestamp, :from_id, :from_name, :subject, :body)
            """
            txn.execute(sql, {
                'timestamp': message.timestamp,
                'from_id': message.from_id,
                'from_name': message.from_name,
                'subject': message.subject,
                'body': message.body
            })
            return txn.lastrowid

        def _insert_recipients(txn, message):
            index_sql = """
                SELECT IFNULL(MAX(mailbox_index), 0) + 1
                FROM message_recipient mr
                WHERE mr.recipient_id = :recipient_id"""
            sql = """
                INSERT INTO message_recipient (
                    message_id, recipient_id, recipient_name, mailbox_index
                ) VALUES (
                    :message_id, :recipient_id, :recipient_name, (%s)
                )
            """ % index_sql
            params = ({'message_id': message.message_id,
                       'recipient_id': k,
                       'recipient_name': v}
                      for k, v in message.recipients.iteritems())
            txn.executemany(sql, params)

        message.message_id = yield self._pool.runInteraction(_insert_message,
                                                             message)
        yield self._pool.runInteraction(_insert_recipients, message)
        yield message.load_recipients()
        returnValue(message)


class MailBox(object):
    """
    Transient object representing an mailbox, backed by a MailDB instance.
    """
    _named_group_re = re.compile('\(\?P<.*?>')

    @classmethod
    def _unname_groups(cls, pattern):
        return cls._named_group_re.sub('(?:', pattern)

    def __init__(self, recipient_id, mail_db):
        """
        :param recipient_id: The recipient whose mailbox this is.
        :type recipient_id: int

        :param mail_db: The MailDB instance backing this class.
        :type mail_db: MailDB
        """
        self.recipient_id = recipient_id
        self.mail_db = mail_db
        # Use the mail_db's parsers to generate a sequence parser.
        seq_pat = '^(?P<set>{set_pat})? *(?P<filters>.*)?$'.format(
            set_pat=self._unname_groups(mail_db.set_re.pattern),
        )
        self.sequence_re = re.compile(seq_pat)

    @property
    def parsers(self):
        return {
            'sequence': self.parse_sequence
        }

    def parse_sequence(self, input):
        """
        A message sequence consists of a range of messages, followed by an
        optional set of filters.
        """
        m = self.sequence_re.match(input)
        if m:
            groups = m.groupdict()
            set = self.mail_db.parse_set(groups['set'])
            filters = (self.mail_db.parse_filter(groups['filters'])
                       if groups['filters'] is not None else None)
            return {'set': set, 'filters': filters}
        else:
            raise InvalidMessageSequence(
                "Invalid message sequence: %s" % input)

    @inlineCallbacks
    def get_messages_from_sequence(self, seq):
        """:rtype: twisted.internet.defer.Deferred"""
        if isinstance(seq, str):
            sequence = self.parse_sequence(seq)
        elif seq is None:
            sequence = self.parse_sequence('')
        else:
            sequence = seq
        query_params = self.mail_db.sequence_query_params(self.recipient_id,
                                                          **sequence)
        messages = yield self.mail_db.message_query(**query_params)
        returnValue(messages)

    @inlineCallbacks
    def get_message(self, index):
        """:rtype: twisted.internet.defer.Deferred"""
        conditions = (('''AND m.message_id IN (SELECT message_id
                                               FROM message_recipient mr2
                                               WHERE mr2.recipient_id = ? AND
                                                     mr2.mailbox_index = ?)''',
                       self.recipient_id, index),)
        results = yield self.mail_db.message_query(
            conditions, mailbox_id=self.recipient_id)
        if len(results):
            returnValue(results.itervalues().next())
        else:
            raise InvalidMessageIndex('Invalid message number: %s' % index)

    @inlineCallbacks
    def get_next_unread_message(self):
        """:rtype: twisted.internet.defer.Deferred"""
        conditions = (('''AND m.message_id IN (SELECT message_id
                                               FROM message_recipient mr2
                                               WHERE mr2.recipient_id = ? AND
                                                     mr2.read = 0
                                               LIMIT 1)''',
                       self.recipient_id),)
        results = yield self.mail_db.message_query(
            conditions, mailbox_id=self.recipient_id)
        if len(results):
            returnValue(results.itervalues().next())
        else:
            returnValue(None)

    def send_message(self, from_name, recipients, subject, body):
        """
        Create a Message object from the mailbox owner and save it.

        :param from_name: The name to use for the sender.
        :type from_name: str

        :param recipients: Who is to receive the message. Keys are recipient id
            numbers and values are strings identifying them (or None to allow
            Message object to obtain name itself).
        :type recipients: dict of (int, str)

        :param subject: The subject of the message.
        :type subject: str

        :param body: The body of the message.
        :type body: str

        :rtype: twisted.internet.defer.Deferred
        """
        message = Message(
            self.mail_db,
            timestamp=unixtime(),
            from_id=self.recipient_id,
            from_name=from_name,
            subject=subject,
            body=body
        )
        for recipient_id, recipient_name in recipients.iteritems():
            message.add_recipient(recipient_id, recipient_name)
        d = self.mail_db.save_message(message)
        d.addCallback(self._notify_recipients)
        return d

    def _notify_recipients(self, message):
        from mudslingcore.mail.recipient import MailRecipient
        for rid, rname in message.recipients.iteritems():
            recipient = ObjRef(rid)
            if recipient.is_valid(MailRecipient):
                recipient.notify_new_mail(message)
        return message


class Message(object):
    """
    Transient object representing a message.
    """

    def __init__(self, mail_db, message_id=None, timestamp=None,
                 mailbox_index=None, read=None, from_id=None, from_name=None,
                 subject=None, body=None):
        #: :type: MailDB
        self.mail_db = mail_db
        self.message_id = message_id
        self.timestamp = timestamp
        self.mailbox_index = mailbox_index
        self.read = read
        self.from_id = from_id
        self.from_name = from_name
        self.subject = subject
        self.body = body
        self.recipients = OrderedDict()
        self.recipient_indexes = {}

    @property
    def recipient_objects(self):
        return tuple(ObjRef(rid) for rid in self.recipients.iterkeys())

    @staticmethod
    def from_row(row, mail_db, mailbox_id=None):
        """
        Create a Message instance from a database result row.

        :param row: Result row to import data from.
        :type row: sqlite3.Row

        :rtype: Message
        """
        fields = ('message_id', 'timestamp', 'from_id', 'from_name', 'subject',
                  'body')
        keys = row.keys()
        message = Message(mail_db, **{k: row[k] for k in fields if k in keys})
        if (mailbox_id is not None and 'recipient_id' in keys
                and row['recipient_id'] == mailbox_id):
            for k in ('mailbox_index', 'read'):
                if k in keys:
                    setattr(message, k, row[k])
        return message

    def add_recipient(self, recipient_id, recipient_name=None,
                      mailbox_index=None):
        recipient = ObjRef(id=recipient_id)
        if recipient_name is None and recipient.is_valid(NamedObject):
            recipient_name = recipient.name
        self.recipients[recipient_id] = recipient_name
        if mailbox_index is not None:
            self.recipient_indexes[recipient_id] = mailbox_index

    @inlineCallbacks
    def load_body(self):
        """:rtype: twisted.internet.defer.Deferred"""
        body = yield self.mail_db.load_message_body(self.message_id)
        self.body = str(body)
        returnValue(self)

    @inlineCallbacks
    def load_recipients(self):
        """:rtype: twisted.internet.defer.Deferred"""
        recipients = yield self.mail_db.load_recipients(self.message_id)
        for rid, recipient in recipients.iteritems():
            self.add_recipient(rid, recipient['name'], recipient['index'])
        returnValue(self)

    def mark_read(self, recipient_id, read=True):
        """:rtype: twisted.internet.defer.Deferred"""
        return self.mail_db.mark_message_read(self.message_id, recipient_id,
                                              read=read)
