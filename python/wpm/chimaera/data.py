

from __future__ import annotations
import typing as T

from dataclasses import dataclass

import numpy as np

from wptree import Tree

from chimaera.core import DataTree

from wpm import om, WN
from wpm.core import classConstantValueToNameMap
from wpm.lib.tracker import NodeLifespanTracker, NodeHierarchyTracker
from wpm.lib import hierarchy as h
from wpm.constant import Space

"""
throwing things at the wall

for now data trees literally represent hierarchy - values are 
rich data classes defining that node - shape, transform, etc

for sanity, we assume that in a data view, individual data objects are immutable - 
updating them requires setting value of tree. Likewise a user edit
in maya regenerates the entire tree.

duplication of some work here from the USD representation of 
nodes as flat arrays - the Data object should probably be the core,
with single conversions between it and the USD representation.

Then each Data can inherit domain-specific methods for interacting
with that dcc

"""

@dataclass
class Transform:
	"""data object for transform
	for now also includes optional dag path
	"""

	matrix : np.ndarray
	# rotateOrder : str = "XYZ"
	# dagPath : str = ""

	def applyToMObject(self, mayaObject:om.MObject):
		"""set mayaObject to this transform data
		for now use direct api calls, might look into DGModifiers
		if it's faster or lets us build changes with multiple threads
		"""
		mfn = om.MFnTransform(mayaObject)
		mfn.setTranslation(om.MVector(self.matrix[3, :3]), om.MSpace.kTransform)
		mfn.setRotation(om.MEulerRotation(self.matrix[:3, :3]), om.MSpace.kTransform)
		mfn.setScale(om.MVector(self.matrix[:3, :3]), om.MSpace.kTransform)

	@classmethod
	def fromMObject(cls, obj:om.MObject):
		mfn = om.MFnTransform(obj)
		matrix = np.identity(4)
		matrix[:3, :3] = np.array(mfn.rotation(Space.TF).asMatrix()).reshape(4, 4)[:3, :3]

		# set translation values along bottom row of matrix
		matrix[3, :3] = np.array(mfn.translation(Space.TF))
		matrix[:3, :3] *= np.array(mfn.scale())
		return cls(matrix)

	apiType = om.MFn.kTransform

@dataclass
class Mesh:
	"""data object for mesh shape
	"""

	facePointCounts : np.ndarray
	facePointConnects : np.ndarray
	pointCoords : np.ndarray

	def applyToMObject(self, mayaObject:om.MObject):
		"""set mayaObject to this transform data
		for now use direct api calls, might look into DGModifiers
		if it's faster or lets us build changes with multiple threads
		"""
		mfn = om.MFnMesh(mayaObject)
		mfn.createInPlace(
			self.pointCoords, self.facePointCounts, self.facePointConnects
		)

	@classmethod
	def fromMObject(cls, obj:om.MObject):
		mfn = om.MFnMesh(obj)
		return cls(
			*mfn.getVertices(),
			np.array(mfn.getPoints())[:, :3]
		)

	apiType = om.MFn.kMesh


class MayaData(DataTree):
	"""DataTree for Maya data.
	not sure of inheritance, only sketch for now

	If we use dataclasses as tree values, how do we detect changes to them?
	"""


	def createMayaNode(self, parentNode:om.MObject):
		pass



class TransformData(MayaData):

	def createMayaNode(self, parentNode:om.MObject):
		data : Transform = self.value
		dagMod = om.MDagModifier()
		transform = dagMod.createNode("transform", parentNode)
		dagMod.doIt()

		data.applyToMObject(transform)


def dataFromMayaNode(node:om.MObject):
	if node.hasFn(om.MFn.kMesh):
		return Mesh.fromMObject(node)
	elif node.hasFn(om.MFn.kTransform):
		return Transform.fromMObject(node)
	else:
		mfn = om.MFnDependencyNode(node)
		raise TypeError(f"no supported Data object for node {node}, {mfn.name()} of type {node.apiTypeStr}")

def gatherData(topNode:om.MObject):
	"""return tree from data"""
	objMap : dict[om.MObject, DataTree] = {}
	topPath = om.MDagPath.getAPathTo(topNode)
	topMFn = om.MFnDagNode(topPath)
	topTree = Tree("root")
	for node in h.iterDagChildren(topNode, includeRoot=False):
		mfn = om.MFnDagNode(om.MDagPath.getAPathTo(node))
		relPath = h.relativeDagTokens(topPath, mfn.dagPath())
		branch = topTree(*relPath, create=True)
		branch.value = dataFromMayaNode(node)


	return topTree




class MayaDataView(NodeHierarchyTracker):
	"""specify top transform to display data of given
	object, updating live when data changes.
	Also allow maya changes to affect data,
	if they pass validation.

	Can we formalise this somehow - effectively
	managing a central source of truth with multiple
	views and ways to edit it.
	Feels like a server and clients

	"""

	# def __init__(self, node:om.MObject, data:DataTree=None):
	# 	super(MayaDataView, self).__init__(node)
	# 	self.data : DataTree = None

	def displayDataTree(self):
		tree = gatherData(self.node())
		tree.display()


	def onChildNameChanged(self, node:om.MObject, prevName:str, *args):
		self.displayDataTree()

	def onChildNodeAdded(self, childPath:om.MDagPath, parentPath:om.MDagPath):
		self.displayDataTree()

	def onChildNodeRemoved(self,
	                       newChildPath:om.MDagPath,
	                       newParentPath:om.MDagPath,
	                       oldChildPath:om.MDagPath,
	                       oldParentPath:om.MDagPath
	                       ):
		self.displayDataTree()

	def onChildLocalMatrixModified(self, node:om.MObject, matrixModifiedFlags:int, *args):
		self.displayDataTree()

	def onChildMeshModified(self, node:om.MObject, dirtyPlug:om.MPlug, *args):
		self.displayDataTree()


