import os
import logging
import re

import markdown

from fuzzywuzzy import process
from mudsling import parsers
from mudsling import errors
from mudsling import locks
from mudsling import utils
import mudsling.utils.file
from mudsling.utils.string import mxp


md = markdown.Markdown(extensions=['meta', 'wikilinks'])


def mxp_link(text, topic):
    return mxp.send(text, "?%s" % topic, "Get help for %s" % topic)


def _mxp_topic_link(match):
    """
    Regex .sub() callback for replacing a Markdown link with an MXP tag to
    send the help command for the topic.
    """
    return mxp_link(match.group('title'), match.group('link'))


def _mxp_wiki_link(match):
    return mxp_link(match.group('link'), match.group('link'))


def _mxp_heading(match):
    return mxp.closed_tag('b', match.group('text').strip())


def _mxp_bold(match):
    return mxp.bold(match.group('text'))


def _mxp_underline(match):
    return mxp.underline(match.group('text'))


def _mxp_italic(match):
    return mxp.italic(match.group('text'))


class HelpEntry(object):
    id = ""
    filepath = ""
    priority = 0
    title = ""
    names = ()
    meta = {}
    mdText = ""

    lock = locks.all_pass  # Help entries universally viewable by default.

    mud_text_transforms = (
        (re.compile(r"\[(?P<title>.*?)\]\((?P<link>.*?)\)"), _mxp_topic_link),
        (re.compile(r"\[\[(?P<link>.*?)\]\]"), _mxp_wiki_link),
        (re.compile(r"`(.*?)`"), r'{c\1{n'),
        (re.compile(r"^#+\s*(?P<text>.+)$", re.MULTILINE), r"{y\1"),
        (re.compile(r"(\*\*|__)(?P<text>.*?)\1"), _mxp_bold),
        (re.compile(r"(\*|_)(?P<text>.*?)\1"), _mxp_italic)
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

        try:
            self.mdText = '\n'.join(md.lines).strip()
            del md.lines
        except AttributeError:
            self.mdText = "This help file has not yet been written."

        if 'id' in self.meta:
            self.id = str(self.meta['id'][0])
        if 'title' in self.meta:
            self.title = str(self.meta['title'][0])
            self.names[0] = self.title.lower()
        if 'aliases' in self.meta:
            parse = parsers.StringListStaticParser.parse
            self.names[1:] = map(str.lower, parse(self.meta['aliases'][0]))
        if 'lock' in self.meta:
            self.lock = locks.Lock(str(self.meta['lock'][0]))
        if 'priority' in self.meta:
            try:
                self.priority = int(self.meta['priority'][0])
            except ValueError:
                logging.warning("Invalid priority in %s" % filepath)

    def __str__(self):
        return self.title

    def __repr__(self):
        return "<Help Topic '%s'>" % self.title

    def mud_text(self):
        """
        Get text appropriate to output to a MUD session. Take the plain-text
        markdown and run some transformations on it to present a version of the
        text that is MUD-friendly (ANSI codes, MXP, etc).
        """
        text = self.mdText
        for regex, replace in self.mud_text_transforms:
            text = regex.sub(replace, text)
        return text


class HelpManager(object):
    def __init__(self):
        self.entries = {}
        self.name_map = {}
        self.all_names = []

    def load_help_path(self, path, rebuild_name_map=True):
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
        if rebuild_name_map:
            self.rebuild_name_map()
        logging.info("Loaded %d help files from %s" % (count, path))

    def _name_map(self, entries):
        mapping = {}
        for e in entries.itervalues():
            for n in e.names:
                n = n.lower()
                if n in mapping and mapping[n].priority >= e.priority:
                    continue
                mapping[n] = e
        return mapping

    def rebuild_name_map(self):
        self.name_map = self._name_map(self.entries)
        self.all_names = self.name_map.keys()

    def find_topic(self, search, entryFilter=None):
        search = search.lower()
        if entryFilter is None:
            nameMap = self.name_map
            names = self.all_names
        else:
            entries = dict(x for x in self.entries.iteritems()
                           if entryFilter(x[1]))
            nameMap = self._name_map(entries)
            names = nameMap.keys()

        if search in nameMap:
            return nameMap[search]
        matches = [x for x in process.extract(search, names) if x[1] >= 85]
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
