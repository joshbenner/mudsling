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

Note that any attribute named in _transientVars in your class or *any of its
parent classes* will **not** be pickled. This is a very handy way to have
volatile storage for stuff you'd rather not store, or cannot store.


Use ObjRefs Instead of Direct References
----------------------------------------

The mudsling.storage.ObjRef class is a rather transparent weak reference proxy
for MUDSling game world objects. It transparently passes attribute and method
calls through to the actual object in the database without requiring you to
have a reference to the actual object.

The only real change in your coding is that some built-ins might not work as
transparently, such as isinstance -- instead, use ObjRef.isa() or .isValid().

For the most part, calls you make to obtain objects will return ObjRef objects.
If you really need a first-class reference to the object, you can call the
._realObject() method on the ObjRef, but this should almost never be needed.

The ObjRef weak reference system is an important part of MUDSling that allows
objects which are deleted to *really* be deleted. Remember that Python will not
garbage collect an object until there are no remaining references to it.
Because of this, the Database wants to be the only thing to maintain an actual
reference to game objects.

This also means that you can have stored ObjRefs that refer to invalid objects.
This is why you have ObjRef.isValid() -- be sure to use it!
