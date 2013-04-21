"""
Message formatting system.
"""
import string
import random
import copy

import zope.interface


class InvalidMessage(Exception):
    pass


class MessageParser(object):
    """
    The message parser is rather similar to L{string.Template}, and even uses
    the same regex pattern. However, L{MessageParser} returns a list meant to
    be used with L{Dynamic Messages} rather than a substituted string.
    """
    @classmethod
    def parse(cls, tpl, **keywords):
        """
        Parses a message template into a list of strings or other values
        intended to pass through dynamic substitution, such as in objects'
        .msg() method.

        @param tpl: The template on which to perform substitutions.
        @type tpl: C{str}

        @param keywords: The keywords and values for substitution.
        @type keywords: C{dict}

        @return: list for use in dynamic message substitution.
        @rtype: C{list}
        """
        return cls._parse(tpl, keywords)

    @classmethod
    def _parse(cls, tpl, keywords):
        """
        The workhorse behind parse. Can be called if you don't want to specify
        keyword arguments and instead wish to pass a dict directly.

        @type tpl: C{str}
        @type keywords: C{dict}
        @rtype: C{list}
        """
        if not tpl:  # Blank messages should yield nothing.
            return None

        def subst(name):
            if name in keywords:
                return keywords[name]
            return "${{{}}}".format(name)

        parts = string.Template.pattern.split(tpl)
        out = []
        i = 0
        nparts = len(parts)
        while i < nparts:
            prefix = parts[i]
            if prefix:
                out.append(prefix)

            if nparts > i + 1:
                escaped, named, braced, invalid = parts[i + 1:i + 5]
                if escaped is not None:
                    out.append('$')
                elif named is not None:
                    out.append(subst(named))
                elif braced is not None:
                    out.append(subst(braced))
                elif invalid is not None:
                    # todo: Raise error? Substitute something else?
                    out.append('$')
            i += 5

        return out


class IHasMessages(zope.interface.Interface):
    """
    Describes a class which provides a series of message templates.
    """
    messages = zope.interface.Attribute("""A Messages instance.""")

    def get_message(key, **keywords):
        """
        Retrieve a formatted message string or dictionary.
        @see: L{Messages.get_message}
        """


class Messages(object):
    """
    A collection of message templates which can participate in message
    retrieval and formatting.
    """

    messages = {}
    """
    Example format:
    >>> messages = {
    ...     # A message that is a dictionary can identify if objects identified
    ...     # by certain keywords should see a different message template.
    ...     'open': {
    ...         'actor': "You open $box.",
    ...         '*': "$actor opens $box."
    ...     },
    ...     # If message is just a single string template, then everyone sees
    ...     # the same thing.
    ...     'glow': "$box glows mysteriously...",
    ...     # Randomly or specifically select from several templates for a
    ...     # single message key.
    ...     'touch': [
    ...         {'actor': "You touch $box and it buzzes loudly!",
    ...          '*': "$box buzzes loudly as $actor touches it!"},
    ...         "$box does nothing when touched by $actor."
    ...     ]
    ... }
    """

    def __init__(self, messages=None):
        self.messages = messages or {}

    def _get_message(self, key, index=None):
        """
        Retrieves the raw message configuration.

        If no message is found, returns C{None}.

        @param key: The message key to retrieve.
        @type key: C{str}

        @param index: For a multi-value message (defined with a list), specify
            the numeric index of the message from the list to return. If None
            or not specified, then will return a random selection.
        @type index: C{None} or C{int}

        @raise C{IndexError}: If index is out of range for message list.
        @raise C{ValueError}: In the case of nested list messages.
        @raise L{InvalidMessage}: If resulting message is not a valid message.

        @return: A message dictionary.
        @rtype: C{dict} or C{None}
        """
        msg = self.messages.get(key, None)

        if msg is None:
            return msg

        if isinstance(msg, list):
            if index is not None:
                msg = msg[index]
            else:
                msg = random.choice(msg)
            if isinstance(msg, list):
                raise ValueError("Message lists cannot be nested.")

        if isinstance(msg, basestring):
            msg = {'*': msg}
        elif isinstance(msg, dict):
            msg = copy.deepcopy(msg)
            if '*' not in msg:
                msg['*'] = None
        else:
            raise InvalidMessage("Message is not str or dict")

        return msg

    def get_message(self, key, **keywords):
        """
        Retrieve a dictionary whose keys are either objects or the string '*'.

        The returned dictionary uses its keys to indicate what messages should
        be seen by which objects. If an object receiving the message does not
        have its own key, then it should see the message in '*'.

        The values of the dictionary are Dynamic Message lists.

        @param key: The key name of the message to generate. Alternately, can
            be an already-loaded message dict.
        @type key: C{str} or C{dict}

        @param keywords: The keywords for substitution.
        @type keywords: C{dict}

        @return: The message dictionary.
        @rtype: C{dict}
        """
        msg = key if isinstance(key, dict) else self._get_message(key)

        for who, tpl in msg.iteritems():
            msg[who] = MessageParser._parse(tpl, keywords)

        for kw, val in keywords.iteritems():
            if kw in msg:
                msg[val] = msg[kw]
                del msg[kw]

        return msg