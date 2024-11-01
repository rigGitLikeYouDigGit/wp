

from __future__ import annotations

import pprint
import typing as T

from wplib import log, Sentinel, TypeNamespace
from wplib.constant import MAP_TYPES, SEQ_TYPES, STR_TYPES, LITERAL_TYPES, IMMUTABLE_TYPES
from wplib.uid import getUid4
from wplib.inheritance import clsSuper
from wplib.object import UidElement, ClassMagicMethodMixin, CacheObj, Adaptor
from wplib.serial import Serialisable
from wplib.object import VisitAdaptor, Visitable


from PySide2 import QtCore, QtWidgets, QtGui

from wpui.widget.canvas import *

from wpdex.ui import StringWidget

from chimaera import ChimaeraNode
from wpdex import WpDexProxy, WX


if T.TYPE_CHECKING:
	from .scene import ChimaeraScene
	from .view import ChimaeraView

"""

TODO: consider maybe inverting the flow for painting widgets? if every one in a hierarchy
	called back to a single root-defined function to see if it needs overrides
	or special treatment, colours etc ?
"""

refType = (WpDexProxy, WX)



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




class TreePlugSpine(QtWidgets.QGraphicsItem):
	"""draw an expanding tree structure"""

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

expandPolicy = QtWidgets.QSizePolicy(
	QtWidgets.QSizePolicy.Expanding,
	QtWidgets.QSizePolicy.Expanding
)
shrinkPolicy = QtWidgets.QSizePolicy(
	QtWidgets.QSizePolicy.Maximum,
	QtWidgets.QSizePolicy.Maximum
)
class ShrinkWrapWidget(QtWidgets.QWidget):

	def sizeHint(self):
		baseRect = QtCore.QRect()
		for i in self.children():
			for at in ["boundingRect", "rect"]:
				try:
					r = getattr(i, at)()
					baseRect = baseRect.united(r)
					break
				except: continue
		size = baseRect.size()
		return size


class RoundLabel(QtWidgets.QLabel):
	def __init__(self, text="", parent=None,
	             backgroundBrush=QtGui.QColor.fromRgbF(0.5, 0.5, 0.5),
	             framePen=QtGui.QColor.fromRgbF(0.5, 0.5, 0.5, 0.0),
	             textPen=QtGui.QColor.fromRgbF(0.8, 0.8, 0.8),
	             ):
		"""
		TODO: drop in EVALAK() calls all over this for dynamic colours

		TODO: there has to be a better way of changing element colours
			dynamically in qt
		"""
		super().__init__(text, parent)
		self.backgroundBrush : QtGui.QBrush = None
		self.framePen : QtGui.QPen = None
		self.textPen : QtGui.QPen = None
		self.setAutoFillBackground(True)
		self.setBackgroundBrush(backgroundBrush)
		self.setFramePen(framePen)
		self.setTextPen(textPen)

	def setBackgroundBrush(self, b:(QtGui.QColor, QtGui.QBrush, tuple)):
		if isinstance(b, (tuple, list)):
			b = QtGui.QColor.fromRgbF(*b)
		if isinstance(b, QtGui.QColor):
			b = QtGui.QBrush(b)
		assert isinstance(b, QtGui.QBrush)
		self.backgroundBrush = b
		self.update()

	def setFramePen(self, b:(QtGui.QColor, QtGui.QPen, tuple)):
		if isinstance(b, (tuple, list)):
			b = QtGui.QColor.fromRgbF(*b)
		if isinstance(b, QtGui.QColor):
			b = QtGui.QPen(b)
		assert isinstance(b, QtGui.QPen)
		self.framePen = b
		self.update()

	def setTextPen(self, b:(QtGui.QColor, QtGui.QPen, tuple)):
		if isinstance(b, (tuple, list)):
			b = QtGui.QColor.fromRgbF(*b)
		if isinstance(b, QtGui.QColor):
			b = QtGui.QPen(b)
		assert  isinstance(b, QtGui.QPen)
		self.textPen = b
		self.update()

	def paintEvent(self, arg__1:QtGui.QPaintEvent):
		painter = QtGui.QPainter(self)
		path = QtGui.QPainterPath()
		path.addRoundedRect(self.rect(), 2, 2)
		painter.fillPath(path, self.backgroundBrush)
		painter.setPen(self.framePen)
		painter.drawPath(path)
		painter.setPen(self.textPen)
		painter.drawText(
			self.rect(), self.text(), QtGui.QTextOption(QtCore.Qt.AlignCenter))



class LabelWidget(QtWidgets.QWidget):
	"""simple way of showing a label alongside
	a normal widget"""

	def __init__(self, label="", w:QtWidgets.QWidget=None, parent=None):
		super().__init__(parent)
		self.w = w
		self.setLayout(QtWidgets.QHBoxLayout(self))
		self.label = QtWidgets.QLabel(label, parent=self)

		#self.label.setAutoFillBackground(True)

		self.layout().addWidget(self.label)
		self.layout().addWidget(self.w)
		self.setContentsMargins(0, 0, 0, 0)
		self.label.setContentsMargins(0, 0, 0, 0)
		self.w.setContentsMargins(0, 0, 0, 0)

		self.setSizePolicy(expandPolicy)
		self.layout().setContentsMargins(0, 0, 0, 0)

class NodeDelegate(QtWidgets.QGraphicsItem,
                   WpCanvasElement,
                   Adaptor):
	"""node has:
	- input tree of structures, widgets and plugs
	- central widgets for name, type, settings etc
	- output tree of structures, widgets and plugs

	adaptor allows defining new delegates for specific node types?

	after checking through years-old tesserae work, aside from a few
	cool marking-menu things, most of it is straight trash
	we have everything we need, start over for the rest

	sizing :)
	height:
		shrink central widgets as much as possible
	width :
		minimum of
			- central widgets
			- top port tree
			- bottom port tree
		dependency of width goes trees -> widgets

	"""
	adaptorTypeMap = Adaptor.makeNewTypeMap()
	forTypes = (ChimaeraNode, )
	dispatchInit = True
	if T.TYPE_CHECKING:
		def scene(self)->ChimaeraScene: pass


	def __init__(self, node:ChimaeraNode,
	             parent=None,
	             ):
		QtWidgets.QGraphicsItem.__init__(self, parent)
		WpCanvasElement.__init__(self,# scene=None,
		                         obj=node)

		#self.node = node

		# not making a whole special subclass to make this call less annoying
		self.setFlag(QtWidgets.QGraphicsItem.ItemIsSelectable)
		self.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable)

		# central widget to contain views -
		# TODO: maybe make it easier to use multiple graphics widgets,
		#  map of proxy widgets and holders etc
		#  but this makes layout so much more difficult
		self.proxyW = QtWidgets.QGraphicsProxyWidget(parent=self
		                                             )
		self.w = ShrinkWrapWidget(parent=None)
		self.w.setContentsMargins(QtCore.QMargins(0, 0, 0, 0))
		self.w.setAutoFillBackground(False)
		self.w.setAttribute(QtCore.Qt.WA_TranslucentBackground)
		#self.w.setWindowOpacity(1)
		self.setWidgetResult = self.proxyW.setWidget(self.w)
		self.wLayout = QtWidgets.QVBoxLayout(self.w)
		self.w.setLayout(self.wLayout)

		shrinkPolicy = QtWidgets.QSizePolicy(
			QtWidgets.QSizePolicy.Maximum,
			QtWidgets.QSizePolicy.Maximum
		)
		expandPolicy = QtWidgets.QSizePolicy(
			QtWidgets.QSizePolicy.Expanding,
			QtWidgets.QSizePolicy.Expanding
		)

		#self.w.setSizePolicy(shrinkPolicy)
		self.w.setSizePolicy(expandPolicy)

		#TODO: later on, allow changing nodetype in-place by right-clicking
		self.typeText = QtWidgets.QGraphicsSimpleTextItem(self.node.typeName(), parent=self)
		self.typeText.setPen(QtGui.QPen(QtGui.QColor.fromRgbF(1.0, 1.0, 1.0, 0.5)))


		self.nameLine = LabelWidget(
			label="name",
			w=StringWidget(self.node.ref("@N"), #TODO: conditions
			               parent=self.w,       # don't set node to empty name, you'll mess stuff up
			               placeHolderText="",
			               ),
            parent=self.w)



		self.wLayout.addWidget(self.nameLine)
		self.nameLine.setSizePolicy(shrinkPolicy)

		log("setup icon", self.icon())
		if self.icon() is not None:
			item = QtWidgets.QGraphicsPixmapItem(self)
			item.setPixmap(QtGui.QPixmap(self.icon().pixmap(30, 30)))


		#self.syncSize()

	def icon(self)->QtGui.QIcon:
		"""return icon to show for node - by default nothing"""
		return None

	@property
	def node(self)->ChimaeraNode:
		return self.obj
	@node.setter
	def node(self, val:ChimaeraNode):
		raise NotImplementedError

	def syncSize(self):
		baseRect = self.proxyW.rect()
		expanded = baseRect.marginsAdded(QtCore.QMargins(10, 10, 10, 10))
		self.setRect(expanded)

		self.typeText.setPos(expanded.right() + 3, 3)

	def boundingRect(self)->QtCore.QRectF:
		#return QtCore.QRectF(0, 0, 50, 50)
		baseRect = self.proxyW.rect()
		expanded = baseRect.marginsAdded(QtCore.QMargins(10, 10, 10, 10))
		return expanded

	def getColour(self):
		return self.node.colour()

	def paint(self,
	          painter:QtGui.QPainter,
	          option:QtWidgets.QStyleOptionGraphicsItem,
	          widget=...):
		painter.drawRoundedRect(self.boundingRect(), 5, 5)
		brush = QtGui.QBrush(QtGui.QColor.fromRgbF(*self.getColour()).darker(300))

		path = QtGui.QPainterPath()
		path.addRoundedRect(QtCore.QRectF(self.boundingRect()), 5, 5)
		painter.fillPath(path, brush)

		pen = QtGui.QPen(QtGui.QColor.fromRgbF(*self.getColour()))
		painter.setPen(pen)
		painter.drawPath(path)









