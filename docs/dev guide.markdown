Developer Guide
===============

This document serves as a place to keep notes about writing code for MUDSling.


Keep the Database Picklable
---------------------------

One of the quickest ways to break your game is to try to stash values that are
not picklable. Here is a brief list of things to avoid storing:

* lambdas
* handles (sockets, files, database connections, etc)

If you really need to pickle something that's not readily picklable, you might
consider wrapping it in a class that stores enough data to reconstruct it in
a picklable fashion. The mudsling.storage.Persistent class is handy for doing
things like that.

You could also implement reduction using copy_reg.pickle, which is how MUDSling
enables pickling of instance methods.


Subclass Persistent if You Want to Store It
-------------------------------------------

The mudsling.storage.Persistent class should be in the ancestry of any object
you wish to persist in the database.

Note that any attribute named in _transient_vars in your class or *any of its
parent classes* will **not** be pickled. This is a very handy way to have
volatile storage for stuff you'd rather not store, or cannot store.


Use ObjRefs Instead of Direct References
----------------------------------------

The mudsling.storage.ObjRef class is a rather transparent weak reference proxy
for MUDSling game world objects. It transparently passes attribute and method
calls through to the actual object in the database without requiring you to
have a reference to the actual object.

The biggest change in your coding is that some built-ins might not work as
transparently, such as isinstance -- instead, use ObjRef.isa() or .is_valid().
The only other thing you'll need to keep in mind is when returning or passing
the self variable -- you'll want to usually return or pass self.ref() instead.

For the most part, calls you make to obtain objects will return ObjRef objects.
If you really need a first-class reference to the object, you can call the
._realObject() method on the ObjRef, but this should almost never be needed.

The ObjRef weak reference system is an important part of MUDSling that allows
objects which are deleted to *really* be deleted. Remember that Python will not
garbage collect an object until there are no remaining references to it.
Because of this, the Database wants to be the only thing to maintain an actual
reference to game objects.

This also means that you can have stored ObjRefs that refer to invalid objects.
This is why you have ObjRef.is_valid() -- be sure to use it!


Writing Plugins
---------------

You need:
* A .plugin-info file.
* A subclass of mudsling.extensibility.Plugin.

=== Exposing plugin as a module ===

If there is a __init__.py inside the plugin's directory, then the entire
directory will be imported as a Python package with the name being the lower-
case version of the plugin's directory name. For instance, MUDSlingCore's
__init__.py is loaded as module 'mudslingcore'.

MUDSling imports the file identified as the plugin module in the .plugin-info
file. This file is imported as a module with a name matching its filename. By
default, this name is 'plugin'. This means that multiple plugins loading using
the default filename may overwrite eachother in sys.modules.

Furthermore, if you have a __init__.py and your plugin's module file name
matches that of your plugin directory, then you may overwrite some elements of
your plugin's directory-level module with the plugin module (since their names
collide).

Best practice is to use different names for the plugin directory and the file
containing the plugin class, if you want to use __init__.py.
