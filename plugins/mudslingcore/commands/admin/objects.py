"""
Object commands.
"""
import inspect

from mudsling.commands import Command
from mudsling.objects import LockableObject, NamedObject, BaseObject
from mudsling.objects import BasePlayer, Object as LocatedObject
from mudsling import registry
from mudsling import parsers
from mudsling import locks
from mudsling import errors

from mudsling import utils
import mudsling.utils.string
import mudsling.utils.modules as mod_utils

from mudslingcore.objects import DescribableObject
from mudslingcore import misc
from mudslingcore.objsettings import ConfigurableObject, lock_can_configure
from mudslingcore.objsettings import SettingEditorSession
from mudslingcore.editor import EditorError
from mudslingcore.rooms import RoomGroup
from mudslingcore.inspectable import InspectableObject

from mudslingcore.commands.admin import ui


class CreateCmd(Command):
    """
    @create <class> called <names>

    Creates a new object of the specified class with the given names.
    """
    aliases = ('@create',)
    lock = 'perm(create objects)'
    syntax = "<class> [{called|named|=} <names>]"

    def run(self, this, actor, args):
        cls = registry.classes.get_class(args['class'])
        if cls is None:
            # noinspection PyBroadException
            try:
                cls = mod_utils.class_from_path(args['class'])
            except:
                cls = None
            if cls is None or not issubclass(cls, BaseObject):
                actor.msg("Unknown class: %s" % args['class'])
                return
        clsName = registry.classes.get_class_name(cls)
        if not actor.superuser and not (issubclass(cls, LockableObject)
                                        and cls.createLock.eval(cls, actor)):
            msg = "{yYou do not have permission to create {c%s{y objects."
            actor.msg(msg % clsName)
            return
        if 'names' in args and args['names']:
            try:
                names = misc.parse_names(args['names'])
            except Exception as e:
                actor.msg('{r' + e.message)
                return
        else:
            names = None

        obj = cls.create(names=names, owner=actor)
        actor.msg("{gCreated new %s: {c%s" % (clsName, obj.nn))

        if obj.isa(LocatedObject):
            if actor.isa(BasePlayer):
                if (actor.possessing is not None
                        and actor.possessing.isa(LocatedObject)):
                    where = actor.possessing
                else:
                    where = None
            elif actor.isa(LocatedObject):
                where = actor
            else:
                where = None

            if where is not None:
                obj.move_to(where)
                actor.msg("{c%s {yplaced in: {m%s" % (obj.nn, where.nn))
            else:
                actor.msg("{c%s {yis {rnowhere{y.")


class RenameCmd(Command):
    """
    @rename <object> to <new-names>

    Renames an object to the new name.
    """
    aliases = ('@rename',)
    syntax = "<obj> {to|as} <names>"
    arg_parsers = {
        'obj': parsers.MatchObject(NamedObject, search_for='named object',
                                   show=True, context=False),
        'names': parsers.StringListStaticParser,
    }
    lock = locks.all_pass  # Everyone can use @rename -- access check within.

    def run(self, actor, obj, names):
        """
        :type actor: mudslingcore.objects.Player
        :type obj: NamedObject
        :type names: list of str
        """
        if not obj.allows(actor, 'rename'):
            actor.tell("{yYou are not allowed to rename {c", obj, "{y.")
            return
        oldNames = obj.set_names(names)
        msg = "{{gName of {{c#{id}{{g changed to '{{m{name}{{g'"
        keys = {'id': obj.obj_id, 'name': obj.name}
        if len(names) > 1:
            msg += " with aliases: {aliases}"
            aliases = ["{y%s{g" % a for a in obj.aliases]
            keys['aliases'] = utils.string.english_list(aliases)
        actor.msg(str(msg.format(**keys)))
        actor.msg("(previous names: {M%s{n)" % ', '.join(oldNames))


class ChangeClassCmd(Command):
    """
    @chclass <object> to <class>
    """
    aliases = ('@chclass', '@change-class', '@chparent')
    syntax = '<object> to <class>'
    arg_parsers = {
        'object': parsers.MatchObject(show=True, context=False),
        'class': parsers.ObjClassStaticParser
    }
    lock = 'perm(create objects)'

    def run(self, this, actor, args):
        """
        :type this: mudslingcore.objects.Player
        :type actor: mudslingcore.objects.Player
        :type args: dict
        """
        cls = args['class']
        clsName = registry.classes.get_class_name(cls)
        if not actor.superuser and not (issubclass(cls, LockableObject)
                                        and cls.createLock.eval(cls, actor)):
            msg = "{yYou do not have permission to create {c%s{y objects."
            raise self._err(msg % clsName)
        obj = args['object']
        if obj._real_object().__class__ == cls:
            raise self._err("%s is already a %s." % (obj, clsName))
        try:
            self.game.db.change_class(args['object'], cls)
        except Exception as e:
            raise self._err(e.message)
        else:
            actor.tell('{c', args['object'], '{g is now a {c', clsName, '{g.')


class DeleteCmd(Command):
    """
    @delete <object>

    Deletes the specified object.
    """
    aliases = ('@delete',)
    lock = 'perm(delete objects)'
    syntax = "<object>"

    def run(self, this, actor, args):
        """
        @type this: mudslingcore.objects.Player
        @type actor: mudslingcore.objects.Player
        @type args: dict
        """
        # err=True means we'll either exit with error or have single-element
        # list containing the match. Use .ref()... just in case.
        obj = actor.match_object(args['object'], err=True)[0].ref()

        if obj == actor.ref():
            actor.msg("{rYou may not delete yourself.")
            return

        if obj.isa(BaseObject) and not obj.allows(actor, 'delete'):
            actor.tell("{yYou are not allowed to delete {c", obj, "{y.")
            return

        def _do_delete():
            msg = "{c%s {yhas been {rdeleted{y." % obj.nn
            obj.delete()
            actor.msg(msg)

        def _abort_delete():
            actor.msg("{yDelete {gABORTED{y.")

        p = ("{yYou are about to {rDELETE {c%s{y.\n"
             "{yAre you sure you want to {rDELETE {ythis object?")
        actor.player.prompt_yes_no(p % obj.nn,
                                   yes_callback=_do_delete,
                                   no_callback=_abort_delete)


class ClassesCmd(Command):
    """
    @classes

    Displays a list of object classes available.
    """
    aliases = ('@classes',)
    lock = 'perm(create objects)'

    def run(self, this, actor, args):
        out = []
        for name, cls in registry.classes.classes.iteritems():
            pyname = '%s.%s' % (cls.__module__, cls.__name__)
            if name == pyname:
                continue  # Skip python name aliases.
            desc = self._class_desc(cls)
            out.append("{c%s {n[{m%s{n]\n%s" % (name, pyname, desc))
        actor.msg('\n\n'.join(sorted(out)))

    def _class_desc(self, cls):
        """
        Return just the syntax portion of the command class's docstring.

        @return: Syntax string
        @rtype: str
        """
        trimmed = utils.string.trim_docstring(cls.__doc__)
        desc = []
        for line in trimmed.splitlines():
            if line == "":
                break
            desc.append('  ' + line)
        return '\n'.join(desc)


class GoCmd(Command):
    """
    @go <location>

    Teleport one's self to the indicated location.
    """
    aliases = ('@go',)
    syntax = "[<where>]"
    lock = 'perm(teleport)'
    arg_parsers = {
        'where': parsers.MatchObject(cls=LocatedObject, context=False,
                                     search_for='location', show=True)
    }

    def run(self, actor, where):
        """
        :type actor: mudslingcore.objects.Player
        :type where: mudsling.objects.Object
        """
        if actor.is_possessing and actor.possessing.is_valid(LocatedObject):
            #: :type: mudsling.objects.Object
            obj = actor.possessing
            plugins = self.game.plugins.enabled_plugins()
            if where is None and 'myobjs' in plugins:
                from myobjs import MyObjCharacter
                #: :type: MyObjCharacter
                char = obj
                if char.isa(MyObjCharacter) and char.has_myobj('place'):
                    place = char.get_myobj('place')
                    if self.game.db.is_valid(place, LocatedObject):
                        where = place
            if where is None:
                actor.msg(self.syntax_help())
                return
            if not obj.allows(actor, 'move'):
                actor.tell("{yYou are not allowed to move {c", obj, "{y.")
                return
            misc.teleport_object(obj, where)
        else:
            m = "You are not attached to a valid object with location."
            raise self._err(m)


class MoveCmd(Command):
    """
    @move <object> to <location>

    Moves the specified object to the specified location.
    """
    aliases = ('@move', '@tel', '@teleport')
    syntax = "<what> to <where>"
    lock = "perm(teleport)"
    arg_parsers = {
        'what':  parsers.MatchObject(cls=LocatedObject, context=False,
                                     search_for='locatable object', show=True),
        'where': parsers.MatchObject(cls=LocatedObject, context=False,
                                     search_for='location', show=True),
    }

    def run(self, this, actor, args):
        """
        :type this: mudslingcore.objects.Player
        :type actor: mudslingcore.objects.Player
        :type args: dict
        """
        obj, where = (args['what'], args['where'])
        if not obj.allows(actor, 'move'):
            actor.tell("{yYou are not allowed to move {c", obj, "{y.")
            return
        misc.teleport_object(obj, where)
        msg_key = 'teleport' if obj.location == where else 'teleport_failed'
        actor.direct_message(msg_key, recipients=(actor, obj),
                             actor=actor, obj=obj, where=where)


match_configurable_obj = parsers.MatchObject(
    cls=ConfigurableObject,
    search_for='configurable object',
    show=True,
    context=False
)


class SettingsCommand(mudsling.commands.Command):
    """
    Special command type which checks access after instantiation based on a
    specially-named parameter. Actor must be able to configure the 'obj'
    parameter.
    """
    abstract = True
    lock = locks.all_pass

    def before_run(self):
        obj = self.parsed_args['obj']
        if not lock_can_configure(obj, self.actor):
            n = self.actor.name_for(obj)
            raise errors.AccessDenied('Access denied to %s configuration.' % n)


class SetCmd(SettingsCommand):
    """
    @set <obj>.<setting>=<value>

    Set a configuration option on an object.
    """
    aliases = ('@set',)
    syntax = (
        '<obj> {.} <setting> {=} <value>',
        '<obj>.<setting> to <value>'
    )
    arg_parsers = {
        'obj': match_configurable_obj
    }

    def run(self, this, actor, args):
        """
        :type this: mudslingcore.objects.Player
        :type actor: mudslingcore.objects.Player
        :type args: dict
        """
        #: :type: mudslingcore.objsettings.ConfigurableObject
        obj = args['obj']
        try:
            previous = obj.get_obj_setting(args['setting']).display_value(obj)
            obj.set_obj_setting(args['setting'], args['value'])
        except errors.ObjSettingError as e:
            raise self._err(e.message)
        else:
            new = obj.get_obj_setting(args['setting']).display_value(obj)
            actor.tell(obj, '.', args['setting'], ' set to %s' % new,
                       ' (previous value: %s)' % previous)


class ResetCmd(SettingsCommand):
    """
    @reset <obj>.<setting>

    Resets an object setting to its default.
    """
    aliases = ('@reset',)
    syntax = '<obj> {.} <setting>'
    arg_parsers = {
        'obj': match_configurable_obj
    }

    def run(self, this, actor, args):
        """
        :type this: mudslingcore.objects.Player
        :type actor: mudslingcore.objects.Player
        :type args: dict
        """
        #: :type: mudslingcore.objsettings.ConfigurableObject
        obj = args['obj']
        try:
            obj.reset_obj_setting(args['setting'])
        except errors.ObjSettingError as e:
            raise self._err(e.message)
        else:
            actor.tell(obj, '.', args['setting'],
                       ' reset to default (%r).'
                       % obj.get_obj_setting_value(args['setting']))


class ShowCmd(SettingsCommand):
    """
    @show <obj>[.<setting>]

    Display all settings on an object, or a specific setting.
    """
    aliases = ('@show',)
    syntax = '<obj>[.<setting>]'

    def execute(self):
        # Just to avoid circular imports!
        self.arg_parsers = {
            'obj': parsers.MatchObject(cls=InspectableObject,
                                       search_for='inspectable object',
                                       show=True, context=False)
        }
        super(ShowCmd, self).execute()

    def before_run(self):
        try:
            super(ShowCmd, self).before_run()
        except errors.AccessDenied:
            if not self.actor.has_perm('inspect objects'):
                raise

    def run(self, this, actor, args):
        """
        :type this: mudslingcore.objects.Player
        :type actor: mudslingcore.objects.Player
        :type args: dict
        """
        obj = args['obj']
        if args['setting'] is not None:
            if obj.isa(ConfigurableObject):
                #: :type: mudslingcore.objsettings.ObjSetting
                setting = obj.get_obj_setting(args['setting'])
                val = mudsling.utils.string.escape_ansi_tokens(
                    setting.display_value(obj))
                actor.tell('{g', obj, '{n.{y', args['setting'], ' {x[',
                           obj._fmt_type(setting), '] {n= {c', val)
            else:
                raise self._err('Object does not have settings')
        else:
            body = obj.inspectable_output(who=actor)
            actor.tell(ui.report('Showing %s' % actor.name_for(obj), body))


class EditCmd(SettingsCommand):
    """
    @edit[/paste] <object>.<setting>

    Open the line editor for a string setting. If /paste switch is used, then
    prompt for a paste.
    """
    aliases = ('@edit',)
    syntax = '<obj> {.} <setting>'
    arg_parsers = {'obj': match_configurable_obj}
    switch_defaults = {'paste': False}

    def run(self, actor, obj, setting, switches):
        """
        :type actor: mudslingcore.objects.Player
        :type obj: mudslingcore.objsettings.ConfigurableObject
        :type setting: str
        :type switches: dict of (str, bool)
        """
        if switches['paste']:
            self._paste(actor, obj, setting)
        else:
            self._edit(actor, obj, setting)

    def _edit(self, actor, obj, setting):
        """
        :type actor: mudslingcore.objects.Player
        :type obj: mudslingcore.objsettings.ConfigurableObject
        :type setting: str
        """
        objsetting = obj.get_obj_setting(setting)
        if objsetting.type != str:
            raise self._err('You can only @edit strings!')
        session = SettingEditorSession(actor, obj, setting)
        try:
            actor.register_editor_session(session, activate=True)
        except EditorError as e:
            raise self._err(e.message)
        actor.tell('{gYou are now editing ', session.description, '.')

    def _paste(self, actor, obj, setting):
        """
        :type actor: mudslingcore.objects.Player
        :type obj: mudslingcore.objsettings.ConfigurableObject
        :type setting: str
        """
        def _set_setting(lines):
            obj.set_obj_setting(setting, '\n'.join(lines))
            self._notify_set(actor, obj, setting)
        try:
            actor.read_lines(callback=_set_setting)
        except errors.PlayerNotConnected:
            raise self._err('Cannot paste with a disconnect player.')

    def _notify_set(self, actor, obj, setting):
        actor.tell(obj, '.', setting, ' has been set.')


class DescribeCmd(EditCmd):
    """
    @describe[/paste] <object> [as <description>]

    Describe a describable object.
    """
    aliases = ('@describe', '@desc')
    syntax = '<obj> [as <text>]'
    arg_parsers = {
        'obj': parsers.MatchObject(
            cls=DescribableObject,
            search_for='describable object',
            show=True,
            context=False
        )
    }
    switch_defaults = {'paste': False}

    # noinspection PyMethodOverriding
    def run(self, actor, obj, switches, text=None):
        """
        :type actor: mudslingcore.objects.Player
        :type obj: mudslingcore.objects.DescribableObject
        :type switches: dict of (str, bool)
        :type text: str
        """
        if switches['paste']:
            self._paste(actor, obj, 'desc')
        elif text is not None:
            obj.set_obj_setting('desc', text)
            self._notify_set(actor, obj, 'desc')
        else:
            self._edit(actor, obj, 'desc')

    def _notify_set(self, actor, obj, setting):
        actor.tell(obj, ' description set.')


class SetGlobalCmd(mudsling.commands.Command):
    """
    @set-global[/obj] <name>=<value>

    Evaluate <value> as Python code (unless /obj switch is used, then it matches
    an object) and store the result in the specified Global Variable.
    """
    aliases = ('@set-global',)
    syntax = '<name> {=} <value>'
    lock = 'perm(eval code) and perm(use global vars)'
    switch_defaults = {'obj': False}

    def execute(self):
        switches = self.parse_args(self.parse_switches(self.switchstr),
                                   self.switch_parsers)
        if 'obj' in switches:
            self.arg_parsers = {'value': parsers.MatchObject(context=False)}
        return super(SetGlobalCmd, self).execute()

    def run(self, actor, name, value):
        """
        :type actor: mudslingcore.objects.Player
        :type name: str
        :type value: BaseObject or str
        """
        from mudslingcore.globalvars import set_var, get_var
        name = name.lower()
        if isinstance(value, str):
            value = self._eval(actor, self.argstr.partition('=')[2])
        previous = get_var(name)
        set_var(name, value)
        actor.tell('Global {y$', name, '{n set to: {c', value,
                   '{n (previously: {m', previous, '{n)')

    def _eval(self, actor, code):
        """
        :type actor: mudslingcore.objects.Player
        :type code: str
        """
        import sys
        from mudsling import registry
        from mudsling.config import config
        from mudsling.objects import Object
        from mudslingcore.commands.admin.system import EvalCmd

        #: :type: mudsling.objects.Object
        char = actor.possessing
        vars = {
            'game': self.game,
            'db': self.game.db,
            'ref': self.game.db.get_ref,
            'registry': registry,
            'config': config,
            'player': actor,
            'me': char,
            'here': (char.location if self.game.db.is_valid(char, Object)
                     else None),
            'utils': mudsling.utils,
        }
        vars.update(sys.modules)

        # Support MOO-style objrefs in eval code.
        code = EvalCmd.objref.sub(r'ref(\1)', code)
        code = EvalCmd.objref_escape_fix.sub(r'#\1', code)

        try:
            return eval(code, {}, vars)
        except Exception as e:
            import logging
            logging.exception('Failed: %s', self.raw)
            raise self._err('{r%s: %s' % (e.__class__.__name__, e.message))


class GlobalsCmd(mudsling.commands.Command):
    """
    @globals

    Display a list of globals and their values.
    """
    aliases = ('@globals',)
    lock = 'perm(use global vars)'

    def run(self, actor):
        """
        :type actor: mudslingcore.objects.Player
        """
        from mudslingcore.globalvars import all_global_vars
        ui = actor.get_ui()
        c = ui.Column

        t = ui.Table([
            c('Name', align='l', cell_formatter=self._format_name),
            c('Type', align='l', cell_formatter=self._format_type),
            c('Value', align='l', cell_formatter=self._format_value)
        ])
        for name, value in all_global_vars().iteritems():
            t.add_row((name, value, value))
        actor.msg(ui.report('Globals', t))

    def _class_name(self, cls):
        out = cls.__module__
        if out == '__builtin__':
            out = ''
        else:
            out += '.'
        out += cls.__name__
        return out

    def _format_name(self, name):
        return '$%s' % name

    def _format_type(self, value):
        if inspect.isclass(value):
            return 'class'
        if self.game.db.is_valid(value, cls=BaseObject):
            return value.python_class_name()
        return self._class_name(type(value))

    def _format_value(self, value):
        if inspect.isclass(value):
            return self._class_name(value)
        if self.game.db.is_valid(value, cls=BaseObject):
            return self.actor.name_for(value)
        return repr(value)


class FindPlaceCmd(mudsling.commands.Command):
    """
    @find-place <name> in <group>

    Find a room within the hierarchy of a room group tree. If you have @myobjs,
    a single result will be saved to your %place myobj variable.
    """
    aliases = ('@find-place',)
    syntax = '<search> {{in|on}} <group>'
    arg_parsers = {
        'group': parsers.MatchObject(cls=RoomGroup, search_for='room group',
                                     show=True, context=False)
    }
    lock = 'perm(teleport)'

    def run(self, actor, search, group):
        """
        :type actor: mudslingcore.objects.Player
        :type search: str
        :type group: mudslingcore.rooms.RoomGroup
        """
        matches = actor._match(search, list(group.all_rooms))
        if not matches:
            p = self.args['optset1'].lower()
            actor.tell('{yNo places found matching "{m', search, '{y" ', p,
                       ' {c', group, '{y.')
            return
        plugins = self.game.plugins.enabled_plugins()
        if len(matches) == 1 and 'myobjs' in plugins:
            from myobjs import MyObjCharacter
            #: :type: myobjs.MyObjCharacter
            char = actor.possessing
            if char.isa(MyObjCharacter):
                char.set_myobj('place', matches[0])
                actor.tell('{mSaved {c', matches[0], '{m to {y%place {mmyobj.')
        out = '{cFound Places{y:\n'
        out += '\n'.join(' {y* {g%s' % actor.name_for(m) for m in matches)
        actor.msg(out)


class LocationsCmd(Command):
    """
    @locations [<object>]

    Print out the nested location tree of the object specified. Defaults to
    self.
    """
    aliases = ('@locations', '@locs')
    syntax = '[<obj>]'
    arg_parsers = {'obj': parsers.MatchObject(cls=LocatedObject, show=True,
                                              search_for='object',
                                              context=False)}
    lock = locks.all_pass

    def run(self, actor, obj):
        """
        :type actor: mudslingcore.objects.Player
        :type obj: mudsling.objects.Object
        """
        if (obj is None and actor.is_possessing
                and actor.possessing.isa(LocatedObject)):
            #: :type: mudsling.objects.Object
            obj = actor.possessing
        if not obj.allows(actor, 'locate'):
            raise self._err('{rYou are not permitted to locate that.')
        locs = ['{g%s' % actor.name_for(obj)]
        locs.extend('{y%s' % actor.name_for(l) for l in obj.locations())
        actor.msg(' {m/ '.join(locs))
