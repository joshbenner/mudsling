import os

schemas_path = os.path.join(os.path.dirname(__file__), 'schemas')


def migrations_path(name):
    return os.path.join(schemas_path, name)
