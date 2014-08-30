"""
Object commands.
"""
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

from mudslingcore import misc
import mudslingcore.objsettings

from mudslingcore.commands.admin import ui

can_configure = mudsling.locks.Lock('can_configure()')


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
    @rename <object> to|as <new-names>

    Renames an object to the new name.
    """
    aliases = ('@rename',)
    syntax = "<object> {to|as} <newNames>"
    arg_parsers = {
        'object': NamedObject,
        'newNames': parsers.StringListStaticParser,
    }
    lock = locks.all_pass  # Everyone can use @rename -- access check within.

    def run(self, this, actor, args):
        """
        @type this: mudslingcore.objects.Player
        @type actor: mudslingcore.objects.Player
        @type args: dict
        """
        #: @type: BaseObject
        obj = args['object']
        if not obj.allows(actor, 'rename'):
            actor.tell("{yYou are not allowed to rename {c", obj, "{y.")
            return
        names = args['newNames']
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
        'object': parsers.MatchObject(show=True),
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
    syntax = "<where>"
    lock = 'perm(teleport)'
    arg_parsers = {
        'where': parsers.MatchObject(cls=LocatedObject,
                                     search_for='location', show=True)
    }

    def run(self, this, actor, args):
        """
        @type this: mudslingcore.objects.Player
        @type actor: mudslingcore.objects.Player
        @type args: dict
        """
        if actor.is_possessing and actor.possessing.is_valid(LocatedObject):
            #: @type: mudsling.objects.Object
            obj = actor.possessing
            if not obj.allows(actor, 'move'):
                actor.tell("{yYou are not allowed to move {c", obj, "{y.")
                return
            misc.teleport_object(obj, args['where'])
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
        'what':  parsers.MatchObject(cls=LocatedObject,
                                     search_for='locatable object', show=True),
        'where': parsers.MatchObject(cls=LocatedObject,
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
    cls=mudslingcore.objsettings.ConfigurableObject,
    search_for='configurable object',
    show=True
)


class SetCmd(mudsling.commands.Command):
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
    lock = can_configure

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


class ResetCmd(mudsling.commands.Command):
    """
    @reset <obj>.<setting>

    Resets an object setting to its default.
    """
    aliases = ('@reset',)
    syntax = '<obj> {.} <setting>'
    arg_parsers = {
        'obj': match_configurable_obj
    }
    lock = can_configure

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


class ShowCmd(mudsling.commands.Command):
    """
    @show <obj>[.<setting>]

    Display all settings on an object, or a specific setting.
    """
    aliases = ('@show',)
    syntax = '<obj>[.<setting>]'
    lock = locks.all_pass

    def execute(self):
        # Just to avoid circular imports!
        from mudslingcore.objects import InspectableObject
        self.arg_parsers = {
            'obj': parsers.MatchObject(cls=InspectableObject,
                                       search_for='inspectable object',
                                       show=True, context=False)
        }
        super(ShowCmd, self).execute()

    def before_run(self):
        if not mudslingcore.objsettings.lock_can_configure(
                self.parsed_args['obj'], self.actor):
            raise self._err('Permission denied.')

    def run(self, this, actor, args):
        """
        :type this: mudslingcore.objects.Player
        :type actor: mudslingcore.objects.Player
        :type args: dict
        """
        obj = args['obj']
        if args['setting'] is not None:
            if obj.isa(mudslingcore.objsettings.ConfigurableObject):
                #: :type: mudslingcore.objsettings.ObjSetting
                setting = obj.get_obj_setting(args['setting'])
                val = mudsling.utils.string.escape_ansi_tokens(
                    setting.display_value(obj))
                actor.tell('{g', obj, '{n.{y', args['setting'], ' {x[',
                           self.fmt_type(setting), '] {n= {c', val)
            else:
                raise self._err('Object does not have settings')
        else:
            details = obj.show_details(who=actor).items()
            out = mudsling.utils.string.columnize(
                str(ui.keyval_table(details)).splitlines(), 2,
                width=ui.table_settings['width'])
            if obj.isa(mudslingcore.objsettings.ConfigurableObject):
                out += '\n\n' + ui.h2('Settings') + '\n'
                out += str(self.settings_table(obj))
            actor.tell(ui.report('Showing %s' % actor.name_for(obj), out))

    def settings_table(self, obj):
        if self.parsed_args['setting'] is not None:
            settings = (self.parsed_args['setting'],)
        else:
            settings = sorted(obj.obj_settings().keys(), key=str.lower)
        settings = map(str.lower, settings)
        table = ui.Table(
            [
                ui.Column('Setting', align='l', data_key='name'),
                ui.Column('Type', align='l', cell_formatter=self.fmt_type),
                ui.Column('Value', align='l', cell_formatter=self.fmt_val),
                ui.Column('Default', align='l',
                          cell_formatter=self.fmt_default)
            ]
        )
        all_settings = obj.obj_settings()
        table.add_rows(*(all_settings[s] for s in settings))
        return table

    def fmt_type(self, setting):
        return setting.type.__name__

    def fmt_val(self, setting):
        return setting.display_value(self.parsed_args['obj'])

    def fmt_default(self, setting):
        obj = self.parsed_args['obj']._real_object()
        default = 'Yes' if setting.is_default(obj) else 'No'
        if default and isinstance(getattr(obj.__class__, setting.attr, None),
                                  property):
            return '(alias)'
        return default
