import os
import markdown
import logging
import re

from fuzzywuzzy import process

from mudsling import parsers
from mudsling import errors
from mudsling import mxp

from mudsling import utils
import mudsling.utils.file


md = markdown.Markdown(extensions=['meta', 'wikilinks'])


def mxpLink(text, topic):
    return mxp.send(text, "?%s" % topic, "Get help for %s" % topic)


def _mxpTopicLink(match):
    """
    Regex .sub() callback for replacing a Markdown link with an MXP tag to
    send the help command for the topic.
    """
    return mxpLink(match.group('title'), match.group('link'))


def _mxpWikiLink(match):
    return mxpLink(match.group('link'), match.group('link'))


def _mxpHeading(match):
    return mxp.closedTag('b', match.group('text').strip())


def _mxpBold(match):
    return mxp.bold(match.group('text'))


def _mxpUnderline(match):
    return mxp.underline(match.group('text'))


def _mxpItalic(match):
    return mxp.italic(match.group('text'))


class HelpEntry(object):
    id = ""
    filepath = ""
    priority = 0
    title = ""
    names = ()
    meta = {}
    required_perm = None

    mud_text_transforms = (
        (re.compile(r"\[(?P<title>.*?)\]\((?P<link>.*?)\)"), _mxpTopicLink),
        (re.compile(r"\[\[(?P<link>.*?)\]\]"), _mxpWikiLink),
        (re.compile(r"`(.*?)`"), r'{c\1{n'),
        (re.compile(r"^#+\s*(?P<text>.+)$", re.MULTILINE), r"{y\1"),
        (re.compile(r"(\*\*|__)(?P<text>.*?)\1"), _mxpBold),
        (re.compile(r"(\*|_)(?P<text>.*?)\1"), _mxpItalic)
    )

    def __init__(self, filepath):
        self.filepath = os.path.abspath(filepath)
        filename = os.path.basename(filepath)
        self.id = filename.rsplit('.', 1)[0]
        self.title = self.id.replace('_', ' ')
        self.names = [self.title.lower()]

        with open(os.devnull, 'w') as f:
            md.reset().convertFile(filepath, output=f)

        try:
            self.meta = md.Meta
            del md.Meta
        except AttributeError:
            self.meta = {}

        if 'id' in self.meta:
            self.id = str(self.meta['id'])
        if 'title' in self.meta:
            self.title = self.meta['title']
            self.names[0] = self.title.lower()
        if 'aliases' in self.meta:
            parse = parsers.StringListStaticParser.parse
            self.names[1:] = map(str.lower, parse(self.meta['aliases']))
        if 'required_perm' in self.meta:
            self.required_perm = str(self.meta['required_perm'])
        if 'priority' in self.meta:
            try:
                self.priority = int(self.meta['priority'])
            except ValueError:
                logging.warning("Invalid priority in %s" % filepath)

    def __str__(self):
        return self.title

    def __repr__(self):
        return "<Help Topic '%s'>" % self.title

    def mudText(self):
        """
        Get text appropriate to output to a MUD session.
        """
        if 'lines' in md.__dict__:
            del md.lines
        with open(os.devnull, 'w') as f:
            md.reset().convertFile(self.filepath, output=f)
            try:
                text = '\n'.join(md.lines).strip()
            except AttributeError:
                text = "This help file has not yet been written."
        for regex, replace in self.mud_text_transforms:
            text = regex.sub(replace, text)
        return text


class HelpManager(object):
    def __init__(self):
        self.entries = {}
        self.name_map = {}
        self.all_names = []

    def loadHelpPath(self, path, rebuildNameMap=True):
        count = 0
        for filepath in utils.file.scan_path(path, "*.md", recursive=True):
            entry = HelpEntry(filepath)
            if not entry.title:
                logging.warning("Help file has empty title: %s" % filepath)
                continue
            if not entry.id:
                logging.warning("Help file has empty id: %s" % filepath)
                continue
            if (entry.id in self.entries
                    and self.entries[entry.id].priority >= entry.priority):
                logging.info("Help file ignored: %s" % filepath)
                continue
            self.entries[entry.id] = entry
            count += 1
        if rebuildNameMap:
            self.rebuildNameMap()
        logging.info("Loaded %d help files from %s" % (count, path))

    def rebuildNameMap(self):
        mapping = {}
        for e in self.entries.itervalues():
            for n in e.names:
                if n in mapping and mapping[n].priority >= e.priority:
                    continue
                mapping[n] = e
        self.name_map = mapping
        self.all_names = self.name_map.keys()

    def findTopic(self, search):
        matches = [x for x in process.extract(search.lower(), self.all_names)
                   if x[1] >= 85]
        if not matches:
            raise errors.FailedMatch(msg="No help found for '%s'." % search)
        elif (len(matches) == 1
              or matches[0][1] - matches[1][1] >= 10
              or matches[0][0] == search.lower()):
            return self.name_map[matches[0][0]]

        # We know we have two or more elements that are 10 or more score apart.
        raise errors.AmbiguousMatch(query=search,
                                    matches=[x[0] for x in matches])


help_db = HelpManager()
