
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

Should we meaningfully separate version of data format, and version of loader?
Version of data format is all that matters, loader versions can change freely
as long as they remain compatible.

Serial data must always be a dict.

We DO still need a type reference system, unless we make an entirely new adaptor
for every possible custom class, dataclass, enum, etc. that we want to serialise.
balls.

We just use string code refs to serialised types - if this ever needs upgrading, shouldn't
require any changes to these classes


Tree shows weakness of encoder system - structure of data tied to structure of object,
headings, properties etc. you would need to encapsulate EVERYTHING


can it be simplified? whole versioning system only matters for loading - 

# in main object
def deserialise(data, dataVersion):
	
	if dataVersion == 1:
		# load version 1 to latest, current object version
	elif dataVersion == 2:
		# load version 2 to latest, current object version
		
wasted a lot of time but this is better and so much simpler,
this is fine
		
we leave humans to specify current data version for saving,
later might try some crazy tracking in the repo to auto-detect
changes to certain functions


"""

from .adaptor import SerialAdaptor

# import and register all default types
from . import applied as _applied

# import the custom base class
from .main import Serialisable

