"""
Various functions and utilities for matching game-world objects.
"""
import re

from mudsling.errors import AmbiguousMatch, FailedMatch

ordinal_words = ('first', 'second', 'third', 'fourth', 'fifth', 'sixth',
                 'seventh', 'eighth', 'ninth', 'tenth')
ordinal_regex = "^(" + '|'.join(ordinal_words) + ")(.*)$"


def match_objlist(search, objlist, varname="aliases", exactOnly=False,
                  err=False):
    """
    Match a search query against a list of objects using string values from the
    provided instance variable.

    Match is a begins-with match, unless an exact match is found, in which case
    it is used. The results will include either prefix-based matches, or exact
    matches -- never both.

    @param search: The search string.
    @param objlist: An iterable containing objects to match.
    @param varname: The instance variable on the objects to match against.
    @param exactOnly: Only look for exact matches.
    @param err: If true, may raise AmbiguousMatch or FailedMatch.

    @rtype: set
    """

    def make_names(val):
        """
        Build a names list for the value, whether it's a string or iterable
        @return: list
        """
        if isinstance(val, basestring):
            return {val}
        else:
            try:
                return set(val)
            except TypeError:
                return set()

    # Lower-case search for case insensitivity.
    srch = search.lower()
    exact = set()
    partial = set()

    for obj in objlist:
        try:
            varval = getattr(obj, varname)
        except AttributeError:
            continue

        # Lowercase everything so that this is case-insensitive
        names = [s.lower() for s in make_names(varval)]
        if len(names) == 0:
            continue

        # Check for exact or else partial match.
        if srch in names:
            exact.add(obj)
        elif not exactOnly and not exact:
            if len([s for s in names if s.startswith(srch)]) > 0:
                partial.add(obj)

    result = exact or partial

    if err and len(result) != 1:
        if len(result) > 1:
            raise AmbiguousMatch(query=search, matches=result)
        else:
            raise FailedMatch(query=search)
    else:
        return result


def match_nth(nth, search, objlist, varname="aliases"):
    raise NotImplemented


def parse_ordinal(string):
    """
    Parses an ordinal reference at the beginning of the string, returning the
    corresponding integer and the rest of the string. Returns None on failure.

    @param string: String to parse.

    @rtype: tuple
    """
    match = re.match(r"^(\d+)(?:st|nd|rd|th)(.*)$", string)
    if match:
        return int(match.group(1)), match.group(2).strip()

    match = re.match(ordinal_regex, string)
    if match and match.group(1) in ordinal_words:
        val = ordinal_words.index(match.group(1)) + 1
        return val, match.group(2).strip()

    return None


def match(search, objlist, varname="aliases"):
    """
    Attempt various types of matching using other functions found in match
    module.

    @param search: The string to search for among the objects.
    @param objlist: The objects to search.
    @param varname: The name of the instance variable containing the string(s)
        to search against.

    @rtype: set
    """
    matches = match_objlist(search, objlist, varname)
    if matches:
        return matches

    parsed = parse_ordinal(search)
    if parsed is not None:
        matches = match_nth(*parsed, objlist=objlist, varname=varname)
        if matches:
            return matches

    return set()
