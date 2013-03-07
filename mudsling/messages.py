"""
Message formatting system.
"""
import string


class MessageParser(object):
    """
    The message parser is rather similar to string.Template, and even uses the
    same regex pattern. However, MessageParser returns a list meant to be used
    with Dynamic Messages rather than a substituted string.
    """
    @classmethod
    def parse(cls, tpl, **keywords):
        """
        Parses a message template into a list of strings or other values
        intended to pass through dynamic substitution, such as in objects'
        .msg() method.

        @param tpl: The template on which to perform substitutions.
        @type tpl: str

        @param keywords: The keywords and values for substitution.
        @type keywords: dict

        @return: list for use in dynamic message substitution.
        @rtype: list
        """
        return cls._parse(tpl, keywords)

    @classmethod
    def _parse(cls, tpl, keywords):
        """
        The workhorse behind parse. Can be called if you don't want to specify
        keyword arguments and instead wish to pass a dict directly.

        @type tpl: str
        @type keywords: dict
        @rtype: list
        """
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


class MessagedObject(object):
    """
    A base class to provide message template storage and retrieval to
    subclasses.

    @ivar messages: The message keys and their template strings or tuples. Most
        cases should ideally see this only set at the class level rather than
        overridding on instances.
    @type messages: dict
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
    ...         ("You touch $box and it buzzes loudly!",
    ...          "$box buzzes loudly as $actor touches it!"),
    ...         "$box does nothing when touched by $actor."
    ...     ]
    ... }
    """

    def getMessage(self, key, **keywords):
        """
        Retrieve a dictionary whose keys are either objects or the string '*'.

        The returned dictionary uses its keys to indicate what messages should
        be seen by which objects. If an object receiving the message does not
        have its own key, then it should see the message in '*'.

        MessagedObject does not provide an application of the return value.
        That is up to the implementor.

        @param key: The key name of the message to generate.
        @param keywords: The keywords for substitution.

        @return: Single string to show all objects, or a tuple
        @rtype: dict
        """
