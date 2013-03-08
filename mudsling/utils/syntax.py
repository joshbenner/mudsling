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

    class _ParseState(object):
        def __init__(self):
            self.i = 0
            self.optsets = 0
            self.depth = []

    def __init__(self, syntax):
        self.natural = syntax
        self.regex = self._to_regex(syntax)
        self._compiled = re.compile(self.regex, re.I)

    def _peek(self, i):
        if i < len(self.natural):
            return self.natural[i]
        return None

    def _to_regex(self, syntax, state=None):
        if not state:
            regex = ['^']
            suffix = '$'
            state = Syntax._ParseState()
        else:
            regex = []
            suffix = ''
            state.i += 1
        lastchar = ''

        while state.i < len(syntax):
            char = syntax[state.i]
            if char == '[':
                state.depth.append(']')
                subpat = self._to_regex(syntax, state)
                if lastchar == ' ':
                    subpat = " +" + subpat
                elif self._peek(state.i + 1) == ' ':
                    subpat += " +"
                regex.append("(?:%s)?" % subpat)
            elif char == '{':
                state.depth.append('}')
                state.optsets += 1
                optset = state.optsets
                subpat = self._to_regex(syntax, state)
                regex.append("(?P<optset%d>%s)" % (optset, subpat))
            elif state.depth and char == state.depth[-1]:
                state.depth.pop()
                break
            elif char == '<':
                end = syntax.find('>', state.i)
                if end == -1:
                    raise SyntaxParseError("Missing closing '>'")
                userval = syntax[state.i + 1:end]
                state.i = end
                name, sep, pat = userval.partition(':')
                if pat == '':
                    pat = '.+?'
                regex.append('(?P<%s>%s)' % (name, pat))
            elif char == ' ':
                if lastchar != ' ':
                    regex.append(' +')
            else:
                regex.append(char)
            lastchar = char
            state.i += 1

        regex.append(suffix)
        return ''.join(regex)

    def parse(self, string):
        m = self._compiled.search(string)
        if m:
            return m.groupdict()
        return False
