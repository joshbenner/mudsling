import logging

from twisted.internet.defer import inlineCallbacks, returnValue

from mudsling.storage import ObjRef
from mudsling.commands import Command, SwitchCommandHost
from mudsling.objects import BaseObject
from mudsling import locks
from mudsling import errors
from mudsling import parsers
from mudsling.utils.time import format_timestamp
from mudsling.utils.string import plural_noun, linewrap, strip_ansi, and_list

from mudslingcore.ui import UsesUI
from mudslingcore.editor import EditorError
from mudslingcore.mail.storage import MailBox
from mudslingcore.mail.errors import *


use_mail = locks.Lock('has_perm(use mail)')


class RecipientsParser(parsers.Parser):
    def parse(self, input, actor=None):
        matcher = parsers.MatchDescendants(cls=MailRecipient,
                                           err=True,
                                           search_for='recipient',
                                           show=True,
                                           context=False)
        strings = parsers.StringListStaticParser.parse(input)
        return [matcher.parse(s, actor=actor) for s in strings]


match_recipients = RecipientsParser()


class MailSubCommand(Command):
    """
    Generic mail subcommand.
    """
    abstract = True
    lock = use_mail

    #: :type: MailRecipient
    obj = None

    #: :type: MailRecipient
    actor = None

    @property
    def mailbox(self):
        """:rtype: MailBox"""
        return self.obj.mailbox

    def match_syntax(self, argstr):
        parsers = self.mailbox.parsers
        for argname, parser in self.arg_parsers.iteritems():
            if parser in parsers:
                self.arg_parsers[argname] = parsers[parser]
        return super(MailSubCommand, self).match_syntax(argstr)

    def execute(self):
        try:
            return super(MailSubCommand, self).execute()
        except MailError as e:
            raise self._err('{r' + e.message)

    def _start_session(self, actor, recipients, subject, body=''):
        from mudslingcore.mail.editor import MailEditorSession
        session = MailEditorSession(actor, recipients=recipients,
                                    subject=subject, body=body)
        try:
            actor.player.register_editor_session(session, activate=True)
        except EditorError as e:
            raise self._err(e.message)
        actor.tell('{gYou are now composing ', session.description, '.')
        return session

    def list_messages(self, messages, title=None, footer=''):
        ui = self.actor.get_ui()
        name = lambda m, na, ia: self._whostr(getattr(m, na), getattr(m, ia))
        mid = lambda m: str(m.mailbox_index) + (' ' if m.read else '{y*{n')
        c = ui.Column
        t = ui.Table([
            c('ID', align='r', cell_formatter=mid),
            c('Date', align='l', data_key='timestamp',
              cell_formatter=format_timestamp, formatter_args=('short',)),
            c('From', align='l', cell_formatter=name,
              formatter_args=('from_name', 'from_id')),
            c('Subject', align='l', data_key='subject')
        ])
        if messages:
            t.add_rows(*sorted(messages.itervalues(),
                               key=lambda m: m.mailbox_index))
        else:
            t.add_row('(no messages found matching query)')
        if title is None:
            title = '@mail: %d messages' % len(messages)
        self.actor.msg(ui.report(title, t, footer))

    def _show_error(self, err):
        err.trap(Exception)
        if err.check(errors.MatchError, MailError, ValueError):
            self.actor.tell('{r', err.getErrorMessage().strip("'"))
        else:
            self.actor.tell('{rInternal Error.')
            logging.error(err.getTraceback())

    def _whostr(self, text, id):
        """:rtype: str"""
        return self.actor.format_recipient(text, id)

    @inlineCallbacks
    def _load_body(self, message):
        yield message.load_body()
        returnValue(message)

    def _message_header(self, message):
        ui = self.actor.get_ui()
        tostr = '; '.join(self._whostr(rname, rid)
                          for rid, rname in message.recipients.iteritems())
        #: :type: list of (str, str)
        headers = [
            ('Date', format_timestamp(message.timestamp, 'long')),
            ('From', self._whostr(message.from_name, message.from_id)),
            ('To', tostr),
            ('Subject', message.subject)
        ]
        t = ui.keyval_table(headers)
        return str(t)

    def _show_message(self, message):
        """
        :type message: mudslingcore.mail.Message
        """
        ui = self.actor.get_ui()
        header = self._message_header(message)
        body = '%s\n\n%s' % (header, message.body)
        title = 'Message %d' % message.mailbox_index
        self.actor.msg(ui.report(title, body))
        return message

    def _mark_read(self, message):
        message.mark_read(self.obj.obj_id)

    def read_message_callbacks(self, deferred):
        deferred.addCallback(self._load_body)
        deferred.addCallback(self._show_message)
        deferred.addCallback(self._mark_read)

    def _quote_body(self, message):
        wrapopts = {'initial_indent': '> ', 'subsequent_indent': '> '}
        quote = linewrap(strip_ansi(self._message_header(message)), **wrapopts)
        quote += '\n> \n'
        quote += linewrap(str(message.body), **wrapopts) + '\n\n'
        return quote


class MailListCmd(MailSubCommand):
    """
    @mail[/list] [<sequence>]

    List the specified range of messages, or the most recent 15 messages.
    """
    aliases = ('list',)
    syntax = '[<seq>]'
    arg_parsers = {'seq': 'sequence'}

    def run(self, this, actor, seq):
        """
        :type this: MailRecipient
        :type actor: MailRecipient
        :type seq: dict
        """
        if not seq:
            seq = '1-$ last:15'
        try:
            d = self.mailbox.get_messages_from_sequence(seq)
        except MailError as e:
            raise self._err(e.message)
        d.addCallback(self._show_messages,
                      self.args['seq'] if seq is not None else None)
        d.addErrback(self._show_error)

    def _show_messages(self, messages, seqstr):
        n = len(messages)
        title = '@mail: %d %s' % (n, plural_noun('message', n))
        if seqstr is not None:
            title += ' (%s)' % seqstr
        self.list_messages(messages, title=title)


class MailNewCmd(MailSubCommand):
    """
    @mail/new

    List all new messages.
    """
    aliases = ('new',)

    def run(self, this, actor):
        d = self.mailbox.get_messages_from_sequence('unread')
        d.addCallback(self.list_messages, title='New Messages')


class MailSendCmd(MailSubCommand):
    """
    @mail/send <recipients>[=<subject>]

    Open mail editor.
    """
    aliases = ('send',)
    syntax = '<recipients>[{=}<subject>]'
    arg_parsers = {'recipients': match_recipients}

    def run(self, this, actor, recipients, subject):
        self._start_session(actor, recipients, subject)


class MailReplyCmd(MailSubCommand):
    """
    @mail/reply <message-num>

    Reply to a specific message.
    """
    aliases = ('reply',)
    syntax = '<num>'
    arg_parsers = {'num': int}

    def run(self, this, actor, num):
        """
        :type this: MailRecipient
        :type actor: MailRecipient
        :type num: int
        """
        d = this.get_mail_message(num)
        d.addCallback(self._load_body)
        d.addCallback(self._reply_to_message)
        d.addErrback(self._show_error)

    def _reply_subject(self, message):
        if message.subject.startswith('RE: '):
            subject = message.subject
        else:
            subject = 'RE: ' + message.subject
        return subject

    def _reply_recipients(self, message):
        recipients = [r for r in message.recipient_objects if r != self.actor]
        from_obj = ObjRef(message.from_id)
        if from_obj.is_valid(MailRecipient):
            if from_obj not in recipients:
                recipients.append(from_obj)
        elif from_obj in recipients:
            recipients.remove(from_obj)
        return recipients

    def _reply_to_message(self, message):
        recipients = self._reply_recipients(message)
        subject = self._reply_subject(message)
        quote = self._quote_body(message)
        self._start_session(self.actor, recipients, subject, quote)


class MailQuickReplyCmd(MailReplyCmd):
    """
    @mail/quickreply <message-num>=<text>

    A quick way to reply to a message.
    """
    aliases = ('quickreply', 'qreply', 'qr')
    syntax = "<num>{=}<text>"
    arg_parsers = {'num': int}

    def _reply_to_message(self, message):
        recipients = self._reply_recipients(message)
        subject = self._reply_subject(message)
        quote = self._quote_body(message)
        body = quote + self.parsed_args['text']
        d = self.obj.send_mail(recipients, subject, body)
        d.addErrback(self._show_error)


class MailForwardCmd(MailSubCommand):
    """
    @mail/forward <message-num> to <recipients>

    Opens the mail editor with the quoted message to the recipients.
    """
    aliases = ('forward', 'fwd')
    syntax = '<num> to <recipients>'
    arg_parsers = {
        'num': int,
        'recipients': match_recipients
    }

    def run(self, this, actor, num, recipients):
        """
        :type this: MailRecipient
        :type actor: MailRecipient
        :type num: int
        :type recipients: list of MailRecipient
        """
        d = this.get_mail_message(num)
        d.addCallback(self._load_body)
        d.addCallback(self._forward_message, recipients)
        d.addErrback(self._show_error)

    def _forward_subject(self, message):
        original = str(message.subject)
        if original.startswith('FWD: '):
            subject = original
        else:
            subject = 'FWD: %s' % original
        return subject

    def _forward_message(self, message, recipients):
        subject = self._forward_subject(message)
        body = self._quote_body(message)
        self._start_session(self.actor, recipients, subject, body)


class MailQuickForwardCmd(MailForwardCmd):
    """
    @mail/quickforward <message-num> to <recipients>

    Quickly forward a message without editing it first.
    """
    aliases = ('quickforward', 'qfwd', 'qf')

    def _forward_message(self, message, recipients):
        subject = self._forward_subject(message)
        body = self._quote_body(message)
        self.obj.send_mail(recipients, subject, body)


class MailReadCmd(MailSubCommand):
    """
    @mail/read <message-num>

    Read the specified message.
    """
    aliases = ('read',)
    syntax = '<num>'
    arg_parsers = {'num': int}

    def run(self, this, actor, num):
        """
        :type this: MailRecipient
        :type actor: MailRecipient
        :type num: int
        """
        d = this.get_mail_message(num)
        self.read_message_callbacks(d)
        d.addErrback(self._show_error)


class MailNextCmd(MailSubCommand):
    """
    @mail/next

    Read the oldest unread message.
    """
    aliases = ('next',)

    def run(self, **kw):
        d = self.mailbox.get_next_unread_message()
        d.addCallback(self._validate_next)
        self.read_message_callbacks(d)
        d.addErrback(self._show_error)

    def _validate_next(self, message):
        if message is None:
            raise MailError("There are no new messages.")
        return message


class MailQuickCmd(MailSubCommand):
    """
    @mail/quick <recipients>[/<subject>]=<text>

    Compose a quick message without using the editor.
    """
    aliases = ('quick',)
    syntax = '<recipients>[{/}<subject>]{=}<text>'
    arg_parsers = {'recipients': match_recipients}

    def run(self, this, actor, recipients, text, subject):
        """
        :type this: MailRecipient
        :type actor: MailRecipient
        :type recipients: list of MailRecipient
        :type text: str
        :type subject: str
        """
        if subject is None:
            subject = 'Quick message'
        d = this.send_mail(recipients, subject, text)
        d.addErrback(self._show_error)


class MailCommand(SwitchCommandHost):
    """
    @mail[/<subcommand>] [<subcommand parameters>]

    Issue a mail command.
    """
    aliases = ('@mail',)
    lock = use_mail
    default_switch = 'list'
    subcommands = (MailListCmd, MailNewCmd, MailSendCmd, MailReadCmd,
                   MailNextCmd, MailQuickCmd, MailReplyCmd, MailQuickReplyCmd,
                   MailForwardCmd, MailQuickForwardCmd)


class MailRecipient(BaseObject, UsesUI):
    """
    An object which can receive mail, and has commands for managing a mailbox.
    Basically a thin interface layer on top of MailBox.
    """
    _transient_vars = ('_mailbox',)
    _mailbox = None

    private_commands = (MailCommand,)

    @property
    def mailbox(self):
        """:rtype: MailBox"""
        if self._mailbox is None:
            from mudslingcore.mail import mail_db
            self._mailbox = MailBox(self.obj_id, mail_db)
        return self._mailbox

    def format_recipient(self, name, id):
        """:rtype: str"""
        out = name
        if self.has_perm('see object numbers'):
            out += ' (#%d)' % id
        return str(out)

    def send_mail(self, recipients, subject, body):
        """
        Send a message from this recipient.

        :param recipients: The recipients who will receive the message.
        :type recipients: list of MailRecipient

        :param subject: The subject of the message.
        :type subject: str

        :param body: The body of the message.
        :type body: str

        :return: A Deferred instance for the sending of the message.
        :rtype: twisted.internet.defer.Deferred
        """
        # Use None for names and Message class handles names itself.
        ids_names = {r.obj_id: None for r in recipients}
        d = self.mailbox.send_message(self.name, ids_names, subject, body)
        d.addCallback(self.notify_sent)
        return d

    def get_mail_message(self, message_index):
        """:rtype: twisted.internet.defer.Deferred"""
        return self.mailbox.get_message(message_index)

    def get_next_unread_message(self):
        """:rtype: twisted.internet.defer.Deferred"""
        return self.mailbox.get_next_unread_message()

    def notify_new_mail(self, message):
        whostr = message.from_name
        if self.has_perm('see object numbers'):
            whostr += ' (#%d)' % message.from_id
        m = '{gYou have new mail '
        index = message.recipient_indexes.get(self.obj_id, None)
        if index is not None:
            m += '({y%d{g) ' % index
        m += 'from {c%s{g.' % whostr
        self.msg(m)

    def notify_sent(self, message):
        recips = and_list(['{c%s{g' % self.format_recipient(rname, rid)
                           for rid, rname in message.recipients.iteritems()])
        m = '{gMail sent to %s.' % recips
        self.msg(m)
        return message
