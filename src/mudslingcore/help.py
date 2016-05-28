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
from mudsling.utils.string import mxp, ansi, trim_docstring


def load_help_files(game):
    """
    Load help files into a HelpManager.

    :param game: The game object whose plugins to poll for help files.
    :type game: mudsling.core.MUDSling

    :return: A newly-loaded HelpManager instance.
    :rtype: HelpManager
    """
    manager = HelpManager()
    for paths in game.invoke_hook('help_paths').itervalues():
        for path in paths:
            manager.load_help_path(path, rebuild_name_map=False)
    manager.rebuild_name_map()
    return manager


md = markdown.Markdown(extensions=['meta', 'wikilinks'])


def mxp_link(text, topic):
    topic = ansi.strip_ansi_tokens(topic)
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
    priority = 0
    title = ""
    names = ()
    meta = {}
    text = ''
    lock = locks.all_pass  # Help entries universally viewable by default.

    def __init__(self, id, title=None, extra_aliases=(), meta=None, text=''):
        self.id = id
        if title is None:
            title = self.id.replace('_', ' ')
        self.title = title
        self.names = [self.title.lower()]
        self.names.extend(extra_aliases)
        if meta is not None:
            self.meta = dict(meta)
        self.text = text

        if 'id' in self.meta:
            self.id = str(self.meta['id'][0])
        if 'title' in self.meta:
            self.title = str(self.meta['title'][0])
            self.names[0] = self.title.lower()
        if 'aliases' in self.meta:
            p = parsers.StringListStaticParser.parse
            self.names[1:] = map(str.lower, p(str(self.meta['aliases'][0])))
        if 'lock' in self.meta:
            self.lock = locks.Lock(str(self.meta['lock'][0]))
        if 'priority' in self.meta:
            try:
                self.priority = int(self.meta['priority'][0])
            except ValueError:
                logging.warning("Invalid priority in %s" % id)

    def mud_text(self):
        return self.text

    def __str__(self):
        return self.title

    def __repr__(self):
        return "<Help Entry '%s'>" % self.title


class MarkdownHelpEntry(HelpEntry):
    mdText = ""

    mud_text_transforms = (
        (re.compile(r"`(.*?)`"), r'{c\1{n'),
        (re.compile(r"^#+\s*(?P<text>.+)$", re.MULTILINE), r"{y\1"),
        (re.compile(r"(\*\*|__)(?P<text>.*?)\1"), _mxp_bold),
        (re.compile(r"(\*|_)(?P<text>.*?)\1"), _mxp_italic),
        (re.compile(r"\[(?P<title>.*?)\]\((?P<link>.*?)\)"), _mxp_topic_link),
        (re.compile(r"\[\[(?P<link>.*?)\]\]"), _mxp_wiki_link)
    )

    def __init__(self, id, title=None, extra_aliases=(), meta=None, text=''):
        if meta is None:
            meta = {}
        _meta, md_text = self._markdown_parse(text)
        meta.update(_meta)
        super(MarkdownHelpEntry, self).__init__(id, title, extra_aliases, meta,
                                                md_text)

    def _markdown_parse(self, raw_markdown):
        md.reset().convert(raw_markdown)
        try:
            meta = md.Meta
            del md.Meta
        except AttributeError:
            meta = {}
        return meta, '\n'.join(md.lines).strip()

    def mud_text(self):
        """
        Get text appropriate to output to a MUD session. Take the plain-text
        markdown and run some transformations on it to present a version of the
        text that is MUD-friendly (ANSI codes, MXP, etc).
        """
        text = self.text
        for regex, replace in self.mud_text_transforms:
            text = regex.sub(replace, text)
        return text


class MarkdownFileHelpEntry(MarkdownHelpEntry):
    filepath = ""

    def __init__(self, filepath):
        self.filepath = os.path.abspath(filepath)
        filename = os.path.basename(filepath)
        id = filename.rsplit('.', 1)[0]

        with open(filepath, 'r') as f:
            raw_text = f.read()

        super(MarkdownFileHelpEntry, self).__init__(id, text=raw_text)


class CommandHelpEntry(HelpEntry):
    """
    Specialized help entry for command docstrings. Treats first group of un-
    broken lines as the syntax usage.
    """
    def __init__(self, cmd_class):
        """
        :type cmd_class: mudsling.command.Command
        """
        text = []
        building_syntax = True
        for line in trim_docstring(cmd_class.__doc__).splitlines():
            if line == '':
                building_syntax = False
            if building_syntax:
                if not text:
                    text.append('{ySyntax: {c%s' % line)
                else:
                    text.append('        %s' % line)
            else:
                text.append(line)
        super(CommandHelpEntry, self).__init__(cmd_class.name(),
                                               text='\n'.join(text))


class HelpManager(object):
    def __init__(self):
        self.entries = {}
        self.name_map = {}
        self.all_names = []

    def load_help_path(self, path, rebuild_name_map=True):
        count = 0
        for filepath in utils.file.scan_path(path, "*.md", recursive=True):
            entry = MarkdownFileHelpEntry(filepath)
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
