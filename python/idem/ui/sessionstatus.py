from __future__ import annotations
import types, typing as T
import pprint
from wplib import log
import numpy as np
from PySide2 import QtCore, QtGui, QtWidgets

from wpui.widget import Status
from wpdex import *
from wpdex.ui import AtomicWidgetOld

class CustomProperty(QtCore.QObject):

	# you can skip this with QVariantAnimation
	# but this way is more general for python objects
	valueChanged = QtCore.Signal(float)
	@classmethod
	def T(cls)->type:
		return float
	def __init__(self, name:str, parent=None, value=0.0):
		super().__init__(parent)
		self.setObjectName(name)
		self._value = value

	@QtCore.Property(float)
	def value(self):
		return self._value
	@value.setter
	def value(self, value):
		self._value = value
		#log("value changed")
		self.valueChanged.emit(self._value)



class Blinker(QtCore.QObject):

	def __init__(self,
	             propertyName:str,
	             propertyCls=CustomProperty,
	             parent=None,
				keys=(1.0, 0.0),
	             curve=QtCore.QEasingCurve.OutCurve,
				decayLength=1.0
	             ):
		"""why yes dear reader, I assure you
		a proper blinking indicator
		is essential to the creation of rigs for animation

		small helper to allow just firing a single pulse,
		without creating a new propertyAnimation instance
		in qt each time

		absolutely NO BUSINESS LOGIC IN THIS AT ALL

		might be excessive to make this a QObject
		"""
		super().__init__(parent=parent)
		self.value = CustomProperty("value",
		                               parent=self,
		                               value=keys[0])
		self.decayLength = decayLength

		self.anim = QtCore.QPropertyAnimation(
			#self, QtCore.QByteArray(b"value"), self
			self.value, b"value", self
		)
		space = np.linspace(0.0, 1.0, len(keys))
		for i, t in enumerate(space):
			self.anim.setKeyValueAt(t, keys[i])
		self.anim.setDuration(int(decayLength * 1000))
		if curve is not None:
			self.anim.setEasingCurve(curve)
		self.valueChanged = self.value.valueChanged

	def blink(self):
		"""start or restart the animation"""
		# if self.anim.state() == self.anim.State.Running:
		# 	self.anim.stop()
		self.anim.setCurrentTime(0)
		self.anim.start(policy=QtCore.QAbstractAnimation.DeletionPolicy.KeepWhenStopped)

class BlinkLight(AtomicWidgetOld, QtWidgets.QWidget):
	"""return a round widget that blinks a solid colour -

	TODO:
		MAYBE combine this with a timer to tick things, but
		that feels like inversion to me
		this should only ever be a display of activity, not a driver
	"""
	def __init__(self, parent=None,
	             value:Status.T()=Status.Neutral):
		QtWidgets.QWidget.__init__(self, parent)
		AtomicWidgetOld.__init__(self, value=value)
		self.blinker = Blinker(propertyName="brightness",
		                       )
		self.brightness = 0.0
		self.solid = None
		self.blinker.valueChanged.connect(lambda f : self.setBrightness(f))
		self.rxValue().rx.watch(lambda *a : self.repaint(), onlychanged=False)
		self.setAutoFillBackground(False)
		self.setFixedSize(20, 20)
		self.setContentsMargins(0, 0, 0, 0)



	def setBrightness(self, f):
		self.brightness = f
		self.repaint()

	def blink(self): # a bit cringe to have passthrough methods like this -
		# maybe this should inherit from blinker directly? idk
		self.blinker.blink()
		#log("blinked")

	def setSolid(self, state=None):
		self.solid = state
		self.repaint()

	def paintEvent(self, event:QtGui.QPaintEvent):
		#print("paintevent")
		painter = QtGui.QPainter(self)
		painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
		painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform, True)


		# fill
		statusColour = QtGui.QColor.fromRgbF(*self.value().colour)
		blinkColour = statusColour.darker(300 - 200 * self.brightness)
		if self.solid is not None:
			if self.solid:
				blinkColour = statusColour
			else:
				blinkColour = statusColour.darker(300)
		grad = QtGui.QRadialGradient(self.rect().center(),
		                             self.rect().width() / 2.0)
		grad.setSpread(grad.Spread.PadSpread)
		grad.setFocalPoint(self.rect().center() * 1.2)
		grad.setColorAt(0.0, blinkColour.lighter(150))
		grad.setColorAt(1.0, blinkColour.dark(150))
		brush = QtGui.QBrush(grad)

		# absolutely heartbreaking - the gradient doesn't look as nice as block colour at range
		#brush = QtGui.QBrush(statusColour)
		path = QtGui.QPainterPath()
		path.addEllipse(self.rect())
		painter.setBrush(brush)
		painter.fillPath(path, brush)

		# outline
		# outlinePen = QtGui.QPen(QtGui.QColor.fromRgbF(0.5, 0.5, 0.5))
		# painter.setPen(outlinePen)
		# painter.drawEllipse(self.rect())


class SessionDisplayWidget(QtWidgets.QWidget):
	"""overall tab to display live dcc sessions -
	on left, logo and session name
	on right, 3 lights - status, outgoing, incoming

	"""

if __name__ == '__main__':

	app = QtWidgets.QApplication()

	w = QtWidgets.QWidget()
	l = QtWidgets.QVBoxLayout()
	w.setLayout(l)
	light = BlinkLight(parent=w,
	                   value=Status.Outgoing)
	l.addWidget(light)
	l.setContentsMargins(0, 0, 0, 0)
	timer = QtCore.QTimer(parent=w)

	timer.setInterval(1000)
	timer.timeout.connect(lambda *a : light.blink())
	timer.start()
	w.show()
	app.exec_()









