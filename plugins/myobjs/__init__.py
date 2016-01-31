import abc
from collections import OrderedDict

from mudsling.commands import Command
from mudsling.locks import Lock
from mudsling.objects import BaseCharacter, literal_parsers
from mudsling.parsers import MatchObject

from mudslingcore.ui import ClassicUI

use_myobjs = Lock('has_perm(use myobjs)')
ui = ClassicUI()


def parse_myobj_literal(searcher, search):
    """
    Parse '%<whatever>' into an object.
    """
    if searcher.isa(MyObjCharacter):
        key = search.lower().lstrip('%')
        obj = searcher.get_myobj(key)
        if obj is not None:
            return [obj]
    return []

literal_parsers['%'] = parse_myobj_literal


class MyObjCommand(Command):
    __metaclass__ = abc.ABCMeta

    #: :type: MyObjCharacter
    actor = None

    def before_run(self):
        self.actor.init_myobjs()


class MyObjsCmd(MyObjCommand):
    """
    @myobjs

    List your myobjs registry.
    """
    aliases = ('@myobjs',)
    lock = use_myobjs

    def run(self, actor):
        """
        :type actor: MyObjCharacter
        """
        c = ui.Column
        t = ui.Table([
            c('Name', align='l'),
            c('Object', align='l')
        ])
        for k, v in actor.myobjs.iteritems():
            t.add_row(['%{}'.format(k), actor.name_for(v)])
        actor.msg(ui.report('My Object Shortcuts', t))


class MyObjSetCmd(MyObjCommand):
    """
    @myobj <key>=[<object>]

    Set the value for a personal object shortcut.
    """
    aliases = ('@myobj',)
    syntax = '<key>=[<object>]'
    arg_parsers = {'object': MatchObject(show=True, context=False)}
    lock = use_myobjs

    def run(self, actor, key, object):
        """
        :type actor: MyObjCharacter
        """
        key = key.lower().lstrip('%')
        previous = actor.set_myobj(key, object)
        actor.tell('Previous value of {y%', key, '{n: ', previous)
        actor.tell('New setting: {y%', key, '{n = {c', object)


class MyObjCharacter(BaseCharacter):
    myobjs = {}
    private_commands = [MyObjsCmd, MyObjSetCmd]

    def init_myobjs(self):
        if 'myobjs' not in self.__dict__:
            self.myobjs = OrderedDict()

    def has_myobj(self, key):
        return key.lower() in self.myobjs

    def get_myobj(self, key):
        return self.myobjs.get(key.lower(), None)

    def set_myobj(self, key, value):
        key = key.lower()
        previous = self.get_myobj(key)
        if value is None:
            del self.myobjs[key]
        else:
            self.myobjs[key] = value
        return previous
