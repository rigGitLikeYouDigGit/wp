from __future__ import annotations
import typing as T
import os, pathlib, weakref

from PySide2 import QtGui, QtCore

from wplib.constant import LITERAL_TYPES

from wplib.object import UidElement

from wptree.main import Tree
from wptree.delta import TreeDeltas
from wptree.ui.constant import addressRole, relAddressRole, childBoundsRole, treeObjRole, rowHeight


if T.TYPE_CHECKING:
	from tree.ui.model import TreeModel

"""for these ui items, we take an immediate approach of syncing and items directly
whenever tree changes
it's just so much simpler
 """



class TreeValueItem(QtGui.QStandardItem):
	""""""

	def __init__(self, tree:Tree):
		self.treeRef = weakref.ref(tree)
		super(TreeValueItem, self).__init__(
			self.processValueForDisplay(self.tree.value)
		)

	def getTree(self)->Tree:
		assert self.treeRef() is not None, "tree is dead"
		return self.treeRef()

	@property
	def tree(self):
		return self.getTree()

	def trueValue(self):
		return self.getTree().value

	def branchItem(self)->TreeBranchItem:
		return self.parent().child(self.row(), 0)

	def onTreeStateChanged(self, branch:Tree):
		if branch is not self.getTree():
			return
		self.setData(branch.value, role=2)


	def processValueForDisplay(self, value):
		""" strip inner quotes from container values -
		this is the raw data, separate from any fancy rendering later
		"""
		if value is None:
			return ""
		return str(value)

	def processValueFromDisplay(self, value):
		"""return displayed or entered text value
		to real type -
		don't change the type of the tree value if ambiguous
		"""
		if not value:
			if self.trueValue() is None:
				return None
		# if isinstance(value, LITERAL_TYPES):
		# 	return value
		return str(value)

	def setData(self, value, role=2):
		""""""
		if role == 2: # user role
			self.tree.value = value
			valueObj = self.processValueForDisplay(value)

			return super(TreeValueItem, self).setData(valueObj, role=role)
		return super(TreeValueItem, self).setData(value, role)


	def data(self, role=QtCore.Qt.DisplayRole):
		"""return the right font advance for value text"""
		if role == QtCore.Qt.SizeHintRole:
			return QtCore.QSize(
				len(str(self.tree.value)) * 7.5 + 3,
				rowHeight)
		base = self.processValueFromDisplay(
			super(TreeValueItem, self).data(role))
		base = super(TreeValueItem, self).data(role)
		return base


	def __repr__(self):
		return "<ValueItem {}>".format(self.data())
	def __hash__(self):
		return id(self)

	def onTreeValueChanged(self, branch, oldValue, newValue):
		if branch is not self.tree:
			return
		self.setData(newValue, role=2)



class TreeBranchItem(QtGui.QStandardItem, UidElement):
	"""small wrapper allowing standardItems to take tree objects directly.
	Always 1:1 with tree python object
	"""

	indexInstanceMap = {}

	def __init__(self, tree):
		""":param tree : Tree"""
		self.treeRef = weakref.ref(tree)
		QtGui.QStandardItem.__init__(self, self.tree.name)
		UidElement.__init__(self, self.tree.uid)

		self.setColumnCount(1)

		self.tree.getSignalComponent().structureChanged.connect(
			self.onBranchEventReceived)
		self.tree.getSignalComponent().valueChanged.connect(
			self.onBranchEventReceived)
		self.tree.getSignalComponent().nameChanged.connect(
			self.onBranchEventReceived)


	def sync(self):
		#print("item sync", self, self.tree.branches)
		for i in range(self.rowCount()):
			self.takeRow(0)
		for i in self.tree.branches:
			self.appendRow(self.itemsForBranch(i))

	def onBranchEventReceived(self, event:TreeDeltas.Base):
		"""fires when a python branch object gets an internal event, including state deltas -
		use to regenerate branch items below the given one"""
		# print("")
		# print("branch event received", event, self.tree)
		if not self.model():
			return
		if not isinstance(event, TreeDeltas.Base):
			return
		# deltas : list[TreeDeltas.Base] = event.da
		self.sync()
		#return
		shouldSync = True
		# for i in deltas:
		# 	#print("branch to sync for delta", branchToSyncForDelta(i, self.tree.root))
		# 	if branchToSyncForDelta(i, self.tree.root) is self.tree:
		# 		shouldSync = True

		if shouldSync:
			self.model().beforeBranchSync(self)
			self.sync()
			self.model().afterBranchSync(self)

	def getTree(self)->Tree:
		assert self.treeRef() is not None, "tree is dead"
		return self.treeRef()

	@property
	def tree(self):
		return self.getTree()

	def __repr__(self):
		return "<BranchItem {}>".format(self.data())

	def __hash__(self):
		return id(self)

	def valueItem(self)->TreeValueItem:
		"""return the associated value item for this branch"""
		return self.parent().child(self.row(), 1)

	def valueItemClsForBranch(self, branch:Tree):
		"""return the value item class for the given tree branch"""
		return TreeValueItem

	def makeValueItemForBranch(self, branch:Tree):
		"""return a value item for the given tree branch"""
		return self.valueItemClsForBranch(branch)(branch)

	@classmethod
	def itemsForBranch(cls, branch:Tree):
		"""return (TreeBranchItem, TreeValueItem) for the
		given tree branch"""
		# create branches first
		branchItem = cls(branch)
		valueItem = branchItem.makeValueItemForBranch(branch)

		mainItems = (branchItem, valueItem)
		for i in branch.branches:
			branchItems = cls.itemsForBranch(i)
			mainItems[0].appendRow(branchItems)
		#print("itemsForBranch returning", mainItems)
		return mainItems

	def data(self, role=QtCore.Qt.DisplayRole):
		""" just return branch name
		data is used when regenerating abstractTree from model"""
		if role in (addressRole, relAddressRole):
			#print("get data", self.tree.address(), role)
			pass

		# if role == QtCore.Qt.DecorationRole:
		# 	return self.icon
		if role == addressRole:
			#print("addressData", self, self.tree.address())
			return self.tree.address()
		elif role == relAddressRole:
			"""same behaviour for now - may have to retire relAddressRole,
			model is always on tree root, it's for individual displays to
			determine relative address"""
			return self.tree.address()

			#print("relAddressData", self, self.tree)
			# may not be actual tree root if ui is scoped on specific part of tree
			uiRoot = self.model().rootItem.tree
			#print("uiRoot", uiRoot)
			rel = self.tree.relAddress(uiRoot)
			#print("rel address", rel)
			return rel

		# elif role == QtCore.Qt.SizeHintRole:
		# 	# return QtCore.QSize(
		# 	# 	len(self.tree.name) * 7.5,
		# 	# 	rowHeight)
		# 	metrics = QtGui.QFontMetrics(self.font())
		# 	length = metrics.size(
		# 		QtCore.Qt.TextSingleLine,
		# 		self.data(QtCore.Qt.DisplayRole)).width()
		# 	return QtCore.QSize(length, rowHeight)


		elif role == childBoundsRole:
			pass

		elif role == treeObjRole:
			return self.tree

		# check for displaying file path
		elif role == QtCore.Qt.DisplayRole:
			if self.tree.getAuxProperty("filePath"):
				# show last 2 tokens
				#fileStr = htmlColour(self.getFileTokensToDisplay(), colour="Gray")
				fileStr = self.getFileTokensToDisplay()
				return "..." + fileStr + " // " + self.tree.name
			base = super(TreeBranchItem, self).data(role)
			#return self.tree.name

		# tooltip to show tree auxProperties
		elif role == QtCore.Qt.ToolTipRole:
			return self.tree.getDebugData()

		base = super(TreeBranchItem, self).data(role)
		return base

	def setData(self, value, role=2):  # sets the NAME of the tree


		name = self.tree.setName(value)  # role is irrelevant

		try:
			result = super(TreeBranchItem, self).setData(name, role)
			self.emitDataChanged()
		except:
			pass



