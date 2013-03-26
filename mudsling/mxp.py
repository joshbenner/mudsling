"""
MXP implementation.
"""
import re


TELNET_OPT = chr(91)
LT = '\x03'
GT = '\x04'
AMP = '\x06'

TAG_PAT = LT + '.*?' + GT
ENTITY_PAT = AMP + '.*?;'
TAG_RE = re.compile('(' + TAG_PAT + ')')
ENTITY_RE = re.compile('(' + ENTITY_PAT + ')')
TAG_ENTITY_RE = re.compile('(' + TAG_PAT + '|' + ENTITY_PAT + ')')
SPECIAL_CHARS = (
    ('<', '&lt;'),
    ('>', '&gt;'),
    ('&', '&amp;'),
)
MXP_ENCODING = (
    (LT, '<'),
    (GT, '>'),
    (AMP, '&'),
)


def tag(name, **attr):
    """
    Returns an encoded MXP tag string containing the special replacement
    characters that should be replaced later.

    @param name: The tag name.
    @type name: C{str}

    @param attr: Dictionary of attributes to send in opening tag.
    @type attr: C{dict}
    """
    out = LT + str(name)
    attrStr = ' '.join(['%s="%s"' % (k, v) for k, v in attr.iteritems()])
    if attrStr:
        out += ' ' + attrStr
    return out + GT


def entity(entity):
    return AMP + str(entity) + ';'


def closedTag(name, content, **attr):
    """
    Return an encoded MXP tag including content and closing tag.

    @param name: The tag name.
    @type name: C{str}

    @param content: The contents between open and closing tags.
    @type content: C{str}

    @param attr: Dictionary of attributes to send in opening tag.
    @type attr: C{dict}

    @rtype: str
    """
    return tag(name, **attr) + str(content) + tag('/' + name)


def strip(text):
    """
    Strips encoded MXP tags and entities out of text.
    """
    return TAG_ENTITY_RE.sub('', text)


def encodeSpecial(text):
    """
    Replaces special characters with their entity-encoded versions.
    """
    for char, encoded in SPECIAL_CHARS:
        text = text.replace(char, encoded)
    return text


def unencodeMxp(text):
    """
    Replaces encoded MXP characters with the natural form. ie: LT to '<'.
    """
    for encoded, unencoded in MXP_ENCODING:
        text = text.replace(encoded, unencoded)
    return text


def prepare(text):
    """
    Prepares text for output to the client. This involves converting encoded
    tags and entities to their natural forms, as well as entity-encoding any
    special characters.
    """
    parts = TAG_ENTITY_RE.split(text)
    for i, part in enumerate(parts):
        if i % 2 == 0:  # Only create entities outside MXP-encoded sequences.
            parts[i] = encodeSpecial(part)
        else:  # Convert encoded MXP sequences to their normal form.
            parts[i] = unencodeMxp(part)
    return ''.join(parts)
