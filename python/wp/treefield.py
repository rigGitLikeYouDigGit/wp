
from __future__ import annotations

import typing as T
from dataclasses import dataclass

from tree import Tree, Signal

from wp.option import OptionItem, optionType, optionMapFromOptions, FilteredOptionsData, optionItemsFromOptions, optionKeyFromValue, optionFromKey, optionFilterTemplateFn, filterOptions, optionFilterFnType

"""test for a new way of building tools - using a tree structure,
addressing signals and events by strings.

Here we define a typed section for entering information at a specific
location in a tree hierarchy.


inspired partially by blueprints, partially by general despair
"""



@dataclass
class TreeFieldParams:
	"""defining auxiliary data, validation, valid options
	etc for tree field

	populate attributes you need, we'll figure it out from there
	"""
	showLabel : bool = True # MAYBE ui directions are fine here

	# options
	options: optionType = None
	optionFilterFn : optionFilterFnType = None

	# strings
	isPath : bool = False
	placeholderText : str = None # greyed out text



class TreeField(Tree):
	"""
	TreeField is a tree node that holds a value and some auxiliary
	typing data for that value.

	Will serve as a base for programmatic tool construction

	Use Params object to flag which tree branches to process
	in which way

	"""

	options = None

	@classmethod
	def defaultBranchCls(cls):
		return TreeField

	def __init__(self, name:str, value=None, uid=None,
	             params:TreeFieldParams=None):
		super(TreeField, self).__init__(name, value, uid)

		# might have to make params a property
		# for now allowing them not to be serialised
		self.params : TreeFieldParams = params or TreeFieldParams()




