"""
Basic MUD @mail system.
"""
import re
from collections import OrderedDict

from twisted.internet.defer import inlineCallbacks, returnValue

from mudsling.utils.db import SQLiteDB
from mudsling.utils.time import parse_datetime, unixtime
from mudsling.objects import BaseObject, NamedObject
from mudsling.commands import Command, SwitchCommandHost
from mudsling.storage import ObjRef
import mudsling.locks as locks
import mudsling.errors as errors

import mudslingcore


class MailError(errors.Error):
    pass


class InvalidMessageSequence(MailError):
    pass


class InvalidMessageSet(MailError):
    pass


class InvalidMessageFilter(MailError):
    pass


class MailDB(SQLiteDB):
    """
    Wrapper around the mail SQLite database.
    """
    migrations_path = mudslingcore.migrations_path('mail')

    #: :type: mudsling.core.MUDSling
    game = None

    def __init__(self, filepath, game):
        """
        :type filepath: str
        :type game: mudsling.core.MUDSling
        """
        self.game = game
        super(MailDB, self).__init__(filepath)

        self.set_re = re.compile(
            r'(?P<explicit>(?:(?P<start>\d+)(?:(?:\.\.|-)(?P<end>\d+|\$))?))'
            r'|(?P<name>%s)' % ('|'.join(self.named_sets.keys())))
        self.filter_re = re.compile(r'^(?:<filter>%s)(?::(?P<param>.*))?$'
                                    % ('|'.join(self.sequence_filters.keys())))

    @inlineCallbacks
    def get_message(self, message_id):
        # results = yield self.query("SELECT * FROM messages")
        pass

    def _message_query(self, txn, conditions, joins=(), order=None, limit=None):
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

        :return: The messages.
        :rtype: dict of Message
        """
        rows = yield self._pool.runInteraction(
            self._message_query, conditions, joins=joins, order=order,
            limit=limit, mailbox_id=mailbox_id)
        messages = OrderedDict()
        for row in rows:
            if row['message_id'] in messages:
                # This is an additional row for extra recipient.
                messages[row['message_id']].add_recipient(
                    row['recipient_id'], row['recipient_name'])
            else:
                message = Message.from_row(row, mailbox_id=mailbox_id)
                message.add_recipient(row['recipient_id'],
                                      row['recipient_name'])
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

    def sequence_query_params(self, txn, recipient_id, set, filter):
        """
        Get the query parameters for messages in a recipient's mailbox that
        match a specific message set and optional filter.
        """
        query = {
            'joins': [("""INNER JOIN message_recipient mailbox
                          ON (mailbox.message_id = m.message_id)""",)],
            'conditions': [('AND mailbox.recipient_id = ?', recipient_id)],
            'order': 'm.timestamp ASC',
            'limit': 15
        }
        if set[0] == 'explicit':
            self._explicit_set(txn, recipient_id, query, *set[1:])
        elif set[0] == 'named':
            self.named_sets[set[1]](txn, recipient_id, query)
        if filter is not None:
            self.sequence_filters[filter[0]](txn, recipient_id, query)
        return query

    def _explicit_set(self, txn, recipient_id, query, start, end=None):
        start = int(start)
        if end is None:
            end = start
        elif end == '$':
            end = self.max_mailbox_index(txn, recipient_id) or 0
        else:
            end = int(end)
        query['conditions'].append(('mailbox.mailbox_index BETWEEN ? AND ?',
                                    start, end))

    def _named_set_first(self, txn, recipient_id, query):
        index = self.min_mailbox_index(txn, recipient_id)
        query['conditions'].append(('AND mailbox.mailbox_index = ?', index))

    def _named_set_last(self, txn, recipient_id, query):
        index = self.max_mailbox_index(txn, recipient_id)
        query['conditions'].append(('AND mailbox.mailbox_index = ?', index))

    def _named_set_unread(self, txn, recipient_id, query):
        query['conditions'].append(('AND mailbox.read = 0',))

    def _named_set_next(self, txn, recipient_id, query):
        query['limit'] = 1
        query['conditoins'].append(('AND mailbox.read = 0',))

    @property
    def named_sets(self):
        return {
            'first': self._named_set_first,
            'last': self._named_set_last,
            'unread': self._named_set_unread,
            'next': self._named_set_next
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

    def _filter_before(self, query, datestr):
        ut = self._parse_filter_date(datestr)
        query['conditions'].append(('AND m.timestamp < ?', ut))

    def _filter_after(self, query, datestr):
        ut = self._parse_filter_date(datestr)
        query['conditions'].append(('AND m.timestamp > ?', ut))

    def _filter_since(self, query, datestr):
        ut = self._parse_filter_date(datestr)
        query['conditions'].append(('AND m.timestamp >= ?', ut))

    def _filter_until(self, query, datestr):
        ut = self._parse_filter_date(datestr)
        query['conditions'].append(('AND m.timestamp <= ?', ut))

    def _parse_recipient(self, whostr):
        matches = self.game.db.match_descendants(whostr, MailRecipient)
        if len(matches) > 1:
            raise errors.AmbiguousMatch('Ambiguous recipient: %s' % whostr)
        elif not matches:
            raise errors.FailedMatch('No such recipient: %s' % whostr)
        return matches[0]

    def _filter_from(self, query, whostr):
        r = self._parse_recipient(whostr)
        query['conditions'].append(('AND m.from_id = ?', r.obj_id))

    def _filter_to(self, query, whostr):
        r = self._parse_recipient(whostr)
        query['conditions'].append(("""
            AND m.message_id IN (SELECT message_id
                                 FROM message_recipient mr_to
                                 WHERE mr_to.recipient_id = ?)
            """, r.obj_id))

    def _filter_fromstr(self, query, whostr):
        search = "%%%s%%" % whostr
        query['conditions'].append(('AND m.from_name LIKE ?', search))

    def _filter_tostr(self, query, whostr):
        search = "%%%s%%" % whostr
        query['conditions'].append(("""
            AND m.message_id IN (SELECT message_id
                                 FROM message_recipient mr_tostr
                                 WHERE mr_tostr.recipient_name LIKE ?)
            """, search))

    def _filter_subject(self, query, text):
        search = '%%%s%%' % text
        query['conditions'].append(('AND m.subject LIKE ?', search))

    def _filter_body(self, query, text):
        search = '%%%s%%' % text
        query['conditions'].append(('AND m.body LIKE ?', search))

    def _filter_first(self, query, num):
        query['limit'] = int(num)

    def _filter_last(self, query, num):
        query['limit'] = int(num)
        query['order'] = 'm.timestamp DESC'


# Initialized by MUDSlingCorePlugin.
mail_db = None


class Message(object):
    """
    Transient object representing a message.
    """

    def __init__(self, message_id=None, timestamp=None, mailbox_index=None,
                 read=None, recipients=None, from_id=None, from_name=None,
                 subject=None, body=None):
        self.message_id = message_id
        self.timestamp = timestamp
        self.mailbox_index = mailbox_index
        self.read = read
        self.from_id = from_id
        self.from_name = from_name
        self.subject = subject
        self.body = body
        self.recipients = OrderedDict if recipients is None else recipients

    @staticmethod
    def from_row(row, mailbox_id=None):
        """
        Create a Message instance from a database result row.

        :param row: Result row to import data from.
        :type row: sqlite3.Row

        :rtype: Message
        """
        fields = ('message_id', 'timestamp', 'from_id', 'from_name', 'subject',
                  'body')
        keys = row.keys()
        message = Message(**{k: row[k] for k in fields if k in keys})
        if (mailbox_id is not None and 'recipient_id' in keys
                and row['recipient_id'] == mailbox_id):
            for k in ('mailbox_index', 'read'):
                if k in keys:
                    setattr(message, k, row[k])
        return message

    def add_recipient(self, recipient_id, recipient_name=None):
        recipient = ObjRef(id=recipient_id)
        if recipient_name is None and recipient.is_valid(NamedObject):
            recipient_name = recipient.name
        self.recipients[recipient_id] = recipient_name


class MailBox(object):
    """
    Transient object representing an mailbox, backed by a MailDB instance.
    """

    def __init__(self, recipient_id, mail_db):
        """
        :param recipient_id: The recipient whose mailbox this is.
        :type recipient_id: int

        :param mail_db: The MailDB instance backing this class.
        :type mail_db: MailDB
        """
        self.recipient_id = recipient_id
        self.mail_db = mail_db

    @property
    def parsers(self):
        return {
            'sequence': self.parse_sequence
        }

    sequence_re = re.compile(r'^(?P<set>[^ ]*)(?: +(?P<filter>.*))?$')

    def parse_sequence(self, input):
        """
        A message sequence consists of a range of messages, followed by an
        optional set of filters.
        """
        m = self.sequence_re.match(input)
        if m:
            groups = m.groupdict()
            set = self.parse_set(groups['set'])
            filter = groups['filter'] if groups['filter'] is not None else None
            filter = self.parse_filter(filter)
            return {'set': set, 'filter': filter}
        else:
            raise InvalidMessageSequence(
                "Invalid message sequence: %s" % input)

    def parse_set(self, input, default='all'):
        """
        A message set specifies a group of messages, either by explicit index
        numbers, or via a special named set.
        """
        if default is not None and not input.strip():
            input = default
        m = self.mail_db.set_re.match(input)
        if m:
            groups = m.groupdict()
            if groups['explicit'] is not None:
                return 'explicit', (groups['start'], groups['end'])
            else:
                return 'named', groups['name']
        else:
            raise InvalidMessageSet("Invalid message range: %s" % input)

    def parse_filter(self, filterstr):
        m = self.mail_db.filter_re.match(filterstr)
        if m:
            g = m.groupdict()
            return g['filter'], g['param']
        else:
            raise InvalidMessageFilter('Invalid message filter: %s' % filterstr)

    def get_message(self, index):
        pass


use_mail = locks.Lock('has_perm(use mail)')


class MailSubCommand(Command):
    """
    Generic mail subcommand.
    """
    abstract = True
    lock = use_mail

    #: :type: MailRecipient
    obj = None

    @property
    def mailbox(self):
        return self.obj.mailbox

    def _insert_mailbox_parsers(self):
        parsers = self.mailbox.parsers


class MailListCmd(MailSubCommand):
    """
    @mail[/list] [<range>]

    List the specified range of messages, or the most recent 15 messages.
    """
    aliases = ('list',)
    syntax = '[<range>]'


    # def run(self, ):


class MailCommand(SwitchCommandHost):
    """
    @mail[/<subcommand>] [<subcommand parameters>]

    Issue a mail command.
    """
    aliases = ('@mail',)
    lock = use_mail
    default_switch = 'list'
    subcommands = ()


class MailRecipient(BaseObject):
    """
    An object which can receive mail, and has commands for managing a mailbox.
    """
    _transient_vars = ('_mailbox',)
    _mailbox = None

    @property
    def mailbox(self):
        """:rtype: MailBox"""
        if self._mailbox is None:
            self._mailbox = MailBox(self.obj_id, mail_db)
        return self._mailbox
