from twisted.internet.defer import inlineCallbacks, returnValue

from mudsling.commands import Command, SwitchCommandHost
from mudsling import locks
from mudsling import parsers
from mudsling import errors
from mudsling.utils.time import format_timestamp
from mudsling.utils.string import plural_noun

from mudslingcore.editor import EditorError
from mudslingcore.mail.editor import MailEditorSession


use_mail = locks.Lock('has_perm(use mail)')


class RecipientsParser(parsers.Parser):
    def parse(self, input, actor=None):
        from mudslingcore.mail import MailRecipient
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

    see_obj_nums = False

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

    def prepare(self):
        self.see_obj_nums = self.actor.has_perm('see object numbers')
        return super(MailSubCommand, self).prepare()

    def execute(self):
        from mudslingcore.mail import MailError
        try:
            return super(MailSubCommand, self).execute()
        except MailError as e:
            raise self._err('{r' + e.message)

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
        from mudslingcore.mail import MailError
        err.trap(errors.MatchError, MailError)
        if err.check(errors.MatchError, MailError):
            self.actor.tell('{r', err.getErrorMessage().strip("'"))

    def _whostr(self, text, id):
        """:rtype: str"""
        out = text
        if self.see_obj_nums:
            out += ' (#%d)' % id
        return str(out)

    @inlineCallbacks
    def _load_body(self, message):
        yield message.load_body()
        returnValue(message)

    def _show_message(self, message):
        """
        :type message: mudslingcore.mail.Message
        """
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
        body = '%s\n\n%s' % (t, message.body)
        title = 'Message %d' % message.mailbox_index
        self.actor.msg(ui.report(title, body))
        return message

    def _mark_read(self, message):
        message.mark_read(self.obj.obj_id)

    def read_message_callbacks(self, deferred):
        deferred.addCallback(self._load_body)
        deferred.addCallback(self._show_message)
        deferred.addCallback(self._mark_read)


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
        from mudslingcore.mail import MailError
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
        session = MailEditorSession(actor,
                                    recipients=recipients,
                                    subject=subject)
        try:
            actor.player.register_editor_session(session, activate=True)
        except EditorError as e:
            raise self._err(e.message)
        actor.tell('{gYou are now composing ', session.description, '.')


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


class MailNextCmd(MailReadCmd):
    """
    @mail/next

    Read the oldest unread message.
    """
    aliases = ('next',)
    syntax = ''
    arg_parsers = {}

    def run(self, **kw):
        d = self.mailbox.get_next_unread_message()
        d.addCallback(self._validate_next)
        self.read_message_callbacks(d)
        d.addErrback(self._show_error)

    def _validate_next(self, message):
        if message is None:
            from mudslingcore.mail import MailError
            raise MailError("There are no new messages.")
        return message


class MailCommand(SwitchCommandHost):
    """
    @mail[/<subcommand>] [<subcommand parameters>]

    Issue a mail command.
    """
    aliases = ('@mail',)
    lock = use_mail
    default_switch = 'list'
    subcommands = (MailListCmd, MailNewCmd, MailSendCmd, MailReadCmd,
                   MailNextCmd)
