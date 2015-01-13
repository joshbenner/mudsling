from twisted.internet.defer import inlineCallbacks

from mudsling.commands import Command, SwitchCommandHost
from mudsling import locks
from mudsling import parsers
from mudsling.utils.time import format_timestamp

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
        from mudslingcore.mail import MailError
        try:
            return super(MailSubCommand, self).execute()
        except MailError as e:
            raise self._err('{r' + e.message)

    def list_messages(self, messages, footer=''):
        ui = self.actor.get_ui()
        c = ui.Column
        t = ui.Table([
            c('ID', align='r', data_key='mailbox_index'),
            c('Date', align='l', data_key='timestamp',
              cell_formatter=format_timestamp, formatter_args=('short',)),
            c('From', align='l', data_key='from_name'),
            c('Subject', align='l', data_key='subject')
        ])
        if messages:
            t.add_rows(*messages.itervalues())
        else:
            t.add_row('(no messages found matching query)')
        self.actor.msg(ui.report('@mail: %d Messages' % len(messages), t,
                                 footer))


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
        f = 'Sequence: %s' % self.args['seq'] if seq is not None else ''
        if not seq:
            seq = '1-$ last:15'
        try:
            d = self.mailbox.get_messages_from_sequence(seq)
        except MailError as e:
            raise self._err(e.message)
        d.addCallback(self.list_messages, f)


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


class MailCommand(SwitchCommandHost):
    """
    @mail[/<subcommand>] [<subcommand parameters>]

    Issue a mail command.
    """
    aliases = ('@mail',)
    lock = use_mail
    default_switch = 'list'
    subcommands = (MailListCmd, MailSendCmd)
