import fnmatch

from mudsling.commands import Command
from mudsling.parsers import MatchObject

from mudslingcore.misc import parse_names
import mudslingcore.areas as areas


class AreaListCmd(Command):
    """
    @area-list [<filter>]

    List areas, optionally filtered by a wildcard pattern.
    """
    aliases = ('@area-list', '@areas-list', '@list-areas')
    syntax = '[<glob>]'
    lock = areas.Locks.import_areas

    def run(self, actor, glob):
        loaders = self.game.invoke_hook('area_loaders',
                                        plugin_type='AreaProviderPlugin')
        flat = {}
        for plugin_loaders in loaders.itervalues():
            flat.update(plugin_loaders)
        filtered = fnmatch.filter(flat.keys(), glob) if glob else flat.keys()
        filtered.sort()
        actor.tell('{cFound {y', len(filtered), '{c importable areas:')
        actor.msg('  ' + ('\n  '.join(filtered)))


class AreaExportCmd(Command):
    """
    @area-export <object>

    Export an area to JSON and output the JSON string.
    """
    aliases = ('@area-export', '@export-area')
    syntax = '<exportable>'
    arg_parsers = {
        'exportable': MatchObject(cls=areas.AreaExportable,
                                  search_for='exportable object',
                                  show=True, context=False)
    }
    lock = areas.Locks.export_areas

    def run(self, actor, exportable):
        exported = areas.export_area_to_json(exportable)
        actor.msg(exported)


class AreaImportCmd(Command):
    """
    @area-import <area ID> [called <names>] [into <obj>]

    Import an area and optionally give it an alternate name and aliases.
    """
    aliases = ('@area-import', '@import-area')
    syntax = '<area_id> [\w{called|named|as|=} <names>] [{to|into} <obj>]'
    arg_parsers = {
        'names': parse_names,
        'obj': MatchObject(cls=areas.AreaExportableObject,
                           search_for='area top object', show=True)
    }
    lock = areas.Locks.import_areas

    def run(self, actor, area_id, names, obj):
        loader = areas.get_area_loader(area_id)
        if loader is None:
            raise self._err('%s not found' % area_id)
        try:
            #: :type: areas.AreaExportableBaseObject
            imported = loader.import_area(top=obj)
        except areas.AreaImportFailed as e:
            raise self._err(e.message)
        else:
            if names is not None:
                imported.set_names(names)
            actor.tell('Imported {m', area_id.lower(), '{y -> {c', imported)
