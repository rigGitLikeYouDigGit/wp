
"""
higher-level extension of tree system

also provides interface for connecting ui widgets
 """
from __future__ import annotations

import pprint, copy, textwrap, ast

import typing as T

from wplib.object.element import UidElement
from wptree.reference import TreeReference


from wptree.interface import TreeInterface, TreeType
from .treedescriptor import TreeBranchDescriptor, TreePropertyDescriptor


class Tree(TreeInterface,
           UidElement,
           ):
	"""
	Real implementation of tree system, storing data in branch nodes.

	No complex integration beyond basic signals.
	"""

	TreePropertyDescriptor = TreePropertyDescriptor
	TreeBranchDescriptor = TreeBranchDescriptor

	# separate master dict of uids to branches
	indexInstanceMap = {} # type: T.Dict[str, Tree]


	def __init__(self, name: str, value=None,
	             uid=None):
		"""initialise real internal values for interface to affect"""
		#TreeInterface.__init__(self)
		UidElement.__init__(self, uid)
		#self._frameContextEnabled = False
		self._name = name
		self._value = value
		self._parent: TreeInterface = None
		self._branches: T.List[TreeType] = []  # direct list of child branch objects, main target for overriding
		self._properties = self.defaultProperties()


	def uidTie(self):
		return (self.uidRepr(), self._coreDataUid[:4] + "-", self.coreData().uidRepr())

	def uidView(self):
		return pprint.pformat([i.uidTie() for i in self.allBranches()])





	def getByUid(self, uid:str)->TreeType:
		"""allows searching by single uid for specific branch"""
		if uid in self._uidBranchMap():
			return self._uidBranchMap()[uid]
		for i in self.branches:
			result = i.getByUid(uid)
			if result: return result
		return None


	def getDebugData(self):
		"""return formatted display of tree data"""
		return textwrap.dedent(f"""
		{self},
		Properties : {pprint.pformat(self.auxProperties)}
		""")




	def contains(self, branch, equivalent=True):
		""" more explicit contains check, allowing for equivalence,
		inheritance, etc
		"""
		if equivalent:
			return any([branch.isEquivalent(i) for i in self.branches])
		else:
			return any([branch is i for i in self.branches])




	def search(self, path, onlyChildren=True):
		""" searches branches for trees matching a partial path,
		and returns ALL THAT MATCH
		so for a tree
		root
		+ branchA
		  + leaf
		+ branchB
		  + leaf
		search("leaf") -> two trees
		right now would also return both for search( "lea" ) -
		basic contains check is all I have

		if onlyChildren, only searches through children -
		else checks through all branches
		"""

		found = []
		if path in self.name:
			found.append(self)
		toCheck = self.branches if onlyChildren else self.allBranches(True)
		for i in toCheck:
			found.extend( i.search(path) )
		return found


	def mergeTo(self, targetBranch:Tree, recursive=True):
		"""add all of this tree's children to the given branch"""
		for i in self.branches:
			if i.name in targetBranch.keys() and recursive:
				i.mergeTo(targetBranch(i.name))
				continue
			targetBranch.addChild(i)
		self.remove()


	def delete(self, andData=True):
		self.remove()
		self.uidInstanceMap.pop(self.uid)
		del self


	def clear(self, delete=True, ):
		"""removes all branches of this tree"""
		for i in self.branches:
			if delete:
				i.delete()
			else:
				i.remove()


	def searchReplace(self, searchFor=None, replaceWith=None,
	                  names=True, values=True, recurse=True):
		"""checks over raw string names and values and replaces"""
		branches = self.allBranches(True) if recurse else [self]
		for branch in branches:
			if names:
				branch.name = str(branch.name).replace(searchFor, replaceWith)
			if values:
				branch.value = str(branch.value).replace(searchFor, replaceWith)

	def matchTree(self, otherTree:Tree, recursive=True,
	              force=False, clean=True):
		"""replaces the name and value of this tree
		with that of target
		if recursive, copies or removes branches to match
		if force, runs internal set methods - otherwise filters"""
		#print("match tree")
		if force:
			self.setName(otherTree.name)
		else:
			self.name = otherTree.name
		self.value = copy.deepcopy(otherTree.value)
		self._properties = copy.copy(otherTree.auxProperties)

		if not recursive:
			return

		if clean:
			self.clear()
			for i in otherTree.branches:
				self.addChild(i.copy())
			return

		for thisBranch, targetBranch in zip(
				self.branches, otherTree.branches):
			thisBranch.matchTree(targetBranch, recursive=True,
			                     force=force, clean=clean)


	def matches(self, other):
		""" check if name, value and extras match
		another given branch """
		return all([getattr(self, i) == getattr(other, i)
		            for i in ("_branchMap", "_value", "_name", "extras")])

	def update(self, tree, deep=True):
		""" copies over keys and values from tree
		not recursive or deep yet """
		for branch in tree.branches:
			self[branch.name] = branch.value
			if deep:
				self(branch.name).update(branch, deep=True)



	#endregion
	#region test

	# loading directly from a file
	@classmethod
	def loadFromFile(cls:type[TreeType], filePath:Path,
	                 makeReadOnly=False)->TreeType:
		"""loads a tree directly from a file,
		if makeReadOnly, edits are not allowed
		"""
		filePath = Path(filePath)
		assert filePath.exists(), f"No file {filePath} to load tree"

		with filePath.open("w") as f:
			fileTree = cls.fromDict(ast.literal_eval(f.read()))
			fileTree.filePath = filePath
			fileTree.readOnly = makeReadOnly
		return fileTree

	def saveToFile(self, filePath=None):
		"""if filePath is not specified and tree has an inherited property
		of filePath, that is used by default"""
		filePath = filePath or self.filePath
		assert filePath, f"No file for {self} to write data"
		filePath = Path(filePath)
		filePath.write_text(str(self.serialise()))


	#endregion


	# region ui integration
	def setUiData(self, widgetType:AtomicWidgetType,
	              widgetMin=None, widgetMax=None,
	              defaultPath:T.Union[str, PurePath]=None):
		uiData = BranchUiData(widgetType, widgetMin,
		                      widgetMax, defaultPath)
		self.setAuxProperty("uiData", uiData)

	#endregion

# set up global root namespace
#Tree.globalTree = Tree("globalRoots")

if __name__ == '__main__':
	t = Tree("a")
	print(t)
