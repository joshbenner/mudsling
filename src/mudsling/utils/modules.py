"""
Utilities for dealing with Python modules.

Items adapted from Evennia are done so under the modified BSD License:

BSD license
===========

Copyright (c) 2012-, Griatch (griatch <AT> gmail <DOT> com), Gregory Taylor
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are
met:

- Redistributions of source code must retain the above copyright
notice, this list of conditions and the following disclaimer.
- Redistributions in binary form must reproduce the above copyright
notice, this list of conditions and the following disclaimer in the
documentation and/or other materials provided with the distribution.
- Neither the name of the Copyright Holders nor the names of its
contributors may be used to endorse or promote products derived from
this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND
CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED
WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE
GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR
BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT
OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
POSSIBILITY OF SUCH DAMAGE.
"""
import traceback
import logging
import types
import os
import re
import imp
import random
import inspect


def make_iter(obj):
    """
    Adapted from Evennia.
    Makes sure that the object is always iterable.
    """
    return not hasattr(obj, '__iter__') and [obj] or obj


def mod_import(module):
    """
    A generic Python module loader, adapted from Evennia.

    Args:
        module - this can be either a Python path (dot-notation), an absolute
                 path (e.g. /home/eve/evennia/src/objects.models.py) or an
                 already import module object (e.g. models)
    Returns:
        an imported module. If the input argument was already a model, this is
        returned as-is, otherwise the path is parsed and imported.
    Error:
        returns None. The error is also logged.
    """

    def log_trace(errmsg=None):
        msg = (errmsg + "\n") or ""
        tracestring = traceback.format_exc()
        if tracestring:
            msg += tracestring
        logging.error(msg)

    if not module:
        return None

    if isinstance(module, types.ModuleType):
        # if this is already a module, we are done
        mod = module
    else:
        # first try to import as a python path
        try:
            mod = __import__(module, fromlist=["None"])
        except ImportError, ex:
            # Check just where the ImportError happened (it could have been an
            # erroneous import inside the module as well). This is the trivial
            # way to do it ...
            if str(ex) != "Import by filename is not supported.":
                raise

            # error in this module. Try absolute path import instead

            if not os.path.isabs(module):
                module = os.path.abspath(module)
            path, filename = module.rsplit(os.path.sep, 1)
            modname = re.sub(r"\.py$", "", filename)

            try:
                result = imp.find_module(modname, [path])
            except ImportError:
                log_trace(
                    "Could not find module '%s' (%s.py) at path '%s'"
                    % (modname, modname, path))
                return
            try:
                mod = imp.load_module(modname, *result)
            except ImportError:
                log_trace(
                    "Could not find or import module %s at path '%s'"
                    % (modname, path))
                mod = None
                # we have to close the file handle manually
            if result[0] is not None:
                result[0].close()
    return mod


def variable_from_module(module, variable=None, default=None):
    """
    Adapted from Evennia.

    Retrieve a variable or list of variables from a module. The variable(s)
    must be defined globally in the module. If no variable is given (or a list
    entry is None), a random variable is extracted from the module.

    If module cannot be imported or given variable not found, default
    is returned.

    Args:
      module (string or module)- python path, absolute path or a module
      variable (string or iterable) - single variable name or iterable of
      variable names to extract default (string) - default value to use if a
      variable fails to be extracted.
    Returns:
      a single value or a list of values depending on the type of 'variable'
      argument. Errors in lists are replaced by the 'default' argument.
    """

    if not module:
        return default
    mod = mod_import(module)

    result = []
    for var in make_iter(variable):
        if var:
            # try to pick a named variable
            result.append(mod.__dict__.get(var, default))
        else:
            # random selection
            mvars = [val for key, val in mod.__dict__.items()
                     if not (key.startswith("_") or inspect.ismodule(val))]
            result.append((mvars and random.choice(mvars)) or default)
    if len(result) == 1:
        return result[0]
    return result


def class_from_path(class_path):
    """
    Given a python dot-notation class path, load the module and return a ref
    to the class object.

    Raises exception if it cannot load the class.

    @param class_path: Dot-notation python path to class.

    @rtype: type
    """
    try:
        module_path, class_name = class_path.rsplit('.', 1)
    except ValueError:
        raise Exception("Invalid class path: %s" % class_path)

    classObj = variable_from_module(module_path, class_name)
    if inspect.isclass(classObj):
        return classObj

    raise Exception("Unable to load class %s" % class_path)
