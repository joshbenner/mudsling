"""
Various functions and utilities for matching game-world objects.
"""
import re

from mudsling.errors import MatchError, AmbiguousMatch, FailedMatch
import mudsling.utils.string as str_utils
import mudsling.utils.string.ansi as ansi

ordinal_words = ('first', 'second', 'third', 'fourth', 'fifth', 'sixth',
                 'seventh', 'eighth', 'ninth', 'tenth')
ordinal_pattern = r"^(?:(?P<word>" + '|'.join(ordinal_words) + ")"
ordinal_pattern += r"|(?:(?P<num>\d+)(?:st|nd|rd|th))) +(?P<subject>.+)$"
ordinal_re = re.compile(ordinal_pattern, re.I)


def match_stringlists(search, stringlists, exact=False, err=False,
                      case_sensitive=False, ordinal=True):
    """
    Match a search query against a dictionary of string lists. The result list
    will include keys from the dictionary which match the search.

    Match is a begins-with match, unless an exact match is found, in which case
    it is used. The results will include either prefix-based matches, or exact
    matches -- never both.

    Strips ANSI codes and tokens from search query and all names to match.

    :param search: The search string.
    :type search: str
    :param stringlists: Dict of lists of strings.
    :type stringlists: dict
    :param exact: Only look for exct matches.
    :type exact: bool
    :param err: If true, may raise AmbiguousMatch or FailedMatch.
    :type err: bool

    :return: A list of 0 or more keys from stringlists.
    :rtype: list
    """
    # Lower-case search for case insensitivity.
    srch = ansi.strip_ansi(search if case_sensitive else search.lower())
    if ordinal:
        ord, srch = parse_ordinal(srch)
    else:
        ord = 1
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

    if ordinal and ord is not None and ord > 0:
        result = result[ord - 1:ord]

    if err and len(result) != 1:
        if len(result) > 1:
            raise AmbiguousMatch(query=search, matches=result)
        else:
            if ordinal:
                try:  # Try without parsing the ordinal?
                    result = match_stringlists(search, stringlists,
                                               exact=exact,
                                               err=err,
                                               case_sensitive=case_sensitive,
                                               ordinal=False)
                except MatchError:
                    raise FailedMatch(query=search)
            else:
                raise FailedMatch(query=search)
    return result


def match_objlist(search, objlist, varname="names", exact=False, err=False):
    """
    Match a search query against a list of objects using string values from the
    provided instance variable.

    :param search: The search string.
    :param objlist: An iterable containing objects to match.
    :param varname: The instance variable on the objects to match against.
    :param exact: Only look for exact matches.
    :param err: If true, may raise AmbiguousMatch or FailedMatch.

    :rtype: list
    """
    strings = dict(zip(objlist, map(lambda v: v() if callable(v) else v,
                                    [getattr(o, varname) for o in objlist])))
    return match_stringlists(search, strings, exact=exact, err=err)


def parse_ordinal(text):
    """
    Parses an ordinal reference at the beginning of the string, returning the
    corresponding integer and the rest of the string. If no ordinal was used,
    then None is passed instead.

    :param text: String to parse.
    :type text: str

    :returns: A tuple containing the ordinal delta and the rest of the string.
    :rtype: tuple
    """
    match = ordinal_re.match(text)
    if match:
        groups = match.groupdict()
        subject = groups['subject']
        try:
            if groups['num'] is not None:
                delta = int(groups['num'])
            else:
                delta = ordinal_words.index(groups['word'].lower()) + 1
        except ValueError:
            delta = None
    else:
        delta = None
        subject = text
    return delta, subject


def match_failed(matches, search=None, search_for=None, show=False, names=str):
    """
    Utility method to handled failed matches. Will return a message if a
    search for a single match has failed and return False if the search
    succeeded.

    :param matches: The result of the match search.
    :type matches: list

    :param search: The string used to search.
    :type search: str

    :param search_for: A string describing what type of thing was being
        searched for. This should be the singular form of the word.
    :type search_for: str

    :param show: If true, will show the list of possible matches in the
        case of an ambiguous match.
    :type show: bool

    :param names: A function to use to convert match objects to string names.
    :type names: function

    :return: Message if match failed, or False if match did not fail.
    :rtype: str or bool
    """
    if len(matches) == 1:
        return False
    elif len(matches) > 1:
        if search is not None:
            if search_for is not None:
                msg = ("Multiple %s match '%s'"
                       % (str_utils.inflection.plural(search_for), search))
            else:
                msg = "Multiple matches for '%s'" % search
        else:
            if search_for is not None:
                msg = "Multiple %s found"
                msg %= str_utils.inflection.plural(search_for)
            else:
                msg = "Multiple matches"
        if show:
            msg += ': ' + str_utils.english_list(matches, formatter=names)
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
                msg = "No matching %s found."
                msg %= str_utils.inflection.plural(search_for)
            else:
                msg = "No match found."
    return msg
