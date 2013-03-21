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
