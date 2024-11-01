
from __future__ import annotations

import types
import typing as T

"""
- camera position and view transform
- visibility filtering
"""
import numpy as np
from collections import namedtuple
from dataclasses import dataclass

from PySide2 import QtWidgets, QtCore, QtGui
#from param import rx

from wplib import log, sequence
from wptree import Tree
from wpdex import WpDexProxy
from wplib.serial import Serialisable

from wpui.keystate import KeyState
from wpui import lib as uilib, constant as uiconstant

if T.TYPE_CHECKING:
	from .scene import WpCanvasScene
	from .element import WpCanvasItem

class WpCanvasMiniMap(QtWidgets.QWidget):
	"""give a houdini-style overview of where the viewport is, in relation
	to the rest of the scene -
	only basic rectangles for now"""

	if T.TYPE_CHECKING:
		def parent(self)->WpCanvasView: pass

	minimapDragged = QtCore.Signal(dict)

	def __init__(self, parent: WpCanvasView):
		super().__init__(parent=parent)
		self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
		self.setWindowFlag(QtCore.Qt.FramelessWindowHint)
		self.ks = KeyState()

	def scene(self)->WpCanvasScene:
		return self.parent().scene()

	def _onViewCameraChanged(self, camData:dict):
		"""fired whenever the view camera moves, updates drawing of
		minimap region"""
		self.repaint()

	def mousePressEvent(self, event):
		self.ks.mousePressed(event)

	def mouseReleaseEvent(self, event):
		self.ks.mouseReleased(event)

	def mouseMoveEvent(self, event):
		"""check if we need to move the view camera around - this will
		also update the drawing here"""
		self.ks.mouseMoved(event)
		#log("map mouse moved")
		#log("lastPressed", self.ks.lastPressed)
		if self.ks.LMB in self.ks.lastPressed:
			#log("drag minimap")
			self.minimapDragged.emit({
				"delta" : - self.ks.mouseDelta(forKey=self.ks.LMB)
			})

	def paintEvent(self, event):
		"""draw the minimap rectangle -
		this probably needs more complex treatment if we ever allow wrapping,
		infinite scene sizes, etc"""
		#log("")
		painter = QtGui.QPainter(self)
		# draw the minimap rounded, looks nicer
		path = QtGui.QPainterPath()
		path.addRoundedRect(QtCore.QRectF(self.rect()), 5, 5)
		# draw the transparent background for minimap, representing whole scene
		painter.setBrush(QtGui.QBrush(
			QtGui.QColor.fromRgbF(0.3, 0.3, 0.3, 0.3)
		))
		#painter.fillRect(self.rect(), painter.brush())
		painter.fillPath(path, painter.brush())
		# draw the white outline for where the view actually is

		minimapArr = uilib.qRectToArr(self.rect(), originSize=True)
		#log("minimapArr", minimapArr)

		sceneRect = self.scene().itemsBoundingRect() # global space
		sceneRect = self.scene().sceneRect() # global space
		#log("sceneRect", sceneRect)
		sceneArr = uilib.qRectToArr(sceneRect, originSize=False)
		#log("sceneArr", sceneArr)

		#viewMappedRect = self.parent().viewportTransform().mapRect(QtCore.QRect())
		viewMappedRect = self.parent().mapToScene(self.parent().rect()).boundingRect()
		#log("viewRect", viewMappedRect)
		viewMappedArr = uilib.qRectToArr(viewMappedRect, originSize=False)
		#log("viewArr", viewMappedArr)

		scaledArr = viewMappedArr / sceneArr[1] * minimapArr[1]
		#log("scaledArr", scaledArr)

		toDrawRect = QtCore.QRect()
		toDrawRect.setCoords(*scaledArr.ravel())
		toDrawRect = toDrawRect.intersected(self.rect().marginsRemoved(
			QtCore.QMargins(2, 2, 2, 2)
		))
		# toDrawRect.setTopLeft(toDrawRect.topLeft() + QtCore.QPoint(2, 2))
		# toDrawRect.setBottomRight(toDrawRect.bottomRight() - QtCore.QPoint(2, 2))
		#log("toDraw", toDrawRect)
		#
		# viewRatioSize = QtCore.QSizeF(viewMappedRect.size().width()) / sceneRect.size().width()
		# viewMappedRect.setSize(viewMappedRect.size() * viewRatioSize) # scaled down
		# minimapRect = self.rect() * viewMappedRect
		painter.setPen(QtGui.QPen(QtGui.QColor.fromRgbF(1.0, 1.0, 1.0, 0.5)))
		painter.drawRoundRect(toDrawRect, 2, 2)


class ViewEventFilter(QtCore.QObject):

	def __init__(self, parent=None):
		super().__init__(parent)
		self._processingTab = False

	def eventFilter(self, watched:WpCanvasView, event):
		#log("eventFilter", event)

		if isinstance(event, QtGui.QKeyEvent):
			if event.key() in (QtCore.Qt.Key_Tab, QtCore.Qt.Key_Backtab):
				#log("no tab for you")
				if self._processingTab: return True # prevent feedback
				self._processingTab = True
				newEvent = QtGui.QKeyEvent(event.type(), event.key(), event.modifiers(),
					                event.nativeScanCode(), event.nativeVirtualKey(),
					                event.nativeModifiers(), event.text(),
					                event.isAutoRepeat(), event.count())
				watched.keyPressEvent(newEvent)
				self._processingTab = False
				return True
		if isinstance(event, QtGui.QHoverEvent):
			"""update the ks mouse history """
			watched.ks.mouseMoved(event)
		return super().eventFilter(watched, event)

class WpCanvasView(QtWidgets.QGraphicsView):
	"""add some conveniences to serialise camera positions
	surely selected items should be per-viewport? not per-scene?
	well per-scene is how qt handles it and for now we're keeping it

	TODO: camera momentum?

	TODO: context menu / radial menu setup

	TODO: E_V_E_M_T_S
		i forgot how fun this is - events pass through this view before they hit
		embedded widgets, so we need a way of checking if a graphics widget is
		under the cursor to receive focus, if it's already got focus, etc
	"""

	if T.TYPE_CHECKING:
		def scene(self)->WpCanvasScene: pass

	@dataclass
	class KeySlot:
		"""easier declaration of hotkey-triggered events"""
		fn : T.Callable[[WpCanvasView], (QtWidgets.QWidget, T.Any)]
		keys : tuple[QtCore.Qt.Key] = ()
		closeWidgetOnFocusOut : bool = True

	cameraChanged = QtCore.Signal(dict)

	def __init__(self,scene:WpCanvasScene, parent=None,
	             ):
		super().__init__(parent)
		self.setScene(scene)

		self.ks = KeyState()
		self.filter = ViewEventFilter(parent=self)
		self.installEventFilter(self.filter)
		#self.setMouseTracking(True)


		self.setTransformationAnchor(self.NoAnchor) # ????
		self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
		self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

		# self.setRenderHints(QtGui.QPainter.Antialiasing# | QtGui.QPainter.HighQualityAntialiasing
		#                     )

		#TODO: rewrite this with the model stuff
		self.data = {
			"position" : [0, 0],
			"zoom" : 1.0,
			"selectionMode" : "rect" # or "lasso"
		}

		# selection tracking
		self._selPath : list[T.Sequence[int]] = []
		self._selGeo : (QtGui.QPainterPath, QtCore.QRect) = None

		# minimap
		self.minimap = WpCanvasMiniMap(parent=self)
		self.minimap.minimapDragged.connect(self._onMiniMapDragged)
		self.cameraChanged.connect(self.minimap._onViewCameraChanged)

		# set up functions to fire when specific keys are pressed
		# if these functions return a widget, widget will be shown and
		# given modal focus
		self.keySlotMap : dict[tuple[QtCore.Qt.Key],
			WpCanvasView.KeySlot] = {}

		# set init camera pos
		self.moveCamera([0, 0], relative=False)
		self.setFocusPolicy(QtCore.Qt.StrongFocus)

	# region focus

	# def focusNextPrevChild(self, next):
	# 	"""this holds the focus on this widget, prevents Tab from moving it
	# 	FOR NOW this is ok, inkeeping with Maya, Houdini node editor conventions
	#
	# 	HOWEVER, later allow separate mode for full Vim key master focus switching -
	# 		maybe that needs some extra treatment
	# 	"""
	# 	return True
	# def focusNextChild(self):
	# 	return True
	# def nextInFocusChain(self):
	# 	return self
	#
	# def focusOutEvent(self, event:QtGui.QFocusEvent):
	# 	log("focusOut event", event.reason() in (QtCore.Qt.FocusReason.TabFocusReason,
	# 	                                         QtCore.Qt.FocusReason.BacktabFocusReason))

	# endregion

	def addKeyPressSlot(self,
	                    slot: (T.Callable[[WpCanvasView], (QtWidgets.QWidget, T.Any)],
	                           WpCanvasView.KeySlot),
	                    keys:tuple[QtCore.Qt.Key]=(),

	                    ):
		"""set a function to fire when the set keys are pressed
		TODO: could probably spin this out into some kind of component -
		"""
		if not isinstance(slot, WpCanvasView.KeySlot):
			slot = WpCanvasView.KeySlot(slot, keys=keys)
		self.keySlotMap[tuple(slot.keys)] = slot

	def _getMousePosForObjCreation(self)->QtCore.QPoint:
		return self.ks.mousePositions[0] \
			if self.ks.mousePositions else self.rect().center()

	def checkFireKeySlots(self, event:QtGui.QKeyEvent):
		"""check if any key functions should be fired -
		if so, activate functions, then show the widget if returned
		and give it focus

		Q : Why not just use QT hotkey actions?
		A : they mess up the control flow of the whole program, even if you block events
			the hotkeys can "leak" up if you declare them higher
		"""
		# this is some of the dumbest code I've ever written
		for keys, slot in self.keySlotMap.items():

			matches = True
			for i in keys:
				if i in self.ks.keyPressedMap.keys():
					if not self.ks.keyPressedMap[i]:
						matches = False
						break
				else:
					if i != event.key():
						matches = False
						break
			if not matches: continue
			# code equivalent of shovelling mud

			result = slot.fn(self)
			if isinstance(result, QtWidgets.QWidget): # show the returned widget
				# unsure if we should enforce it being a parent of this widget
				result.setEnabled(True)
				result.show()
				result.setFocus()
				# move it to the last shown mouse position
				pos = self._getMousePosForObjCreation()
				pos = self.mapTo(result.parent(), pos)
				result.move(pos)
				result.setFocus()

				# if we say to close after losing focus, set up that as a patch
				if slot.closeWidgetOnFocusOut:
					def _patchFocusEvent(focusEvent:QtGui.QFocusEvent):
						log("run slot focus out event")
						type(result).focusOutEvent(result, focusEvent)
						result.hide(); result.setEnabled(False)
						self.setFocus()
					result.focusOutEvent = _patchFocusEvent


	def keyPressEvent(self, event):
		"""
		TODO: for some reason tab events trigger this 3 times at once -
			fix this sometime, for now push through it
		"""
		#log("key press", event.key(), uiconstant.keyDict[event.key()])

		self.ks.keyPressed(event)
		self.checkFireKeySlots(event)
		super().keyPressEvent(event)


	def keyReleaseEvent(self, event):
		self.ks.keyReleased(event)


	def selection(self)->list[QtWidgets.QGraphicsItem]:
		"""seems weird that the view can't access this natively"""
		return self.scene().selectedItems()
	def selectionMode(self)->str:
		#TODO: FIX
		return self.data["selectionMode"]
	def setSelectionMode(self, s:str):
		assert s in ("rect", "lasso")
		self.data["selectionMode"] = s

	def resizeEvent(self, event):
		super().resizeEvent(event)

		# want the map to start at (0.9, 0.9) normalised
		widthStep = self.width() / 10.0
		heightStep = self.height() / 10.0
		self.minimap.setGeometry(widthStep * 9, heightStep * 9,
		                         widthStep * 0.9, heightStep * 0.9)

	def moveCamera(self, pos:T.Sequence[float], relative=True, delay=None):
		"""overall method to move camera by relative or absolute scene coords"""

		arr = uilib.qTransformToArr(self.viewportTransform() )
		if isinstance(pos, (QtCore.QPoint, QtCore.QPointF)):
			pos = np.array(pos.toTuple())
		#log("arr", arr)
		#log(self.viewportTransform(), tuple(self.viewportTransform()))
		thisPos = (arr[0, 2], arr[1, 2])
		if not relative:

			pos = np.array(pos) - thisPos
		self.translate(*pos)

		self.cameraChanged.emit({"old" : thisPos,
		                         "new" : pos})


	def mousePressEvent(self, event):
		self.ks.mousePressed(event)
		scenePressPos = self.mapToScene( event.pos())

		if event.button() == self.ks.lmbKey:
			items = self.scene().itemAt(scenePressPos, QtGui.QTransform())
			if items:
				items = sequence.toSeq(items)
				mode = "replace"
				if self.ks.SHIFT and self.ks.CTRL: mode = "add"
				elif self.ks.SHIFT: mode = "toggle"
				elif self.ks.CTRL : mode = "remove"

				self.scene().select(items, mode=mode)
				#return
		super().mousePressEvent(event)
		#log("end selection", self.scene().selectedItems())

	def _onMiniMapDragged(self, data):
		self.moveCamera(data["delta"], relative=True)


	def mouseReleaseEvent(self, event):
		self.ks.mouseReleased(event)
		super().mouseReleaseEvent(event)

	def _updateIncludedSelectionItems(self):
		"""check any """

	def _updateSelectionDrawing(self):
		if self.selectionMode() == "lasso": # draw a path and fill in included area
			path = QtGui.QPainterPath(self._selPath[0])
			for i in self._selPath[1:]:
				path.lineTo(i)
			# close back to start
			path.lineTo(self._selPath[0])
			self._selGeo = path
		else:
			rect = QtCore.QRect(self._selPath[0], self._selPath[1])


	def _updateSelectionPositions(self, event:QtGui.QMoveEvent):
		if self.selectionMode() == "lasso" :
			self._selPath.append(event.pos())
		else:
			self._selPath[0] = event.pos()
		self._updateSelectionGeo()
		self._updateIncludedSelectionItems()

	def _clearSelectionData(self):
		self._selPath = []
		self._selGeo = None

	def mouseMoveEvent(self, event):
		"""if alt + lmb is held, move the camera"""
		self.ks.mouseMoved(event)
		if self.ks.ALT and self.ks.MMB:
			self.moveCamera(self.ks.mouseDelta(), relative=True)
			return # moving the camera should override everything?

		if self.ks.LMB:
			if self.ks.SHIFT or self.ks.CTRL: # selection modifiers:
				self._updateSelectionPositions(event)
				return
			if self.scene().selectedItems():
				# we send the drag event to scene
				self.scene().itemsDragged(items=self.scene().selectedItems(),
				                          delta=self.ks.mouseDelta(forKey=self.ks.LMB))
		super().mouseMoveEvent(event)



	# def dragMoveEvent(self, event:QtGui.QDragMoveEvent):
	#
	# 	self.ks.mouseMoved(event)





