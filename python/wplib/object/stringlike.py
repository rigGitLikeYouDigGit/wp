
class StringLike(object):
	""" emulates behaviour of magic methods with strings
	uses the result of this object's __str__(),
	but does not define it -
	child classes to define their own __str__()
	"""

	# overriding this in child classes doesn't
	# seem to act here
	inheritStrMethods = True
	if inheritStrMethods:
		def __getattr__(self, item):
			if self.inheritStrMethods:
				return getattr(str(self), item)

	def __repr__(self):
		return str(self)

	# string magic methods -------------
	def __add__(self, other):
		#return str.__add__(self.value, other)
		return str(self) + other
	def __radd__(self, other):
		return other + str(self)

	def __contains__(self, item):
		return str(self).__contains__(item)
	def __delslice__(self, i, j):
		return str.__delslice__(self.value, i, j)
	def __eq__(self, other):
		return str(self).__eq__(other)
	def __format__(self, format_spec):
		return str(self).__format__(format_spec)
	def __ge__(self, other):
		return str.__ge__(self.value, other)
	def __getitem__(self, item):
		return str.__getitem__(self.value, item)
	def __getslice__(self, start, stop):
		return str.__getslice__(self.value, start, stop)
	def __gt__(self, other):
		return str.__gt__(self.value, other)
	def __iadd__(self, other):
		self.value = self.value + other
		return self.value
	def __imul__(self, other):
		self.value = self.value * other
		return self.value
	def __le__(self, other):
		return str.__le__(self.value, other)
	def __len__(self):
		return len(self.value)
	def __lt__(self, other):
		return str.__lt__(self.value, other)
	def __mul__(self, other):
		return str.__mul__(self.value, other)
	def __ne__(self, other):
		return str.__ne__(self.value, other)
	def __reversed__(self):
		return reversed(self.value)
	def __rmul__(self, other):
		return str.__rmul__(self.value, other)
	def __hash__(self):
		return str.__hash__(self.value)