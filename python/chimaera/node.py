
from __future__ import annotations
import typing as T

import fnmatch

from collections import namedtuple

from wplib import log, Sentinel, TypeNamespace
from wplib.constant import MAP_TYPES, SEQ_TYPES, STR_TYPES, LITERAL_TYPES, IMMUTABLE_TYPES
from wplib.uid import getUid4
from wplib.inheritance import clsSuper
from wplib.object import UidElement, ClassMagicMethodMixin

from wptree import Tree


from chimaera.lib import tree as treelib



"""
can a node just be a tree?
outer node attributes each have "incoming" and "defined" ?
{
node uid : node name
	"type" : node type
	"params" : 
		"incoming" : "CLS"
		"defined" : "root" # could have root as value, to separate stable and dynamic regions
			
			 
	
	"storage" : 
		"root" 
	
	
currently graph structure depth is represented literally in tree data -
for now is ok


need to weaken connection between node wrapper and data - 
wrapper cannot be cached, since we need to dynamically
change the node type by string attribute

node.attr("type") -> attribute wrapper
node(".type") -> attribute wrapper
node.type -> attribute wrapper
node.type.resolve() -> resolved type
node.type.resolve()() -> new node of matching type

node.type() -> directly resolve attribute, resolved type
node.type()() -> directly resolve attribute, resolved type, new node of matching type


node("/type") -> child node called "type"


SEPARATE EVERYTHING.
separate node type looked up constantly is fine,
all concrete node objects just have python type ChimaeraNode 

Any filter or search operations return a flat list matching the query -
single values are taken as the first element, or None if no match or list is empty


node "type" attribute resolves to list - in the limit, a way to have nodes act as 
dynamic subclasses of these bases.
usually just a single value


child nodes tracked with "nodes" attr





incoming attributes sorted into tree with list values

list values composed together, and then child branches
are composed on top

root : [ a, b, c]
	branch : [ d.p, f.storage("branch2"), c ]


example value incoming might be ["T", "uid", "uid.p[branch, leaf]"] -
so node type value is base, and incoming nodes are overlayed on top 

but surely we don't know what the node's default value is before knowing its inputs

defined value should be T.compute()

no reason to allow the tree-overlay stuff for value too - 

value should always be run through a callable or expression - that callable can
also handle overlaying params or parts of it, on value data before or after compute, etc

eventually a value expression should look like
"T.compute(self, $in)" or something

params might have sections of "preCompute" and "postCompute" -


still need the refMap for adding nodes into node-local variables

refMap : []
	"refName" : [node filters]


refMap : [node uid] <- inherit refMap from another node
	"refName" : [node filters]
	
	
incoming cannot edit incoming data - any logic is only used to filter and compose incoming

incoming:
	defined: raw tree of strings as entered by user
	resolved: tree of node lists, expressions eval'd
	evaluated: tree of rich trees in values
	composed: final tree of incoming graph data
	
	
value works on same principle as others - 
default is T.compute, which is a callable at root level, 
so operates on the root of all incoming data
	
	
	
so the tree stack would be:
overlay( value.incoming, params.resolve )

how can we generalise normal python functions to work on trees?
string searchReplace for example - 
MAPTONAMES(b, b.replace("L_", "R_"))
MAPTOVALUES()
MAPTOBRANCHES(b, b.name = b.name.replace("L_", "R_") )
?

with exp shorthand for variables?
($NAME=b): b.replace("L_", "R_")
($BRANCH=b): b.name.replace("L_", "R_") 

prefer this to the expressions, but should probably flip the arg names.
this flows better as a lemma to me, "let BRANCH equal b" etc,
but it's literally the opposite way round to the rest of python

(b=$NAME) : b.replace 

could always do simply $NAME = $NAME.replace("L_", "R_")

maybe something like the match statements?



intermediate stage of incoming tree should resolve branches to lists of tuples:

root : [(node uid, attribute, path), (node uid, attribute, path), (node uid, attribute, path)]
	+ branch : [(node uid, attribute), (node uid, attribute), (node uid, attribute)]
	
etc


pendulum swings
now use instance node classes, not class methods
handle dynamic node types changing somehow
it's worth it for easier writing in compute context - 
self.controlGrp, self.markNode, self.setOutput, etc




RESOLVE INCOMING CONNECTIONS:

tree starts out with simple string values - list expressions, uids, etc

root : [ "T" ]
	+ trunk : [ "uid", "n:ctl*nodes", "uid.p[branch, leaf]" ]
		+ branch : [ "n:overrideNode"[trunk, branch, leaf] ]

expand all node expressions
resolve to tree[list[tuples]] of (node uid, attribute, path)

root : [ ("T", "value", ()) ]
	+ trunk : [ ("uid", "value", ()), 
					(ctlA uid, "value", ()),
					(ctlB uid, "value", ()),
					(other uid, "params", ("branch", "leaf")),
					 ]
		+ branch : [ (overrideNode uid, "value", ("trunk", "branch", "leaf")) ]

this tree gives definitive list of nodes and attributes to be used as input

convert to tree[list[trees]] of rich trees

root : [ type default value tree ]
	+ trunk : [ value tree, 
					ctlA value tree,
					ctlB value tree,
					otherValueTree(branch, leaf)
					 ]
		+ branch : [ overrideNode value("trunk", "branch", "leaf") ]


resolve THAT tree top-down, with lists resolving from left to right

raw tree("trunk", "branch") will index into outer result tree("trunk", "branch"),
and use that as the base tree for overlaying with value of raw tree("trunk", "branch") 

"""


if T.TYPE_CHECKING:
	class NodeAttrRef(namedtuple):
		uid : str
		attr : str = "value"
		path : tuple[(str, int, slice), ...] = ()
else:
	NodeAttrRef = namedtuple("NodeAttrRef", "uid attr path")



def expandIncomingTree(rawTree:Tree,
                       attrWrapper:NodeAttrWrapper,
                       parentNode:ChimaeraNode,
                       graph:ChimaeraNode)->Tree:
	"""expand the incoming tree for this attribute -

	filtering actual tree with path requires explicitly
	defining tree to use - ".p[branch, leaf]" etc
	if .p or .v is not defined, will slice nodes found by
	uid matching

	STILL need a general solution to evaluate normal python code
	within these that RESOLVES to a node expression, path etc

	path is always () for now, get back to it later

	return tree[list[tuple[
		str node uid,
		str attribute,
		tuple[str] path
		]]]"""
	#assert graph
	for branch in rawTree.allBranches(includeSelf=True):
		rawValue = branch.value
		if not isinstance(rawValue, SEQ_TYPES):
			rawValue = [rawValue]
		resultTuples : list[NodeAttrRef] = []
		for i in rawValue: # individual string expressions

			# separate nodes / node terms from path if given
			nodeExpr = i.split(".")[0]
			pathTokens = i.split(".")[1:]

			attr = "value"
			if pathTokens:
				attr = pathTokens

			# expand node lists to individual uids
			if nodeExpr == "T":
				resultTuples.append( NodeAttrRef("T", attrWrapper.name(), ()) )
				continue

			if graph is not None:
				for node in graph.getNodes(nodeExpr):
					resultTuples.append( NodeAttrRef(node.uid, attr, ()) )
		branch.value = resultTuples

def populateExpandedTree(expandedTree:Tree[list[NodeAttrRef]],
                         attrWrapper:NodeAttrWrapper,
						 parentNode:ChimaeraNode,
						 graph:ChimaeraNode)->Tree:
	"""populate the expanded tree with rich trees -
	expand each node attr ref into a rich tree"""

	for branch in expandedTree.allBranches(includeSelf=True):
		newValue = []
		for i in branch.value: #type:NodeAttrRef
			#log("populateExpandedTree", i, i.uid)

			if i.uid == "T":
				newValue.append(parentNode.getAttrInputFromType(
					attrWrapper.name(), parentNode))
				continue
			newValue.append(graph.getNodes(i.uid)[0]._attrMap[i.attr].resolve())
		# branch.value = [graph.getNodes(i.uid)[0]._attrMap[i.attr].resolve() for i in branch.value]
		branch.value = newValue

def overlayPopulatedTree(populatedTree:Tree[list[Tree]],
                         attrWrapper:NodeAttrWrapper,
                         parentNode:ChimaeraNode,
                         graph:ChimaeraNode)->Tree:
	"""overlay the populated tree -
	overlay each tree in populated branch value, left to right
	then for any child branches in populated tree,
	overlay the result branch at that path with the overlaid result
	"""
	resultTree = Tree("root")
	for populatedBranch in populatedTree.allBranches(includeSelf=True,
	                                        depthFirst=True,
	                                        topDown=True):
		resultBranch = resultTree(
			populatedBranch.address(
			includeSelf=True, includeRoot=False, uid=False),
						create=True)
		for i in populatedBranch.value:
			resultBranch = treelib.overlayTreeInPlace(resultBranch, i,
			                                          mode="union")
	return resultTree



def resolveIncomingTree(
		rawTree:Tree,
		attrWrapper:NodeAttrWrapper,
		parentNode:ChimaeraNode,
		graph:ChimaeraNode)->Tree:
	"""resolve the incoming tree for this attribute -
	replace string references with trees to compose"""
	resultTree = rawTree.copy()

	# expand expressions to tuples of (node uid, attribute, path)
	expandIncomingTree(resultTree, attrWrapper, parentNode, graph)

	# populate expanded tree with rich attribute trees
	populateExpandedTree(resultTree, attrWrapper, parentNode, graph)
	# this tree is cached so we don't have to resolve a load of node addresses
	# every time -
	# if the incoming data is filtered by dynamic expression, we can't cache :(
	# not sure how to detect this
	cacheTree = resultTree.copy()

	# overlay rich trees into final incoming data stream
	return overlayPopulatedTree(resultTree, attrWrapper, parentNode, graph)




def getEmptyTree():
	return Tree("root")


def getEmptyNodeAttributeData(name: str, incoming=("T", ), defined=())->Tree:
	t = Tree(name)
	t["incoming"] = list(incoming)
	t["defined"] = list(defined)
	return t


class NodeAttrWrapper:
	def __init__(self, attrData:Tree, node:ChimaeraNode):
		self._tree = attrData
		self.node = node

	def name(self)->str:
		return self._tree.name

	# region locally defined overrides
	def defined(self)->Tree:
		return self._tree("defined")

	def setDefined(self, value):
		"""manually override"""
		self._tree["defined"] = value
	#endregion

	# incoming connections
	def incomingTreeRaw(self)->Tree:
		"""raw tree with string filters"""
		return self._tree("incoming", create=False)

	def incomingTreeResolved(self)->Tree:
		"""incoming with rich trees resolved"""
		#print("SELF", self, self.node, self.node.parent())
		#assert self.node.parent(), f"node {self.node} has no parent"
		return resolveIncomingTree(self.incomingTreeRaw(),
		                           self,
		                           self.node,
		                           self.node.parent())

	def incomingComposed(self)->Tree:
		"""composed final tree of incoming data"""

		baseTree = self.incomingTreeResolved()
		return baseTree
		# resultList = baseTree.value
		# # overlay all incoming trees for this level of input tree
		# # TODO: proper node EvaluationReport / error system to give details
		# assert all(isinstance(i, Tree) for i in
		#            resultList), f"resultList {resultList} \n for attr {self} not all trees"
		# try:
		# 	resultTree = treelib.overlayTrees(resultList)
		# 	# no recursion yet
		# 	return resultTree
		# except Exception as e:
		# 	log("error composing incoming tree")
		# 	self.incomingTreeResolved().display()
		# 	raise e


	def setIncoming(self, value:(str, list[str])):
		"""reset incoming connections to given value"""

	# endregion

	# region resolved value
	def resolve(self)->Tree:
		"""return the resolved tree for this attribute.

		if defined is callable, call it with incoming data
		 and this node.
		if defined is tree, compose it with incoming and
		eval any expressions

		nodeType defines default behaviour in composition, which may
		be overridden at any level of tree
		"""

		#log("RESOLVE")
		#log("attr", self.name(), self.node)

		if self.name() == "value":
			# send to nodeType compute
			return self.node.compute(
				self.incomingComposed()
			)
		if not self.node.parent():
			return self.defined()
		incoming = self.incomingComposed()

		defined = self.defined()

		return treelib.overlayTrees([incoming, defined])

		try:
			return treelib.overlayTrees([incoming, defined])
		except Exception as e:
			log("error overlaying incoming and defined")
			log("incoming")
			incoming.display()
			log("defined")
			defined.display()
			raise e

	def resolveToList(self)->list:
		"""return the resolved value of the top branch for this attribute
		"""
		val = self.resolve().value
		if isinstance(val, list):
			return val
		return [val]

	def __call__(self) -> Tree:
		# specialcase type, messy but whatever
		if self.name() == "type" :

			# T E M P
			# use directly defined type for now to avoid recursion
			return ChimaeraNode.getNodeType(self.defined().value[0])

		return self.resolve()

	# @staticmethod
	# def resolveNodeTypeMROFromTree(tree:Tree)->list[type[_NodeTypeBase]]:
	# 	"""return the node type mro for the given tree"""
	# 	return [NodeType.getNodeType(i) for i in tree.value]

	# endregion

class ChimaeraNode(UidElement, ClassMagicMethodMixin):
	"""node's internal data is a tree -
	this wrapper may be created and destroyed at will.

	Node objects should look up their NodeType live from "type" attribute,
	so type can be changed dynamically.


	Tree composition behaviour -
		default defined by node type
		can be overridden within branches by expression
	"""

	# region node type identification and retrieval

	nodeTypeRegister : dict[str, type[_NodeTypeBase]] = {}

	@classmethod
	def prefix(cls)->tuple[str]:
		"""return the prefix for this node type -
		maybe use to define domain-specific node types.
		c : chimaera (always available)
		m : maya
		h : houdini
		b : blender
		n : nuke
		"""
		return ("c", )

	@classmethod
	def typeName(cls)->str:
		return "base"

	@staticmethod
	def registerNodeType(cls:type[ChimaeraNode]):
		"""register the given node type -
		deal with prefixes some other time"""
		cls.nodeTypeRegister[cls.typeName()] = cls

	@classmethod
	def __init_subclass__(cls, **kwargs):
		"""register a derived ChimaeraNode type"""
		super().__init_subclass__(**kwargs)
		cls.registerNodeType(cls)


	@staticmethod
	def getNodeTypeFromDataTree(data:Tree):
		"""get the right node type to use for
		a data tree"""
		return ChimaeraNode.nodeTypeRegister[data["type", "defined"][0]]

	@staticmethod
	def getNodeType(lookup:(str, ChimaeraNode, Tree))->type[ChimaeraNode]:
		"""return the node type for the given lookup string.
		Later maybe allow searching somehow
		"""

		if isinstance(lookup, str):
			return ChimaeraNode.nodeTypeRegister[lookup]

		if isinstance(lookup, ChimaeraNode):
			return lookup.type()

		if isinstance(lookup, Tree):
			return ChimaeraNode.getNodeTypeFromDataTree(lookup)


	# region node attributes

	@classmethod
	def getNewNodeAttrTree(cls, attrName:str,
	                       incoming=("T", ),
	                       defined=())->Tree:
		"""return the data tree for a newly created node attribute -
		by default this is also the live default value for a node's evaluation.
		probably don't override this
		"""
		empty = getEmptyNodeAttributeData(attrName, incoming=incoming, defined=defined)
		return empty

	@classmethod
	def newNodeData(cls, name:str, uid="")->Tree:
		"""return the default data for a node of this type"""
		t = Tree(name)
		if uid:
			t.setElementId(uid)
		t.addChild(cls.getNewNodeAttrTree("type",
		                                  incoming=(),
		                                  defined=(cls.typeName(),)
		                                  ))
		t.addChild(cls.getNewNodeAttrTree("nodes",
		                                  defined=(),
		                                  incoming=("T",)
		                                  ))
		#t.addChild( cls.getNewNodeAttrTree("edges", incoming="T") )
		t.addChild(cls.getNewNodeAttrTree("value",
		                                  incoming=("T",),
		                                  defined=( ),
		                                  ))
		t.addChild(cls.getNewNodeAttrTree("params"))
		t.addChild(cls.getNewNodeAttrTree("storage"))
		return t


	@classmethod
	def getDefaultParams(cls, forNode:ChimaeraNode):
		"""return the default params tree for this node type.
		could be REALLY adaptive and pass in the node instance to
		these methods, but maybe we shouldn't
		"""
		return getEmptyTree()

	@classmethod
	def getDefaultStorage(cls, forNode:ChimaeraNode):
		"""return the default storage tree for this node type"""
		return getEmptyTree()

	@classmethod
	def getAttrInputFromType(cls, attrName:str, forNode:ChimaeraNode)->Tree:
		"""return the default input for a node attribute of this type"""
		if attrName == "params":
			return cls.getDefaultParams(forNode)
		if attrName == "storage":
			return cls.getDefaultStorage(forNode)
		return getEmptyTree()


	@classmethod
	def getDefaultAttrInput(cls, attrName:str)->Tree:
		"""return the default input for a node attribute of this type"""
		return getEmptyTree()

	# endregion

	# region node creation

	class _MasterGraph:pass
	_defaultGraph : ChimaeraNode = None
	@classmethod
	def defaultGraph(cls)->ChimaeraNode:
		"""return the default graph node -
		used for creating new nodes
		"""
		if cls._defaultGraph is None:
			cls._defaultGraph = ChimaeraNode("graph", parent=cls._MasterGraph)
		return cls._defaultGraph


	@classmethod
	def create(cls, name:str, uid="", parent:ChimaeraNode=None)->ChimaeraNode:
		"""create a new node of this type"""
		print("CREATE")
		newNodeData =  cls(
			cls.newNodeData(name, uid=uid)
		)
		# if parent is None:
		# 	parent = cls.defaultGraph()
		# parent.addNode(newNodeData)
		return newNodeData



	# region uid registering
	indexInstanceMap = {} # global map of all initialised nodes

	@classmethod
	def _nodeFromClsCall(cls,
	                     *dataOrNodeOrName: (str, Tree, ChimaeraNode),
	                     uid: str = None,
	                     ) -> (ChimaeraNode, bool):
		"""create a node from the given data -
		handle all specific logic for retrieving from different params

		bool is whether node is new or not
		"""

		if isinstance(dataOrNodeOrName[0], ChimaeraNode):
			# get node type
			nodeType = cls.getNodeTypeFromDataTree(dataOrNodeOrName[0].tree)
			if nodeType == cls:
				return dataOrNodeOrName[0], False

			return type(clsSuper(nodeType)).__call__(nodeType, dataOrNodeOrName[0].tree), False
			# return type(clsSuper(nodeType)).__call__(nodeType, dataOrNodeOrName[0].tree)


		if isinstance(dataOrNodeOrName[0], Tree):
			# check if node already exists
			lookup = cls.indexInstanceMap.get(dataOrNodeOrName[0].uid, None)
			if lookup is not None:
				return lookup, False

			# get node type
			nodeType = cls.getNodeTypeFromDataTree(dataOrNodeOrName[0])
			#print("retrieve node type", nodeType)

			#return type(clsSuper(nodeType)).__call__(nodeType, dataOrNodeOrName[0])
			return type.__call__(nodeType, dataOrNodeOrName[0]) , False

		if isinstance(dataOrNodeOrName[0], str):
			name = dataOrNodeOrName[0]
			data = cls.newNodeData(name, uid)
			return type(clsSuper(cls)).__call__(cls, data), True

		if uid is not None:
			# check if node already exists
			lookupNode = cls.indexInstanceMap.get(uid, None)
			if lookupNode is not None:
				return lookupNode, False

			# create new node object around data
			lookupData = Tree.getByIndex(uid)
			if lookupData:
				return type(clsSuper(cls)).__call__(cls, lookupData), False

		raise ValueError(f"Must specify one of name, data or uid - invalid args \n {dataOrNodeOrName}, {uid} ")

	@classmethod
	def __class_call__(cls,
	                   *dataOrNodeOrName:(str, Tree, ChimaeraNode),
	                   uid:str=None,
	                   parent=None
	                   )->ChimaeraNode:
		"""retrieve existing node for data, or instantiate new wrapper
				specify only one of:
		data - create object around existing data tree
		uid - retrieve existing data tree for object
		name - create new data tree with given name

		don't know why first arg is starred, remove it
		"""

		if not any((dataOrNodeOrName, uid)):
			raise ValueError("Must specify one of name, data or uid")
		assert not all((dataOrNodeOrName, uid)), "Must specify only one of name, data or uid"

		node, isNew = cls._nodeFromClsCall(*dataOrNodeOrName, uid=uid)
		if not isNew:
			return node
		if parent is cls._MasterGraph: # don't parent top graph
			return node

		if parent is None:
			parent = cls.defaultGraph()
			parent.addNode(node, force=True)
			return node
		parent.addNode(node)
		return node



	def __init__(self, data:Tree=None):
		"""create a node from the given data -
		must be a tree with uid as name

		"""

		super().__init__(uid=data.uid)
		self.tree : Tree = data

		# map just used for caching attribute wrappers, no hard data stored here
		self._attrMap : dict[str, NodeAttrWrapper] = {}

		# add attributes
		self.type = self._newAttrInterface("type")
		self.nodes = self._newAttrInterface("nodes")
		self.params = self._newAttrInterface("params")
		self.storage = self._newAttrInterface("storage")
		self.value = self._newAttrInterface("value")

	if T.TYPE_CHECKING: # better typing for call override
		def __init__(self,
		             *dataOrNodeOrName: (str, Tree, ChimaeraNode),
		             uid: str = None,
		             parent:ChimaeraNode=None
		             ):
			pass

	def __repr__(self):
		return f"<{self.__class__.__name__}({self.tree.name})>"


	def attrMap(self)->dict[str, NodeAttrWrapper]:
		return self._attrMap

	def _newAttrInterface(self, name:str)->NodeAttrWrapper:
		"""create a new interface wrapper for the given attribute name"""
		self._attrMap[name] = NodeAttrWrapper(self.tree(name, create=False),
		                                      node=self)
		return self._attrMap[name]


	def getElementId(self) ->keyT:
		return self.tree.uid

	@property
	def name(self)->str:
		return self.tree.name

	# def nodeTypeMRO(self)->list[type[_NodeTypeBase]]:
	# 	"""return the node type mro for this node"""
	# 	return self.type.resolveToList()

	# region child nodes
	def parent(self)->ChimaeraNode:
		"""return the parent of this node

		graph stores nodes as attributes, so

		graphRoot
			+ nodes
				+ defined
					nodeA
					nodeB
				+ incoming
					nodeC

		parent.parent.parent is graphRoot

		"""
		if not self.tree.parent: # top node of graph
			return None
		# parent of this graph will be the "nodes" branch -
		# we want the parent of that

		return ChimaeraNode(self.tree.parent.parent.parent)

	def addNode(self, nodeData:(ChimaeraNode, Tree), force=False):
		if isinstance(nodeData, ChimaeraNode):
			nodeData = nodeData.tree

		# print("ADD NODE")
		# print(self, nodeData, self.nodes.defined())

		# assert nodeData.name not in self.nodes.defined().keys(), f"Node {nodeData.name} already exists in graph {self}"
		self.nodes.defined().addChild(nodeData, force=force)

	def children(self)->list[ChimaeraNode]:
		"""return the children of this node"""
		return [ChimaeraNode(i) for i in self.nodes.resolve().branches]

	def nameUidMap(self)->dict[str, str]:
		"""return a map of node names to uids"""
		return {n.name : n.uid for n in self.tree("nodes").branches}

	def nodeMap(self)->dict[str, ChimaeraNode]:
		combinedMap = {}
		for data in self.nodes.resolve().branches:
			combinedMap[data.name] = ChimaeraNode(data)
			combinedMap[data.uid] = ChimaeraNode(data)
		return combinedMap

	def getNodes(self, pattern:str)->list[ChimaeraNode]:
		"""return all nodes matching the given pattern -
		combine names and uids into map, match against keys"""
		#log("getNodes", pattern, self.nodeMap().keys())
		matches = fnmatch.filter(self.nodeMap().keys(), pattern)
		return [self.nodeMap()[i] for i in matches]


	def compute(self, inputData:Tree
	            )->Tree:
		""" OVERRIDE THIS

		active function of node, operating on incoming data.
		look up some specific headings of params if wanted -
		preIncoming, postIncoming, etc
		each of these can act to override at different
		points.

		If none is found, overlay all of params on value.

		The output of compute is exactly what comes out
		as a node's resolved value - if any extra overriding
		has to happen, do it here

		inputData is value.incomingComposed()
		"""
		#log("base compute")
		#log("input")
		#inputData = self.value.incomingTreeResolved()
		#inputData.display()

		#log("composed")
		# inputData = self.value.incomingComposed()
		# #inputData.display()
		#
		# assert isinstance(inputData, Tree)


		# override with final defined tree
		return treelib.overlayTrees([inputData, self.value.defined()])


	# def getNode(self, node:(str, ChimaeraNode, Tree)):
	# 	if isinstance(node, str):
	# 		uidCheck = self.indexInstanceMap.get(node)
	# 		if uidCheck is not None:
	# 			return uidCheck
	# 		# check for name match
	# 		nameCheck = self.nameUidMap()
	#endregion

	# region edges
	# endregion

ChimaeraNode.registerNodeType(ChimaeraNode)







if __name__ == '__main__':

	testGraph : ChimaeraNode = ChimaeraNode("graph")
	print(testGraph)

	newNode = ChimaeraNode(testGraph.tree)
	print(newNode)
	print(newNode is testGraph)

	#print(newNode.type())

	# log("data")
	# graph._data.display()
	#
	# log("value defined")
	# graph.value.defined().display()

	# #print(graph.value.resolve())
	# value = graph.value.resolve()
	# log("final value")
	# value.display()

	# log("incomingRaw")
	# graph.value.incomingTreeRaw().display()
	# log("incomingResolved")
	# graph.value.incomingTreeResolved().display()


	nodeA = ChimaeraNode("nodeA")
	nodeB = ChimaeraNode("nodeB")
	testGraph.addNode(nodeA)

	assert nodeA.parent() is testGraph
	testGraph.addNode(nodeB)


	# nodes = graph.getNodes("node*")
	# print(graph.getNodes("node*"))
	#
	# print(nodeA in nodes)
	# print(nodeB in nodes)

	# # set up string join operation
	# nodeA.value.defined().value = "start"
	# nodeB.value.defined().value = "end"
	#
	# class StringJoinOp(NodeType):
	#
	# 	@classmethod
	# 	def compute(cls, node:ChimaeraNode#, inputData:Tree
	#             ) ->Tree:
	# 		"""active function of node, operating on incoming data.
	# 		join incoming strings
	# 		"""
	# 		log("string op compute")
	# 		joinToken = node.params()["joinToken"]
	#
	# 		# this could be done with just a list connection to single
	# 		# tree level, but this is more descriptive
	# 		incoming = node.value.incomingTreeResolved()
	# 		aValue = incoming["a"]
	# 		bValue = incoming["b"]
	# 		result = aValue + joinToken + bValue
	# 		return Tree("root", value=result)
	#
	#
	# opNode : ChimaeraNode = StringOp(name="opNode")
	# graph.addNode(opNode)
	#
	# # connect nodes
	# opNode.value.incomingTreeRaw()["a"] = nodeA.uid
	# opNode.value.incomingTreeRaw()["b"] = nodeB.uid
	#
	# # get result
	# result = opNode.value.resolve()
	#
	# log("result")














