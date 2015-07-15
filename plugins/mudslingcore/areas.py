import os
import uuid
import json
from collections import OrderedDict

import mudsling
import mudsling.errors as errors
import mudsling.objects
import mudsling.utils.modules as mod_utils
from mudsling.messages import Messages
from mudsling.storage import ObjRef
from mudsling.utils.json import json_decode_dict
from mudsling.extensibility import Plugin
from mudsling.locks import Lock


class Locks:
    """Namespaced container for convenience locks."""
    import_areas = Lock('perm(import areas)')
    export_areas = Lock('perm(export areas)')


class AreaImportFailed(errors.Error):
    pass


def export_area_to_json(area):
    """
    Exports an area object to JSON.

    :param area: The area to export.
    :type area: AreaExportable

    :return: JSON as string.
    :rtype: str
    """
    data = area.area_export(sandbox={})
    return json.dumps(data, indent=2)


def import_area_from_json(text):
    hook = lambda d: json_decode_dict(d, dict_cls=OrderedDict)
    data = json.JSONDecoder(object_pairs_hook=hook).decode(text)
    if not isinstance(data, dict):
        raise AreaImportFailed("Imported JSON is not an object.")
    sandbox = {}
    area = import_area_object(data, sandbox)
    process_weak_refs(sandbox)
    return area


def process_weak_refs(sandbox):
    for obj, attributes in sandbox.get('weakrefs', {}).iteritems():
        for attr, ref_id in attributes.iteritems():
            try:
                setattr(obj, attr, sandbox['objmap'][ref_id])
            except (AttributeError, KeyError) as e:
                raise AreaImportFailed(e.message)


def import_area_object(data, sandbox):
    """
    Import an area data structure. Main entry point.

    :param data: The area data to import.
    :type data: dict
    """
    try:
        cls = mod_utils.class_from_path(data['class'])
    except errors.Error as e:
        raise AreaImportFailed(e.message)
    except KeyError:
        raise AreaImportFailed('Invalid area file: missing class')
    if 'id' in data:
        external_id = data['id']
        if 'objmap' not in sandbox:
            sandbox['objmap'] = {}
        objmap = sandbox['objmap']
        if external_id in objmap:
            return objmap[external_id]
    obj = cls()
    obj.area_import(data, sandbox)
    obj = obj.ref() if isinstance(obj, AreaExportableBaseObject) else obj
    if 'id' in data:
        sandbox['objmap'][data['id']] = obj
    return obj


def import_weak_ref(obj, attr, ref_id, sandbox):
    if 'weakrefs' not in sandbox:
        sandbox['weakrefs'] = {}
    if obj not in sandbox['weakrefs']:
        sandbox['weakrefs'][obj] = {}
    sandbox['weakrefs'][obj][attr] = ref_id


def export_object(obj, sandbox):
    """
    Convenience function ton export an exportable value, accounting for
    game-world objects.
    """
    if isinstance(obj, ObjRef):
        obj = obj._real_object()
    if isinstance(obj, AreaExportable) and obj.area_exportable:
        return obj.area_export(sandbox)
    return None


def export_object_list(obj_list, sandbox):
    return filter(None, (export_object(o, sandbox) for o in obj_list))


def export_weak_ref(obj):
    """
    Export only an object reference for an AreaExportableBaseObject.
    """
    if isinstance(obj, ObjRef):
        obj = obj._real_object()
    if isinstance(obj, AreaExportableBaseObject):
        return obj.area_export_id
    return None


class AreaExportable(object):
    """
    An object that can be exported to an Area file.

    Generic export functions are not provided, since area file format is
    intended to be a very purpose-specific format, not a generic serialization.
    By adhering to these, we can keep the format simple, and the files can be
    read and edited by humans.
    """

    area_exportable = True

    def area_export(self, sandbox):
        """
        Produce a JSON-encodable data structure that represents this object in
        a generic fashion.

        The structure exported here must be readable by area_import.

        Default implementation does nothing but export class identifier.

        :param sandbox: A state container for sharing information throughout
            the object tree.
        :type sandbox: dict

        :rtype: dict
        """
        return OrderedDict({
            'class': "%s.%s" % (self.__class__.__module__,
                                self.__class__.__name__)
        })

    def area_import(self, data, sandbox):
        """
        Given a data structure decoded from JSON, generate an object tree.

        Default implementation does nothing.
        """
        pass


class AreaExportableBaseObject(AreaExportable, mudsling.objects.BaseObject):
    """
    An exportable MUDSling object.
    """
    _area_export_id = None
    area_import_id = None

    @property
    def area_export_id(self):
        if self._area_export_id is None:
            self._area_export_id = str(uuid.uuid4())
        return self._area_export_id

    @area_export_id.setter
    def area_export_id(self, val):
        # Mostly to support old DBs that are pre-property.
        self._area_export_id = val

    def area_export(self, sandbox):
        export = super(AreaExportableBaseObject, self).area_export(sandbox)
        export['id'] = self.area_export_id
        if 'objmap' not in sandbox:
            sandbox['objmap'] = {}
        sandbox['objmap'][self.area_export_id] = self.ref()
        if '_names' in self.__dict__:
            export['name'] = self.name
            if len(self._names) > 1:
                export['aliases'] = self.aliases
        if 'messages' in self.__dict__:
            export['messages'] = self.messages.messages
        return export

    def area_import(self, data, sandbox):
        super(AreaExportableBaseObject, self).area_import(data, sandbox)
        if 'id' in data:
            self.area_import_id = data['id']
        mudsling.game.db.register_object(self)
        if 'objmap' not in sandbox:
            sandbox['objmap'] = {}
        sandbox['objmap'][self.area_import_id] = self.ref()
        if 'name' in data:
            self.set_name(data['name'])
        if 'aliases' in data:
            self.set_aliases(data['aliases'])
        if 'messages' in data:
            self.messages = Messages(messages=data['messages'])


class AreaExportableObject(AreaExportableBaseObject, mudsling.objects.Object):
    """
    A location-aware object that knows how to be exported as part of an area.

    This is where an object tree begins to emerge, since this class will also
    export objects that it contains. Areas assume that they will be working
    with children of this class.
    """
    def area_export(self, sandbox):
        export = super(AreaExportableObject, self).area_export(sandbox)
        if len(self._contents):
            export['contents'] = export_object_list(self._contents, sandbox)
        return export

    def area_import(self, data, sandbox):
        super(AreaExportableObject, self).area_import(data, sandbox)
        for contained in data.get('contents', []):
            obj = import_area_object(contained, sandbox)
            obj.move_to(self)


class AreaLoader(object):
    """
    Object to represent information about how to load an area. Instances are
    gathered when looking for an area to import.

    This class is abstract.
    """
    __slots__ = ('area_id',)

    def __init__(self, area_id):
        self.area_id = area_id

    def import_area(self):
        raise NotImplementedError()


class InvalidAreaJSONFile(errors.Error):
    pass


class AreaJSONLoader(AreaLoader):
    """
    An area loader for areas stored as JSON files.
    """
    __slots__ = ('filepath',)

    def __init__(self, filepath, id_prefix=''):
        if not os.path.exists(filepath) or not os.path.isfile(filepath):
            raise InvalidAreaJSONFile('Area JSON files must be valid files.')
        self.filepath = os.path.realpath(filepath)
        filename = os.path.basename(filepath)
        area_id = os.path.splitext(filename)[0]
        super(AreaJSONLoader, self).__init__(id_prefix + area_id)

    def import_area(self):
        #json_text = None
        with open(self.filepath, 'r') as f:
            json_text = f.read()
        if len(json_text):
            return import_area_from_json(json_text)
        else:
            raise InvalidAreaJSONFile('No JSON loaded from %s' % self.filepath)


class AreaProviderPlugin(Plugin):
    """
    A MUDSling plugin that provides areas.

    Default implementation provides areas via files stored in the plugin.
    """

    @property
    def area_files_path(self):
        return os.path.join(self.info.path, 'areas')

    def area_loaders(self):
        """
        Plugin hook for getting a list of area loaders.

        Default implementation looks for JSON area files in the area_files_path
        to encapsulate as AreaJSONLoader instances.

        :rtype: dict of (str, AreaLoader)
        """
        loaders = {}
        id_prefix = self.info.machine_name + '.'
        for dirname, dirnames, files in os.walk(self.area_files_path):
            for file in [f for f in files if f.endswith('.json')]:
                filepath = os.path.join(dirname, file)
                loader = AreaJSONLoader(filepath, id_prefix=id_prefix)
                loaders[loader.area_id] = loader
        return loaders
