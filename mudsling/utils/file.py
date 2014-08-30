import os
import fnmatch


def scan_path(root, pattern, recursive=True):
    """
    Return a generator of files in the given path matching the file pattern.

    @param root: The root of the directory tree to scan.
    @param pattern: The UNIX filename pattern to match with.
    @param recursive: Whether to search subdirectories or not.

    @return: Generator of filenames.
    """
    iter = os.walk(os.path.abspath(root))
    if not recursive:
        iter = (iter.next(),)
    for path, dirs, files in iter:
        for filename in fnmatch.filter(files, pattern):
            yield os.path.join(path, filename)


def path_parts(path):
    """
    Split path into all parts.
    """
    allparts = []
    while 1:
        parts = os.path.split(path)
        if parts[0] == path:  # sentinel for absolute paths
            allparts.insert(0, parts[0])
            break
        elif parts[1] == path:  # sentinel for relative paths
            allparts.insert(0, parts[1])
            break
        else:
            path = parts[0]
            allparts.insert(0, parts[1])
    return allparts


def sanitize_filename(filename):
    others = frozenset('_-.()')
    return ''.join(x for x in filename if x.isalnum() or x in others)
