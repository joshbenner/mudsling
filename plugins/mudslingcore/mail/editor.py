from mudsling.utils.string import and_list

from mudslingcore.editor import EditorSession, EditorSessionCommand
from mudslingcore.mail.recipient import match_recipients


class MailEditorSendCmd(EditorSessionCommand):
    """
    .send

    Sends the current buffer as an @mail message.
    """
    key = 'send'
    match_prefix = '.send'

    def run(self, this, actor):
        """
        :type this: MailEditorSession
        :type actor: mudslingcore.mail.MailRecipient
        """
        actor.tell('Sending message...')
        d = this.send_message()
        d.addErrback(self._notify_error)
        this.owner.terminate_editor_session(this.session_key)

    def _notify_error(self, error):
        error.printTraceback()


class MailEditorSubjectCmd(EditorSessionCommand):
    """
    .subject [<subject>]

    Displays the current subject, or sets a new subject.
    """
    key = 'subject'
    match_prefix = '.subj'
    syntax = '{.subj|.subject}\w[<subject>]'

    def run(self, this, actor, subject):
        """
        :type this: MailEditorSession
        :type actor: BaseObject
        :type subject: str
        """
        if subject is None:
            actor.tell('{cSubject{y: {n', this.subject)
        else:
            this.subject = subject
            actor.tell('Subject changed to "', subject, '".')


def fmt_recipient_list(recipients, actor):
    return '; '.join(actor.name_for(r) for r in recipients)


class MailEditorToCmd(EditorSessionCommand):
    """
    .to [<recipients>]

    Displays or sets the list of recipients for the message in the editor.
    """
    key = 'to'
    match_prefix = '.to'
    syntax = '.to [<recipients>]'
    arg_parsers = {'recipients': match_recipients}

    def run(self, this, actor, recipients):
        """
        :type this: MailEditorSession
        :type actor: BaseObject
        :type recipients: list of MailRecipient
        """
        if recipients is None:
            actor.tell('{cTo{y: {n',
                       fmt_recipient_list(this.recipients, actor))
        else:
            this.recipients = list(recipients)
            actor.tell('Message now addressed to: ',
                       fmt_recipient_list(recipients, actor))


class MailEditorAlsoToCmd(EditorSessionCommand):
    """
    .also-to <recipients>

    Add more recipients to the message in the editor.
    """
    key = 'also-to'
    match_prefix = '.also-to'
    syntax = '.also-to <recipients>'
    arg_parsers = {'recipients': match_recipients}

    def run(self, this, actor, recipients):
        """
        :type this: MailEditorSession
        :type actor: BaseObject
        :type recipients: list of MailRecipient
        """
        before = len(this.recipients)
        for r in recipients:
            if r not in this.recipients:
                this.recipients.append(r)
        if len(this.recipients) == before:
            actor.tell('{yNo new recipients.')
        else:
            actor.tell('{cTo{y: {n',
                       fmt_recipient_list(this.recipients, actor))


class MailEditorSession(EditorSession):
    __slots__ = ('recipients', 'subject', 'sender')

    commands = (MailEditorSendCmd, MailEditorSubjectCmd, MailEditorToCmd,
                MailEditorAlsoToCmd)

    def __init__(self, sender, recipients=(), subject='', body=''):
        self.recipients = list(recipients)
        self.subject = subject
        self.sender = sender
        super(MailEditorSession, self).__init__(sender.player, preload=body)

    @property
    def session_key(self):
        r = ','.join(map(lambda m: str(m.obj_id), self.recipients))
        return 'mail:%s:%s' % (r, self.subject)

    @property
    def description(self):
        r = and_list(map(self.owner.name_for, self.recipients))
        return "@mail message to %s regarding '%s'" % (r, self.subject)

    def send_message(self):
        """:rtype: twisted.internet.defer.Deferred"""
        return self.sender.send_mail(self.recipients, self.subject, self.text)
