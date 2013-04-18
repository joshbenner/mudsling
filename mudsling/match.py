"""
Various functions and utilities for matching game-world objects.
"""
import re
import inflect

from mudsling.errors import AmbiguousMatch, FailedMatch
from mudsling.utils import string
from mudsling.utils.string import ansi

ordinal_words = ('first', 'second', 'third', 'fourth', 'fifth', 'sixth',
                 'seventh', 'eighth', 'ninth', 'tenth')
ordinal_regex = "^(" + '|'.join(ordinal_words) + ")(.*)$"


def match_stringlists(search, stringlists, exact=False, err=False,
                      case_sensitive=False):
    """
    Match a search query against a dictionary of string lists. The result list
    will include keys from the dictionary which match the search.

    Match is a begins-with match, unless an exact match is found, in which case
    it is used. The results will include either prefix-based matches, or exact
    matches -- never both.

    Strips ANSI codes and tokens from search query and all names to match.

    @param search: The search string.
    @type search: str
    @param stringlists: Dict of lists of strings.
    @type stringlists: dict
    @param exact: Only look for exct matches.
    @type exact: bool
    @param err: If true, may raise AmbiguousMatch or FailedMatch.
    @type err: bool

    @return: A list of 0 or more keys from stringlists.
    @rtype: list
    """
    # Lower-case search for case insensitivity.
    srch = ansi.strip_ansi(search if case_sensitive else search.lower())
    exact_matches = []
    partial = []

    for key, names in stringlists.iteritems():
        if len(names) == 0:
            continue
        # Lowercase everything if this is case-insensitive
        if not case_sensitive:
            names = [s.lower() for s in names]
        names = [ansi.strip_ansi(s) for s in names]

        # Check for exact or else partial match.
        if srch in names:
            exact_matches.append(key)
        elif not exact and not exact_matches:
            if len([s for s in names if s.startswith(srch)]) > 0:
                partial.append(key)

    result = exact_matches or partial

    if err and len(result) != 1:
        if len(result) > 1:
            raise AmbiguousMatch(query=search, matches=result)
        else:
            raise FailedMatch(query=search)
    else:
        return result


def match_objlist(search, objlist, varname="names", exact=False, err=False):
    """
    Match a search query against a list of objects using string values from the
    provided instance variable.

    @param search: The search string.
    @param objlist: An iterable containing objects to match.
    @param varname: The instance variable on the objects to match against.
    @param exact: Only look for exact matches.
    @param err: If true, may raise AmbiguousMatch or FailedMatch.

    @rtype: list
    """
    strings = dict(zip(objlist, map(lambda v: v() if callable(v) else v,
                                    [getattr(o, varname) for o in objlist])))
    return match_stringlists(search, strings, exact=exact, err=err)


def match_nth(nth, search, objlist, varname="names"):
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


def match(search, objlist, varname="names"):
    """
    Attempt various types of matching using other functions found in match
    module.

    @param search: The string to search for among the objects.
    @param objlist: The objects to search.
    @param varname: The name of the instance variable containing the string(s)
        to search against.

    @rtype: list
    """
    matches = match_objlist(search, objlist, varname)
    if matches:
        return matches

    parsed = parse_ordinal(search)
    if parsed is not None:
        matches = match_nth(*parsed, objlist=objlist, varname=varname)
        if matches:
            return matches

    return []


def match_failed(matches, search=None, search_for=None, show=False):
    """
    Utility method to handled failed matches. Will return a message if a
    search for a single match has failed and return False if the search
    succeeded.

    @param matches: The result of the match search.
    @type matches: list

    @param search: The string used to search.
    @type search: str

    @param search_for: A string describing what type of thing was being
        searched for. This should be the singular form of the word.
    @type search_for: str

    @param show: If true, will show the list of possible matches in the
        case of an ambiguous match.
    @type show: bool

    @return: Message if match failed, or False if match did not fail.
    @rtype: C{str} or C{bool}
    """
    p = inflect.engine()

    if len(matches) == 1:
        return False
    elif len(matches) > 1:
        if search is not None:
            if search_for is not None:
                msg = ("Multiple %s match '%s'"
                       % (p.plural(search_for), search))
            else:
                msg = "Multiple matches for '%s'" % search
        else:
            if search_for is not None:
                msg = "Multiple %s found" % p.plural(search_for)
            else:
                msg = "Multiple matches"
        if show:
            msg += ': ' + string.english_list(matches)
        else:
            msg += '.'
    else:
        if search is not None:
            if search_for is not None:
                msg = "No %s called '%s' was found." % (search_for, search)
            else:
                msg = "No '%s' was found." % search
        else:
            if search_for is not None:
                msg = "No matching %s found." % p.plural(search_for)
            else:
                msg = "No match found."
    return msg
