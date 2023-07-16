
from __future__ import annotations
import typing as T

from wplib import inheritance
from wplib.object.metamagicdelegator import ClassMagicMethodMixin

"""without question overkill - 
this is just to make it explicit whenever we have a 
class that acts only as a namespace

sometimes helpful reducing the number of import elements needed

would be amazing if there were a way to get hints working for 
dynamically-extended namespaces, currently pycharm doesn't pick up
members added after definition.

Usually these are just used as bulkier enums


"""


class NamespaceElement(ClassMagicMethodMixin):
	"""base class for items to put in class-level dict
	don't actually initialise these
	"""

	@classmethod
	def clsName(cls)->str:
		return cls.__name__

	@classmethod
	def clsNameCamel(cls)->str:
		return cls.clsName()[0].lower() + cls.clsName()[1:]

	# def __str__(cls):
	# 	print("call instance str")
	# 	return cls.clsName()
	#
	#
	# def __format__(self, format_spec):
	# 	return self.clsName().__format__(format_spec)

	@classmethod
	def __class_str__(cls):
		return cls.clsName()

	@classmethod
	def __class_format__(cls, format_spec):
		return cls.clsName().__format__(format_spec)

	@classmethod
	def __class_repr__(cls):
		return "<" + cls.clsName() + ">"

class TypeNamespace(ClassMagicMethodMixin):
	"""namespace container to hold discrete elements as types
	this is like an Enum where each member can have arbitrary
	extra attributes declared"""

	# override the "_Base" member for the base class of any of
	# your namespaces
	_Base = NamespaceElement

	@classmethod
	def base(cls)->T.Type[_Base]:
		return cls._Base


	@classmethod
	def T(cls)->T.Type[base()]:
		"""class-level typing assist for signatures -
		def a(b : Namespace.T())
		"""
		return T.Type[cls.base()]

	@classmethod
	def members(cls)->dict[str, T()]:
		members = {}
		#for k, v in cls.__dict__.items():
		for k, v in inheritance.mroMergedDict(cls).items():
			if isinstance(v, type):
				if issubclass(v, cls.base()):
					members[v.clsName()] = v
		return members

	@classmethod
	def __class_getitem__(cls, item):
		if isinstance(item, str):
			found = cls.members().get(item,
			                          cls.members().get(item.lower(), None))
			return cls.members()[item]
		if isinstance(item, type):
			if issubclass(item, cls.base()):
				return item
		return cls.members()[item]

	@classmethod
	def __class_len__(cls):
		return len(cls.members())

	@classmethod
	def __class_iter__(cls):
		""" 'for i in Namespace'
		returns iterator over namespace members
		"""
		return iter(cls.members().values())

	@classmethod
	def __class_bool__(cls):
		return True

	@classmethod
	def __class_instancecheck__(cls, other)->bool:
		"""to support enum-like type checking -
		returns true if other is a type within this namespace,
		or an instance of one of those types"""
		if other in cls.members().values():
			return True
		if isinstance(other, tuple(cls.members().values())):
			return True
		return type.__instancecheck__(cls, other)

	@classmethod
	def addMember(cls, member : T.Type[NamespaceElement], force=False):
		"""add a member to the namespace"""
		assert issubclass(member, cls.base()), f"New namespace f{cls} member f{member} must be subclass of {cls.base()}"
		# do not allow overriding here unless force
		assert force or (member.clsName() not in cls.members()), f"Namespace {cls} already has member {member.clsName()} in {cls.members()}"
		# add to class dict
		setattr(cls, member.clsName(), member)



"""is there any advantage to this?
equivalent effect would be possible through dataclasses or namedtuples - 
BUT this does not rely on instantiation, which I find important
"""

if __name__ == '__main__':

	# example of a custom namespace
	class OptionNamespace(TypeNamespace):

		# define a new base class
		class _Base(TypeNamespace.base()):
			colour = (0, 0, 0)
			value = -1

		class Ready(_Base):
			colour = (0, 0, 1)

		class Success(_Base):
			colour = (0, 1, 0)

		class Failure(_Base):
			colour = (1, 0, 0)


	assert (isinstance(OptionNamespace.Ready, OptionNamespace)) # true
	assert(isinstance(OptionNamespace.Ready(), OptionNamespace)) # true
	assert not(isinstance(TypeNamespace.base(), OptionNamespace)) # false

	print(OptionNamespace.members())
	class OptionNamespaceExtended(OptionNamespace):
		class NewMember(OptionNamespace.base()):
			colour = (1, 1, 1)

	print(OptionNamespaceExtended.members())
	assert OptionNamespaceExtended["NewMember"] == OptionNamespaceExtended.NewMember
	assert OptionNamespaceExtended["Success"] == OptionNamespaceExtended.Success

