import re


class SyntaxParseError(Exception):
    pass


class Syntax(object):
    """
    Load a natural syntax spec and prepare for parsing!

        [ ] = Optional segment.
        < > = User value (named). Values in parse dict with named keys.
        { } = Required from set. Values in parse dict with 'optset#' keys.

        User value spec:
            <name>[:<pattern>]
            ie: <userval:[0-9]+>
    """
    natural = None
    regex = None
    _compiled = None

    def __init__(self, syntax):
        self.natural = syntax
        self.regex = self.syntax_to_regex(syntax)
        self._compiled = re.compile(self.regex, re.I)

    def syntax_to_regex(self, syntax):
        regex = ['^']

        i = 0
        optsets = 0
        lastchar = ''
        optBeganWithSpace = False
        while i < len(syntax):
            char = syntax[i]
            if char == '[':
                if lastchar == ' ':
                    # Optional group after a space. Include space in optional
                    # group. We set the flag so that we know if we should also
                    # include a space trailing an optional within the optional.
                    # If the optional is surrounded by spaces, one is required.
                    optBeganWithSpace = True
                    regex = regex[:-1]
                    regex.extend(['(?: +'])
                else:
                    optBeganWithSpace = False
                    regex.append('(?:')
                    lastchar = ''
            elif char == ']':
                regex.append(')?')
                lastchar = ']'
            elif char == '<':
                lastchar = ''
                end = syntax.find('>', i)
                if end == -1:
                    raise SyntaxParseError('Missing closing >')
                userval = syntax[i + 1:end]
                i = end
                name, sep, pat = userval.partition(':')
                if pat == '':
                    pat = '.+?'
                regex.append('(?P<%s>%s)' % (name, pat))
            elif char == '{':
                lastchar = ''
                end = syntax.find('}', i)
                if end == -1:
                    raise SyntaxParseError('Missing closing }')
                opt_spec = syntax[i + 1:end]
                i = end
                opt_regexes = []
                for opt in [s.strip() for s in opt_spec.split('|')]:
                    opt_re = self.syntax_to_regex(opt).rstrip('$').lstrip('^')
                    opt_regexes.append(opt_re)
                optsets += 1
                regex.append('(?P<optset%d>' % optsets)
                regex.append('(?:%s))' % ')|(?:'.join(opt_regexes))
            else:
                if char == ' ' and lastchar == ' ':
                    pass
                else:
                    if char == ' ':
                        if lastchar == ']' and not optBeganWithSpace:
                            regex = regex[:-1]
                            regex.append(' +)?')
                        else:
                            regex.append(' +')
                    else:
                        regex.append(re.escape(char))
                    lastchar = char
            i += 1

        regex.append('$')
        return ''.join(regex)

    def parse(self, string):
        m = self._compiled.search(string)
        if m:
            return m.groupdict()
        return False
