
from __future__ import annotations
import typing as T

"""Redoing serialisation framework - it was already pretty decent,
but this has to be absolutely foolproof.

There are several issues to separate and solve:
- Serialise references to user-defined object types in code, which may move around.

- Serialise external or STL objects, where types cannot be modified.

- Serialise / deserialise arbitrarily nested data structures with single top-level call.

- Serialise data in future-proof way, so that a more modern version of the same type
can still load old serialised data.


adapters / subclasses to specify UID for serialisation.


Provide separate function or tool to run over a pool of serialised data files,
reading back which data versions of which types are actually in use.

In general though assume that once an encoder version is used once in anger,
that version will never be removed from code.

Use simple sequential versioning - readable, easy to track in code history if needed.

Encoder versions SHOULD NOT SHARE ANYTHING. No lib dependencies, no shared code,
everything copy-pasted. Otherwise a modification to shared code may break
multiple versions at once, or break back-compatibility.

(could investigate more hardcore ways to enforce this, like pickling and reloading
encoders themselves - actually an interesting idea, but for now against my 
better judgement, we trust the programmer)
"""
