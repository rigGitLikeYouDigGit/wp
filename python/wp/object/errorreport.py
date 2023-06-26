
from __future__ import annotations
import typing as T

from traceback import format_exc

"""more rich error class, containing traceback and
a more descriptive message to show user"""

class ErrorReport:

	def __init__(self, error:Exception, message:str=None):
		self.error = error
		self.message = message or str(error)
		self.traceback = format_exc()
