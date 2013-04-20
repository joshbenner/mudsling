import re
import socket

from twisted.mail.smtp import ESMTPSenderFactory, sendmail
from twisted.internet.defer import Deferred
from twisted.internet import reactor
from twisted.internet import threads

from cStringIO import StringIO
from email.generator import Generator

import mailer

EMAIL_RE = re.compile(r"(?P<local>[^@]+)@(?P<domain>[^@]+)")


# Proxy the message class within our own email module for easy access.
Message = mailer.Message


class TwistedMailer(mailer.Mailer):
    """
    Twisted version of the simple Mailer.
    """

    def send(self, msg):
        if self._usr or self._pwd:
            factory = ESMTPSenderFactory(self._usr, self._pwd)


def _sendmail(fromAddress, toAddress, message, host='localhost', port=0,
              user=None, password=None, callback=None, errback=None):
    """
    Connect to an SMTP server and send an email message. If username and
    password are provided, ESMTP is used to connect, otherwise a standard SMTP
    connection is used.

    @param fromAddress: The SMTP reverse path (ie, MAIL FROM)
    @param toAddress: The SMTP forward path (ie, RCPT TO)
    @param message: An L{email.message.Message} instance (such as C{MIMEText}).
    @param host: The MX host to which to connect.
    @param port: The port number to which to connect.
    @param user: The username with which to authenticate.
    @param password: The password with which to authenticate.

    @return: A Deferred which will be called back when the message has been
        sent or which will errback if it cannot be sent.
    """
    if user or password:
        fp = StringIO()
        g = Generator(fp, mangle_from_=False, maxheaderlen=60)
        g.flatten(message)
        d = Deferred()
        factory = ESMTPSenderFactory(user, password, fromAddress, toAddress,
                                     message, d)
        reactor.connectTCP(host, port, factory)
    else:
        d = sendmail(host, fromAddress, toAddress, )

    return d


def valid_email(email):
    """
    Very basic check to see if provided email address seems valid.
    @rtype: C{bool}
    """
    return True if EMAIL_RE.match(email) else False


def reverse_dns(ip):
    """
    Perform a reverse-DNS lookup on a given IP address string. The lookup is
    asynchronous, so a callback is also required.

    @param ip: A string IP address.

    @return: A deferred. You should probably .addCallback().
    @rtype: L{twisted.internet.defer.Deferred}
    """
    return threads.deferToThread(lambda: socket.gethostbyaddr(ip)[0])
