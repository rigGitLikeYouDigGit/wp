
from sys import version_info


import inspect
from weakref import WeakSet, WeakKeyDictionary
from collections import deque
from functools import partial


class Signal(object):
	""" basic signal emitter
	fired signals are added to this object's calling frame -
	if this becomes excessive, this
	also includes mode to add function calls to queue
	instead of directly firing connnected functions

	queue support not complete yet, as nothing I use needs it.
	"""
	
	queues = {"default" : deque()}
	debugConnection = False
	
	def __init__(self, name="", queue="", useQueue=False):
		""":param queue : name of queue to use, or external queue object """
		self.name = name
		self._functions = WeakSet()
		self._methods = WeakKeyDictionary()
		#self._functions = set()
		#self._methods = {}

		# separate register for references to explicitly strong functions
		# they are still placed in main weak sets above,
		# little bit spaghetti
		self._strongItemRefs = set()

		# is signal active
		self._active = True

		# event queue support
		self._useQueue = useQueue
		self._queue = queue or "default"

	def __hash__(self):
		return hash(id(self))

	def __repr__(self):
		return f"Signal({self.name})"

	def __call__(self, *args, **kwargs):
		#print("emit", self.debugLog())
		if not self._active:
			return

		queue = self.getQueue()
		# Call handler functions
		for func in list(self._functions):
			if self._useQueue:
				queue.append(partial(func, *args, **kwargs))
			else:
				func(*args, **kwargs)

		# Call handler methods
		for obj, funcs in dict(self._methods).items():
			for func in funcs:
				if self._useQueue:
					queue.append(partial(func, obj, *args, **kwargs))
				else:
					func(obj, *args, **kwargs)

	def debugLog(self):
		return str((*self._functions, dict(self._methods)))

	def activate(self):
		self._active = True
	def mute(self):
		self._active = False

	def getQueue(self, name="default", create=True):
		"""return one of the event queues attended by signal objects"""
		name = name or self._queue or "default"
		if not name in self.queues and create:
			self.queues[name] = deque()
		return self.queues[name]

	def setQueue(self, queueName):
		""" set signal to use given queue """
		self._queue = queueName

	def emit(self, *args, **kwargs):
		""" brings this object up to rough parity with qt signals """
		self(*args, **kwargs)

	def connect(self, slot):
		"""add given callable to function or method register
		flag as strong to allow local lambdas or closures"""

		if inspect.ismethod(slot):
			if self.debugConnection:
				print()
			try:
				hash(slot.__self__)
				if slot.__self__ not in self._methods:
					self._methods[slot.__self__] = WeakSet()

				self._methods[slot.__self__].add(slot.__func__)
			except TypeError:
				self._functions.add(slot)
				pass
		else:
			self._functions.add(slot)


	def disconnect(self, slot):
		if inspect.ismethod(slot):
			try:
				hash(slot.__self__)
				if slot.__self__ in self._methods:
					self._methods[slot.__self__].remove(slot.__func__)
					return
			except TypeError:
				# self._functions.remove(slot)
				pass

		if slot in self._functions:
			self._functions.remove(slot)


	def disconnectFromPool(self, pool):
		"""remove any function in the pool from signal's connections
		"""
		for fn in pool:
			self.disconnect(fn)

	def clear(self):
		self._functions.clear()
		self._methods.clear()