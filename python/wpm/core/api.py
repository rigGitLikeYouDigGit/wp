
"""lib for core openmaya stuff
mainly MObject cache"""

from __future__ import annotations

import typing as T

from wplib import sequence
from wplib.object import UserSet


# small class representing each MFn type constant
from .cache import getCache, om


# access functions
def MObjectRegister():
	return getCache().mObjRegister

def apiTypeMap():
	return getCache().apiTypeMap

def apiTypeCodeMap():
	return getCache().apiTypeCodeMap

def apiCodeNameMap():
	return getCache().apiCodeNameMap

def apiTypeDataMap():
	return getCache().apiTypeDataMap

def mfnDataConstantTypeMap():
	return getCache().mfnDataConstantTypeMap

#mfnT = T.TypeVar('mfnT', bound=om.MFnBase)
# test to access all members of all MFn types

if T.TYPE_CHECKING:
	class MFMFnT(om.MFnDependencyNode,
	             # give
	             om.MFnDagNode,
	             om.MFnAttribute,
	             om.MFnNumericAttribute,
	             # me
	             om.MFnTypedAttribute,
	             om.MFnUnitAttribute,
	             om.MFnMatrixAttribute,
	             om.MFnCompoundAttribute,
	             om.MFnMessageAttribute,
	             om.MFnEnumAttribute,
	             # e v e r y t h i n g
	             om.MFnMesh,
	             om.MFnNurbsCurve,
	             om.MFnNurbsSurface,
	             om.MFnLattice,
	             om.MFnSet,
	             om.MFnSkinCluster,
	             om.MFnIkJoint,
	             om.MFnData
	             ):
		pass

def getMFn(obj: (om.MObject, str, om.MFn))->MFMFnT:
	"""return mfn function set initialised on the given object
	returns most specialised mfn possible for given object"""
	return getCache().getMFn(obj)

MFnT = T.TypeVar('MFnT', bound=om.MFnBase)
def asMFn(obj, mfnT:T.Type[MFnT])->MFnT:
	"""return mfn function set initialised on the given object
	returns most specialised mfn possible for given object"""
	return mfnT(getCache().getMObject(obj))


def getMFnType(obj: om.MObject) -> T.Type[om.MFnBase]:
	"""returns the highest available MFn
	for given object, based on sequence order
	above"""
	return getCache().getMFnType(obj)

def getMObject(node)->om.MObject:
	"""this is specialised for dg nodes -
	component MObjects will have their own functions anyway if needed
	"""
	return getCache().getMObject(node)

def nodeTypeFromMObject(mobj:om.MObject):
	"""return a nodeTypeName string that can be passed to cmds.createNode
	"""
	return getCache().nodeTypeFromMObject(mobj)

# region specific mfn functions
# dissuaded other than for explicit function use, since getMFn is superior
def toMFnDep(obj)->om.MFnDependencyNode:
	return om.MFnDependencyNode(getMObject(obj))
def toMFnDag(obj)->om.MFnDagNode:
	return om.MFnDagNode(getMObject(obj))
def toMFnTransform(obj)->om.MFnTransform:
	return om.MFnTransform(getMObject(obj))

def toMFnMesh(obj)->om.MFnMesh:
	return om.MFnMesh(getMObject(obj))
def toMFnCurve(obj)->om.MFnNurbsCurve:
	return om.MFnNurbsCurve(getMObject(obj))
def toMFnSurface(obj)->om.MFnNurbsSurface:
	return om.MFnNurbsSurface(getMObject(obj))

#endregion

def isDag(obj:om.MObject):
	return obj.hasFn(om.MFn.kDagNode)

def isTransform(obj:om.MObject):
	return obj.hasFn(om.MFn.kTransform)

def isShape(obj:om.MObject):
	return getCache().isShape(obj)


def classConstantValueToNameMap(cls):
	"""return a dict mapping class constants to their names"""
	return {v:k for k,v in cls.__dict__.items() if k.startswith('k')}


class MObjectSet(UserSet):
	"""convenience class providing filtering functions over contents
	"""
	# def uniqueObjs(self)->MObjectSet:
	# 	return MObjectSet(set(self))

	def validObjs(self)->MObjectSet:
		return MObjectSet(filter(lambda x: not x.isNull(), self))

	def filterObjs(self, mfnTypes:T.Iterable[int], toType=None)->(MObjectSet, set[EdNode]):
		"""if toType, given type is mapped across filter results, and
		a normal set of these items is returned"""
		filtered = MObjectSet(filter(lambda x: any(x.hasFn(i) for i in sequence.toSeq(mfnTypes)), self))
		if toType:
			return set(map(toType, filtered))
		return filtered

	# set-like methods



def listMObjects(type=om.MFn.kInvalid)->set[om.MObject]:
	mit = om.MItDependencyNodes(type)
	# objs = MObjectSet()
	objs = set()
	while not mit.isDone():
		objs.add(mit.thisNode())
		mit.next()
	return objs

# def listNamedMObjects()

# endregion


