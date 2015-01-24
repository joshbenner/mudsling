from mudsling.storage import ObjRef
from mudsling.utils.string import and_list

from mudslingcore.editor import EditorSession, EditorSessionCommand


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
        d.addCallbacks(self._notify_sent, self._notify_error)
        this.owner.terminate_editor_session(this.session_key)

    def _notify_sent(self, message):
        r = and_list(self.actor.name_for(ObjRef(r))
                     for r in message.recipients)
        self.actor.tell('{gMessage "{c', message.subject, '{g" sent to: {n', r)

    def _notify_error(self, error):
        error.printTraceback()


class MailEditorSession(EditorSession):
    __slots__ = ('recipients', 'subject', 'sender')

    commands = (MailEditorSendCmd,)

    def __init__(self, sender, recipients=(), subject=''):
        self.recipients = list(recipients)
        self.subject = subject
        self.sender = sender
        super(MailEditorSession, self).__init__(sender.player)

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
