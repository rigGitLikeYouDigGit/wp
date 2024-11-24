
from __future__ import annotations
import typing as T, types
from wplib import log


from PySide2 import QtCore, QtWidgets, QtGui
from wptree import Tree

from wplib import inheritance
from wpui.widget.canvas import *
from wpdex.ui import StringWidget
from wpdex.ui.atomic import ExpWidget
from chimaera import ChimaeraNode
from chimaera.attr import NodeAttrWrapper, NodeAttrRef
from wpdex import WpDexProxy, WX, react
from wpdex.ui import AtomicWindow, AtomicUiInterface
from wpui.widget.collapsible import ShrinkWrapWidget


if T.TYPE_CHECKING:
	from .scene import ChimaeraScene
	from .view import ChimaeraView
	from .node import NodeDelegate

"""
how the heck do we handle drawing connection points within scene 

"""

class ConnectionPoint:
	"""this shouldn't know much
	for now we assume a point is either a source or destination,
	as opposed to assuming connections are always dragged from
	source to destination
	"""
	def __init__(self, isSrc=True):
		self.isSrc = isSrc

	def connectionPoint(self,
	                    forDelegate:ConnectionDelegate
	                    )->tuple[tuple[float, float], (tuple[float, float], None)]:
		"""implement custom logic for the given delegate if wanted
		by default falls back to nearest point on outline, on bounding
		rect, etc

		optionally also return a tuple for the direction vector to use for the connection

		"""

	def connectionPath(self, forDelegate:ConnectionDelegate)->QtGui.QPainterPath:
		"""in case a connection can be made / slide along a patch on the given
		object
		by default return None"""

	#region drag processing

	def canAcceptDragConnections(self):
		"""overall method - if False, this won't be included in scene event checks
		for valid targets when dragging a connection"""
		return False

	def acceptsIncomingConnection(self, fromObj:ConnectionPoint)->bool:
		"""check if this point accepts a drag connection from the given source"""

	def acceptsOutgoingConnection(self, toObj:ConnectionPoint)->bool:
		"""check if a line from this point can attach to the given point
		both of the above must agree for a connection to be made"""

	def onIncomingConnectionAccepted(self, fromObj:ConnectionPoint)->bool:
		pass
	def onOutgoingConnectionAccepted(self, toObj:ConnectionPoint)->bool:
		pass
	#endregion

class ConnectionDelegate:
	"""
	holds start and end objects that could be ANYTHING - graphicsItems, widgets, points, etc

	need some way to flag when they move, or just sync at all times -

	for each end, first check if it defines a "connectionPoint()" method, and if so, check if that method returns None for this delegate (somehow, I know this splits the logic around)
	if not, try and check if the end points have a representation in scene - eg like bounding geometry
	if so take the connection points as the mutual closest points there, like for the group fields

	mixin parent class for now, at some point I might have to rewrite all of this into
	composition somehow
	for now we assume start and end

	"""

	def __init__(self,
	             start:(T.Any, types.FunctionType),
	             end:(T.Any, types.FunctionType),
	             **kwargs
	             ):
		"""allow static pointers or functions to look up based on
		other data contained in mixin"""
		self.start = start
		self.end = end

	def getConnectionPoints(self)->list[tuple[float, float], tuple[float, float]]:
		"""get the points and vectors to use to draw this delegate"""
		points = [None, None]
		vectors = [None, None]
		start = react.EVAL(self.start)
		end = react.EVAL(self.end)
		if not start:
			log("no start point found for delegate", self, self.start, self.end)
		if not end:
			log("no end point found for delegate", self, self.start, self.end)
		for i, obj in enumerate((start, end)):
			if isinstance(obj, ConnectionPoint):
				result = obj.connectionPath(forDelegate=self)
				if result is None:
					result = obj.connectionPoint(forDelegate=self)
				assert result is not None, "Must implement either connectionPath() or connectionPoint()"
				point, vector = result
				if vector is None:
					vector = (0.0, -1.0 if i else 1.0)
				points[i] = point
				vectors[i] = vector
			else:
				raise NotImplementedError("not supported yet:", obj)







	def onMouseHover(self,
	                 path:QtWidgets.QGraphicsPathItem,
	                 pos):
		"""called by drawConnections whenever the path associated with this
		element is moused over"""

class ConnectionScene:
	"""handle drag connection events - if it's legal,
	how the mouse move affects drawing, etc"""

	def onDragBegin(self, fromObj:ConnectionPoint):
		"""start drawing path"""
		pass

class DrawConnections:
	"""no idea -
	it seems that usually you need to draw multiple connections
	in awareness of the whole, not just one by one.

	this way we can have multiple ways to draw connections, without modifying the logic
	of where and how they connect
	"""

	def __init__(self, connections:list[ConnectionDelegate],
	             scene:QtWidgets.QGraphicsScene):
		self.connections = connections

	def draw(self):
		"""build collection of pathItems for each delegate after working out
		paths?
		then track which is matched to which?
		seems super complicated

		- just do setPath(), don't need to put mouse-over and interaction
		logic here
		"""

	def onMouseHover(self):
		"""work out which path is hovered over,
		then which delegate is associated with that path,
		then trigger that delegate's hover method?"""
		# NO







def paintDropdownSquare(rect:QtCore.QRect, painter:QtGui.QPainter,
          canExpand=True, expanded=False):
	painter.drawRect(rect)
	innerRect = QtCore.QRect(rect)
	innerRect.setSize(rect.size() / 3.0 )
	innerRect.moveCenter(rect.center())
	if expanded:
		rect.moveCenter(QtCore.QPoint(rect.center().x(), rect.bottom()))
	if canExpand:
		painter.drawRect(innerRect)


class OpenPlugRowConnectorPanel(QtWidgets.QGraphicsLineItem):
	"""single line that goes on the end of an open branch, showing actual connections
	from all node attributes

	should try and relax multiple connections to individual incoming streams -
	LATER
	"""

	def __init__(self, parent:OpenPlugRow=None):
		QtWidgets.QGraphicsLineItem.__init__(self, parent=parent)


class OpenPlugRow(QtWidgets.QGraphicsItem):
	""" a single triple of
	( attrRef (s), attribute, path )
	including connector panel on end
	TODO: in future we might just make this a single expression
	"""
	if T.TYPE_CHECKING:
		def parentItem(self)->PlugBranchItem: ...
	def __init__(self,
	             valueList:list[str, str, list],
	             parent:PlugBranchItem=None):
		QtWidgets.QGraphicsItem.__init__(self, parent)
		self.proxyW = QtWidgets.QGraphicsProxyWidget(parent=self
		                                             )
		self.w = ShrinkWrapWidget(parent=None)
		self.w.setContentsMargins(QtCore.QMargins(0, 0, 0, 0))
		self.w.setAutoFillBackground(False)
		self.w.setAttribute(QtCore.Qt.WA_TranslucentBackground)
		self.setWidgetResult = self.proxyW.setWidget(self.w)

		self.nodeLine = ExpWidget(value=valueList[0],
		                          parent=self.w)
		self.attrLine = ExpWidget(value=valueList[1],
		                          parent=self.w)
		self.pathLine = ExpWidget(value=valueList[2],
		                          parent=self.w)
		self.w.setLayout(QtWidgets.QHBoxLayout(self.w))
		for i in (self.nodeLine, self.attrLine, self.pathLine):
			self.w.layout().addWidget(i)

	def isInput(self)->bool:
		return self.parentItem().isInput

	def paint(self, painter, option, widget=...):
		pass

	def boundingRect(self):
		return self.childrenBoundingRect()

class PlugBranchItem(QtWidgets.QGraphicsItem,
                     AtomicUiInterface,
                     metaclass=inheritance.resolveInheritedMetaClass(
	                     QtWidgets.QGraphicsItem, AtomicUiInterface
                     )):
	"""single branch of tree for connections, showing branch name
	either collapsed or expanded view of individual link items

	testing using the same reactive interface in this too, gaining
	more faith in it as a general solution

	"""

	if T.TYPE_CHECKING:
		def parentItem(self)->(PlugBranchItem, NodeDelegate):...
		def value(self) ->Tree:...

	def __init__(self,
	             branch: Tree,
	             parent=None,
	             isInput=True,
	             ):
		AtomicUiInterface.__init__(self,
		                           value=branch)
		QtWidgets.QGraphicsItem.__init__(self, parent=parent)

		self.branch = branch
		self.isInput = isInput
		self.branchItems : dict[Tree, PlugBranchItem] = {}
		self.rowItems : list[OpenPlugRow] = []
		self.lines = []

	def node(self)->NodeDelegate:
		p = self.parentItem()
		while not isinstance(p, NodeDelegate):
			p = p.parentItem()
		return p

	def syncBranchItems(self):
		"""build out child items - leave layout for separate method
		"""
		for i in self.branchItems.values():
			self.scene().removeItem(i)
		self.branchItems.clear()

		for k, b in self.branch.branchMap():
			self.branchItems[b] = PlugBranchItem(b,
			                                     parent=self,
			                                     isInput=self.isInput)

	def syncRowItems(self):
		"""look at the current value of the tree, create an entry for each existing list
		item,
		plus a trailing empty one"""
		for i in self.rowItems:
			self.scene().removeItem(i)
		self.rowItems.clear()

		v = self.value()
		assert isinstance(v, Tree)
		if not isinstance(self.value().value, list):
			assert not self.value().value, f"Linking tree {self.value()} has non-list, non-None value"
			# unsure how to make this reactive - hook into empty and default values on dex
			row = OpenPlugRow()

	# for reactive widgets, allow an empty entry?
	# allow buttons to add and remove empty entries?
	# set this on WPDEX? default trailing value, default empty value?

	def syncLayout(self):
		pass

	def syncLines(self):
		pass



class TreePlugSpine(QtWidgets.QGraphicsItem):
	"""draw an expanding tree structure -
	this is used to display connections coming in to the
	"linking" tree of each attribute
	"""

	def __init__(self, parent=None, size=10.0):
		super().__init__(parent)
		self._expanded = False
		self.size = 10.0

	def childTreeSpines(self)->list[TreePlugSpine]:
		return [i for i in self.childItems() if isinstance(i, TreePlugSpine)]

	def expanded(self): return self._expanded
	def setExpanded(self, state): self._expanded = state; self.update()

	def boundingRect(self):
		return QtCore.QRectF(0, 0, self.size, self.size)
	def paint(self, painter:QtGui.QPainter, option, widget=...):
		"""draw a line backwards,
		a cross if not expanded,
		and the vertical bar down if expanded
		"""
		mid = self.size / 2.0
		painter.drawLine(-mid, mid, mid, mid)
		childSpines = self.childTreeSpines()
		if not self.childTreeSpines(): return
		paintDropdownSquare(rect=self.boundingRect(), painter=painter,
		                    canExpand=True, expanded=self.expanded())