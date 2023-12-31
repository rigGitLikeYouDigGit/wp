from __future__ import annotations
import typing as T

from PySide2 import QtWidgets, QtCore

from wp.constant import Status
from wp.object import PostInitBase, postInitWrap
from wp.ui.widget.base import WpWidgetBase
from wplib.validation import Rule, RuleSet, ValidationError

class StringTranslator:
	"""in future we could use this to pass rich path objects
	back and forth from ui -
	Probably better to defer to the calling code in question though,
	this is a bit obscure"""

	@classmethod
	def fromUiString(cls, uiString:str)->object:
		"""translate from ui string to internal string"""
		return uiString

	


@postInitWrap
class StringWidget(QtWidgets.QWidget, PostInitBase, WpWidgetBase):
	"""test for more open / versatile string entry widget.
	Incorporates validation checking on user input.
	Later provide support for searching, completion, etc.
	"""

	textChanged = QtCore.Signal(str)

	def __init__(self, parent=None):
		super(StringWidget, self).__init__(parent)
		WpWidgetBase.__init__(self)

		self._textValue = "" # actual value of widget
		self._ruleSet : RuleSet = None # validation ruleset
		self.lineEdit = QtWidgets.QLineEdit(self)
		self._isEditing = False # whether user is currently editing widget

	def __postInit__(self):
		"""layout and connection functions are run after any subclasses
		have run their __init__ functions - otherwise in overriding
		these methods, you end up trying to connect widgets that don't exist yet
		"""
		self._makeLayout()
		self._makeConnections()
		pass

	def _makeLayout(self):
		layout = QtWidgets.QHBoxLayout(self)
		layout.setContentsMargins(0,0,0,0)
		layout.setSpacing(0)
		layout.addWidget(self.lineEdit)
		self.setLayout(layout)

	def _makeConnections(self):
		self.lineEdit.textChanged.connect(self._onUserInput)
		self.textChanged.connect(self._onValueChanged)
		#self.lineEdit.
		self.lineEdit.editingFinished.connect(self._onWidgetEditingFinished)


	def setValidationRuleSet(self, ruleset:RuleSet):
		"""set the validation ruleset for this widget"""
		self._ruleSet = ruleset

	def validationRuleSet(self)->RuleSet:
		"""return the current validation ruleset"""
		return self._ruleSet

	def value(self)->str:
		"""return the current text value of the widget"""
		return self._textValue

	def setValue(self, text:str, emit=True):
		"""set the text value of the widget - does not check against validation ruleset
		also does not propagate if text is the same as current value"""
		oldValue = self._textValue
		if oldValue == text:
			return
		self._textValue = text
		if not self.isEditing():
			self._setWidgetText(str(text))
		if emit:
			self.textChanged.emit(text)

	def widgetText(self)->str:
		"""return the current text value of the widget"""
		return self.lineEdit.text()

	def checkWidgetText(self)->bool:
		"""check the current text value of the widget
		against the current validation ruleset"""
		return self.validationRuleSet().checkInput(self.widgetText())

	def _setWidgetText(self, text:str):
		"""set the text value of the widget - does not check against validation ruleset.
		Also prevent text changed signal from firing"""
		self.lineEdit.blockSignals(True)
		self.lineEdit.setText(text)
		self.lineEdit.blockSignals(False)

	def _setVisualState(self, state:Status.T()):
		"""set the visual state of the widget based on validation result"""
		if state == Status.Success:
			self.lineEdit.setStyleSheet("")
		elif state == Status.Error:
			self.lineEdit.setStyleSheet("background-color: red; color: white")


	def _onUserInput(self):
		"""check any text input to widget against validation ruleset -
		if accepted, update widget value"""
		#print("user input", self.widgetText())
		if self.validationRuleSet() is not None:
			result = self.checkWidgetText()
			#print("result", result)
			if not result:
				self._setVisualState(Status.Error)
				return
			self._setVisualState(Status.Success)
		self.setValue(self.widgetText(), emit=True)

	def _onWidgetEditingBegan(self, *args, **kwargs):
		self._isEditing = True

	def _onWidgetEditingFinished(self):
		"""coerce displayed text to this widget's value -
		if widget is left with invalid text, overwrite with last valid value"""
		self._isEditing = False
		self._setVisualState(Status.Success)
		self._setWidgetText(self.value())

	def isEditing(self):
		#print("editing?", self.lineEdit.hasFocus(), self.lineEdit.isActiveWindow())
		return self.lineEdit.hasFocus() and self.lineEdit.isActiveWindow()

	def _onValueChanged(self, text:str):
		"""override for any actions to occur when text value changes"""


if __name__ == '__main__':

	import sys, re
	from PySide2.QtWidgets import QApplication as QApp

	class NodeNameValidCharactersRule(Rule):
		"""check that input does not contain invalid characters"""
		invalidPattern = re.compile(r"[^a-zA-Z0-9_|:]")

		def checkInput(self, data: str)->bool:

			if self.invalidPattern.findall(data):
				raise ValidationError(f"Node name {data} contains invalid characters:  {self.invalidPattern.findall(data)}")
			return True

		def getSuggestedValue(self, data) -> T.Any:
			"""replace invalid characters with underscores,
			as Maya does"""
			return self.invalidPattern.sub("_", data)


	nodeNameRuleSet = RuleSet(
		[NodeNameValidCharactersRule()]
	)

	app = QApp(sys.argv)

	widget = StringWidget()
	widget.show()

	widget.setValidationRuleSet(nodeNameRuleSet)

	app.exec_()

