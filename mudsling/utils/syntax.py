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
    named_captures = None

    class _ParseState(object):
        def __init__(self):
            self.i = 0
            self.optsets = 0
            self.depth = []

    def __init__(self, syntax):
        self.natural = syntax
        self._named_captures = []
        self.regex = self._to_regex(syntax)
        self._compiled = re.compile(self.regex, re.I)

    def _peek(self, i):
        if i < len(self.natural):
            return self.natural[i]
        return None

    def _to_regex(self, syntax, state=None):
        if not state:
            prefix = '^(?P<argstr>'
            suffix = ')$'
            state = Syntax._ParseState()
        else:
            prefix = ''
            suffix = ''
            state.i += 1
        regex = []
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
                    state.i += 1
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
                self._named_captures.append(name)
                fmt = '(?:(?P<__quoted_{0}>"{1}")|(?P<__unquoted_{0}>{1}))'
                regex.append(fmt.format(name, pat))
            elif char == ' ':
                if lastchar != ' ' and lastchar != 'OR' and len(regex):
                    regex.append(' +')
            elif char == '|' and state.depth[-1] == '}':
                if lastchar == ' ':
                    regex.pop()
                regex.append('|')
                lastchar = 'OR'
                state.i += 1
                continue
            else:
                regex.append(re.escape(char))
            lastchar = char
            state.i += 1

        # Trim trailing spaces.
        if lastchar == ' ':
            regex.pop()

        return prefix + ''.join(regex) + suffix

    def parse(self, string):
        m = self._compiled.search(string)
        if m:
            out = m.groupdict()
            for nc in self._named_captures:
                qkey = "__quoted_%s" % nc
                ukey = "__unquoted_%s" % nc
                quoted = out[qkey]
                if isinstance(quoted, str):
                    quoted = quoted.strip('"')
                unquoted = out[ukey]
                del out[qkey], out[ukey]
                out[nc] = quoted or unquoted or None
            return out
        return False


if __name__ == '__main__':
    import time
    testCases = {
        '<class> {named|called|=} <names>': [
            'thing named foo',
        ],
        '<exitSpec> to <room>': [
            '"Room to Delete"',
        ],
    }

    for spec, tests in testCases.iteritems():
        syntax = Syntax(spec)
        print spec, '->', syntax.regex
        for t in tests:
            start = time.clock()
            r = syntax.parse(t)
            duration = (time.clock() - start) * 1000
            print '  ', t, '->', r
            print '  (%.3fms)' % duration
