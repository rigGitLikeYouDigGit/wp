

from __future__ import annotations
import typing as T

from PySide2 import QtCore, QtWidgets, QtGui

from wplib import Sentinel, log
from wpdex import *
from .instance import IdemWidget, IdemSession
"""
each package can define an "onStartup" function,
fully immersed in dcc domain code, and idem calls it
once dcc is running


"""

class Window(QtWidgets.QWidget):
	"""
	instead of multiple sessions in tabs,
	maybe it's less complicated to
	just open multiple idem windows
	"""

	def __init__(self, parent=None):
		super().__init__(parent)
		self.setObjectName("idem")
		self.setWindowTitle("idem")

		# # list of active sessions
		self.sessions = [IdemSession.create(name="idem")]
		self.w = IdemWidget(self.sessions[0], parent=self)

		l = QtWidgets.QVBoxLayout(self)
		self.setLayout(l)
		l.addWidget(self.w)
		self.setContentsMargins(0, 0, 0, 0)


	@classmethod
	def launch(cls):
		app = QtWidgets.QApplication()
		from wpui.theme.dark import applyStyle
		#app.setStyleSheet(STYLE_SHEET)
		applyStyle(app)
		w = cls()
		w.show()

		#w.w.graphW.scene.graph().createNode("i:MayaSessionNode")
		#
		# def _onFocusChanged(*args):
		# 	log("onFocusChanged", args)
		# app.focusChanged.connect(_onFocusChanged)

		app.exec_()

