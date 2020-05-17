.. wirerope documentation master file, created by
   sphinx-quickstart on Mon May 18 02:46:57 2020.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

wirerope - the way to handle bound methods.
===========================================

.. toctree::
   :maxdepth: 3
   :caption: Contents:

   wirerope

The concepts:

- :class:`wirerope.rope.WireRope` is a wrapper interface for python callable.
- Custom :class:`wirerope.wire.Wire` class provides user-defined behavior.
  A subclass of this class is working similar to a *decorator function* body.
- A wire object is associated with a bound method.
- Rope is dispatching types.

:class:`wirerope.rope.WireRope` is the wrapper for callables. By wrapping a
function with `WireRope` with a custom subclass of the :class:`wirerope.wire.Wire`
class, the wire object will be created by each function or bound method.

`Wire` is the most important part. The given class will be instantiated and
bound to each function or bound method - which fits the concept of *instance
cmethod* of human.
For example, when `f` is a free function or staticmethod, the wire also will
be a single object. When `f` is a method or property, wires will be created for
each method owner object `self`. When `f` is a classmethod, wires will be
created for each method owner class `cls`. Yes, it will detect the owner
and bound to it regardless of the calling type.

`Rope` is internal dispatcher. It will be helpful when creating a complex
object for decorated callable instead of simple callable feature.


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
