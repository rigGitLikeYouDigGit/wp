
from __future__ import annotations, print_function

"""general libs for sequence types"""

from types import GeneratorType

import typing as T

SEQUENCE_TYPES = (list, tuple, set)
MAP_TYPES = (dict,)
NESTED_TYPES = SEQUENCE_TYPES + MAP_TYPES

# lambda to allow negative indexing
resolveSeqIndex = lambda index, length : (index if index >= 0 else length + index) % (length + 1)

# lambda to coerce values to iterable input
toSeq = lambda x: x if isinstance(x, (*SEQUENCE_TYPES, *MAP_TYPES)) else (x, )

# return empty sequence if original value is not
toSeqIf = lambda x: (x if isinstance(x, (*SEQUENCE_TYPES, *MAP_TYPES)) else (x,)) if x else ()

# may need to be moved higher if we need stronger high-level coercion
isSeq = lambda x: isinstance(x, tuple(SEQUENCE_TYPES))

def toArgList(i, argType=str):
	"""return a list of arguments, given a single value
	"""
	if isinstance(i, argType):
		return [i]
	return list(i)

def strList(i)->list[str]:
	if isinstance(i, str):
		return [i]
	return list(i)

getFirst = lambda x: next(iter(x), None)

def flatten(l, ltypes=(list, tuple))->(tuple, list):
	"""after Mike C Fletcher"""
	if isinstance(l, str):
		return l
	if isinstance(l, GeneratorType):
		l = tuple(l)
	ltype = type(l)
	try:
		ltype(l)
	except TypeError: # happens when passing in dict_values or similar
		ltype = tuple
	l = list(l)
	i = 0
	while i < len(l):
		while isinstance(l[i], ltypes):
			if not l[i]:
				l.pop(i)
				i -= 1
				break
			else:
				l[i:i + 1] = l[i]
		i += 1
	return ltype(l)

firstOrNone = lambda x: next(iter(x), None)

def indexByPath(value:NESTED_TYPES, keyIndexPath:list):
	"""lookup a value in a nested structure by a path"""
	while keyIndexPath:
		keyIndex = keyIndexPath[0]
		value = value[keyIndex]
		keyIndexPath = keyIndexPath[1:]
	return value


def visitTemplateFunction(element, parent:NESTED_TYPES, keyIndexPath:list):
	"""example function for recursive visit system below
	if replace, value returned from this function will replace original value"""
	return element

def containsObject(iterable, instance):
	"""returns True if iterable contains the literal given object
	"""
	return any(i is instance for i in iterable)


def iterWindowIndices(seq:T.Sequence):
	"""iterate over sequence giving window
	of (prev, current, next)
	"""
	l = len(seq)
	for i in range(l):
		yield (
			((i - 1) % l),
			i,
			((i + 1) % l),
		       )

def iterWindow(seq:T.Sequence):
	for prev, current, next in iterWindowIndices(seq):
		yield (seq[prev], seq[current], seq[next])

def shiftListEntries(arr, lookupOffset=1):
	""" given a list, shift its entries by given offset,
	positive or negative
	by default duplicates last entry"""
	for i in range(len(arr) - 1):
		arr[i] = arr[i + lookupOffset]



