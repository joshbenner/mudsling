import re
from mudsling.objects import literal_parsers
from mudsling.errors import Error


#: :type: mudsling.storage.Database
db = None

global_re = re.compile(
    r"^\$(?:(?P<prefix>[a-zA-Z_][a-zA-Z0-9_]+)\.)?(?P<name>.+)$")


class GlobalVarsNoDatabase(Error):
    pass


def _init_global_vars():
    if db is not None:
        if not db.has_setting('global_vars'):
            db.set_setting('global_vars', {})
        return db.get_setting('global_vars')
    raise GlobalVarsNoDatabase()


def get_var(name, default=None):
    global_vars = _init_global_vars()
    return global_vars.get(name, default)


def set_var(name, value):
    global_vars = _init_global_vars()
    global_vars[name] = value


def has_var(name):
    global_vars = _init_global_vars()
    return name in global_vars


# noinspection PyUnusedLocal
def handle_global_var(requestor, name):
    if has_var(name):
        return [get_var(name)]
    else:
        return []


global_handlers = {
    None: handle_global_var
}


def parse_global_literal(searcher, search):
    """
    Parse '$<whatever>' into an object.
    """
    m = global_re.match(search)
    if m is None:
        return []
    else:
        prefix = m.group('prefix')
        name = m.group('name')
        if prefix in global_handlers:
            return global_handlers[prefix](searcher, name)
        else:
            return []


literal_parsers['$'] = parse_global_literal
