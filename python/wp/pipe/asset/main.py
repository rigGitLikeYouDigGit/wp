
from __future__ import annotations

import glob
import typing as T

from pathlib import Path, PurePath
import orjson

from wplib import log, string as libstr
from wplib.object import UidElement, SmartFolder, DiskDescriptor
from wplib.pathable import Pathable
from wplib.sequence import toSeq, flatten

from wp.constant import getAssetRoot, WP_ROOT


"""main asset object, to be integrated with chimaera
we go back to the original folder-based idea -
if a folder contains a file named "_asset.json", it's an asset

consider ASSET vs RESOURCE - 
an asset is usually a concrete object like a person or a ford focus that is
used in multiple places and sequences across a project
a RESOURCE can be anything at all in the studio, but should be accessible
retrievable by exactly the same path system

"""

class Show(Pathable):
	"""
	TODO:
	 - add proper support for show-level rules here


	 """

	def __init__(self, name, parent:AssetRoot):
		super().__init__(obj=self, parent=parent,
		                 name=name)
		#self.prefix = prefix
		self._diskPath = parent.diskPath() / self.name

	def diskPath(self):
		return Path(self._diskPath)

	@classmethod
	def get(cls, *args, showDir:Path=None, name=""):
		if args:
			if isinstance(args[0], Show):
				return args[0]
			if isinstance(args[0], str):
				name = args[0]
			if isinstance(args[0], Path):
				showDir = args[0]
		if showDir:
			data = orjson.loads( (showDir / "_show.json").read_text() )
			return Show(name=showDir.name,
			            prefix=data["prefix"]
			            )
		if name:
			return showsDict()[name]
		raise RuntimeError("no options passed to Show.get()")

	def configDict(self)->dict:
		"""maybe there's a good way to automate this"""
		return {"prefix" : self.prefix}

	def makeNewShow(self):
		showDir = WP_ROOT / self.name
		if showDir.is_dir():
			raise RuntimeError("SHOW {} ALREADY EXISTS, STOPPING IMMEDIATELY".format(self.name))
		showDir.mkdir(parents=True, exist_ok=True)
		(showDir / "_show.json").write_text(orjson.dumps(self.configDict()))
		#return

	@classmethod
	def isShowDir(cls, path:Path):
		return ( path / "_show.json" ).exists()

	@staticmethod
	def showsDict()->dict[str, Show]:
		return root().branchMap()
	@staticmethod
	def shows()->list[Show]:
		return list(Show.showsDict().values())

	@classmethod
	def fromDiskPath(cls, path:Path)->Show:
		"""from path like 'F:\\wp\\wpcore\\asset\\character\\sourceHuman\\_asset.json'
		return a show that matches its root"""

		# get show
		d = Show.showsDict()
		show = None
		for token in Path(path).parts:
			#log(token, token in d)
			if token in d:
				showKey = token
				show = d[showKey]
				break
		return show

	@classmethod
	def fromPath(cls, path):
		"""could be ANY format of path - find some way
		to get to the show level, else error.

		maybe there should be some unified separate way of resolving
		paths like this
		maybe we should just use USD
		"""
		path = toAssetPath(path)

		try:
			return cls.showsDict()[path[0]]
		except KeyError:
			raise KeyError(f"no show found for path {path}\n in show map\n{cls.showsDict()}")

	def _buildBranchMap(self) ->dict[keyT, Pathable]:
		"""look at top-level folders under this show,
		allowing pathing into rich assets or the medial
		AssetFolder objects
		"""
		children = {}
		for childDir in self.diskPath().glob("*"):
			#print("childDir", childDir)
			if not childDir.is_dir(): continue
			child = self._buildChildPathable(
				childDir, name=childDir.name)
			if child is None: continue
			children[childDir.name] = child
		return children

	def _buildChildPathable(self, obj:Path, name:keyT):
		"""we pass a Path object as obj, check if that should be a full
		Asset wrapper or not"""
		if Asset.isAssetDir(obj):
			return Asset(name, parent=self)
		elif obj.is_dir():
			return StepDir(parent=self, name=name)
		else:
			return None


# def showsDict()->dict[str, Show]:
# 	"""check any top-level folders having a "_show.json" file
# 	"""
# 	result = {}
# 	for childDir in WP_ROOT.iterdir():
# 		if not childDir.is_dir():
# 			continue
# 		if not (childDir / "_show.json").exists():
# 			continue
# 		result[childDir.name] = Show.get(childDir)
# 	return result


class StepDir(Pathable):
	"""represent an empty category folder for assets -
	it's a shame to need these but otherwise the asset
	system seems decently intuitive

	TODO: overhaul file tree pathable stuff
	 - fn to select specifc file wrapper for given file, or given dir
	 - overall subclass of pathable, which is then inherited by specific file wrappers
	 - uniform data() interface to read file, cache read data, update when changes, etc
	 - cache diskPath once on init
	 - LATER, find some way to integrate this with the "expected" subtree descriptors, basically a way to use python classes as schemas to set out consistent folder formats
	"""
	def __init__(self, parent, name):
		super().__init__(obj=self, parent=parent, name=name)
		self._diskPath = self.parent.diskPath() / self.name

	def diskPath(self)->Path:
		return self._diskPath

	def _buildBranchMap(self) ->dict[keyT, Pathable]:
		"""look at top-level folders under this show,
		allowing pathing into rich assets or the medial
		AssetFolder objects
		"""
		children = {}
		for childDir in self.diskPath().glob("*"):
			#log("childDir", childDir)
			if not childDir.is_dir(): continue
			child = self._buildChildPathable(
				childDir, name=childDir.name)
			if child is None: continue
			children[childDir.name] = child
		return children

	def _buildChildPathable(self, obj:Path, name:keyT):
		"""we pass a Path object as obj, check if that should be a full
		Asset wrapper or not"""
		if Asset.isAssetDir(obj):
			return Asset(name, parent=self)
		elif obj.is_dir():
			return StepDir(parent=self, name=name)
		else:
			return None


defaultAssetData = {
	"tags" : {},
	"created" : None,
	"version" : {"latest" : 0},
	#"uid" : None
}

class AssetFolder(SmartFolder):
	inDir = DiskDescriptor("_in", create=False)
	outDir = DiskDescriptor("_out", create=True)
	vcsDir = DiskDescriptor("_vcs", create=True)
	workDir = DiskDescriptor("_work", create=True)
	assetData = DiskDescriptor("_asset.json", create=True,
	                           default=defaultAssetData)

	createMissingFilesOnInit = False


class Asset(Pathable):
	"""this may also be used for components

	path contains show for now
	"""

	parent : StepDir

	@classmethod
	def tokensFromDirPath(cls, path):
		return Path(str(Path(path)).split(str(WP_ROOT))[-1]).parts[1:]

	def __init__(self, name, parent=None):
		"""parent only used transiently to prepend tokens"""
		#self._path = path
		super().__init__(obj=self, parent=parent, name=name)

		self._diskPath = self.parent.diskPath() / self.name

		self._folder = None
		self._data = None

	def exists(self)->bool:
		return self.diskPath().exists()


	def showName(self)->str:
		return self.tokens[0]

	def show(self)->Show:
		return Show.get(name=self.showName())

	def smartFolder(self)->AssetFolder:
		if self._folder is None:
			self._folder = AssetFolder(path=self.diskPath())
		return self._folder

	def diskPath(self)->Path:
		"""feels like muddying, maybe asset shouldn't know its
		direct placement on disk, should go through bank to map
		a show path to real disk.

		then again the folders power everything at the moment"""
		return self._diskPath
		# tokens = self.tokens
		# if tokens[0] == self.show().name: tokens = tokens[1:]
		# return self.show().path() / "/".join(tokens)

	# def path(self)->str:
	# 	return "/".join(self.tokens)

	@classmethod
	def isAssetDir(cls, path:Path):
		return ( path / "_asset.json" ).exists()

	# def parent(self)->(None, Asset):
	# 	if self.isAssetDir(self.diskPath().parent):
	# 		return Asset(self.tokens[:-1])
	# 	return None

	def create(self):
		"""set up all missing folders and files for a new asset"""
		self.smartFolder().createMissingFiles()

	# store any metadata about asset like tags, uid, etc
	# TODO: do we really want to mess around with live saving / loading to disk when dict changes
	def data(self)->dict:
		if self._data is None:
			self._data = orjson.loads(self.smartFolder().assetData.read_text())
		return self._data
	def saveData(self, data=None):
		self.smartFolder().assetData.write_text(orjson.dumps(data or self._data))

	def tags(self)->dict:
		return self.data()["tags"]

	@classmethod
	def fromDiskPath(cls, path:Path):
		"""from path like 'F:\\wp\\wpcore\\asset\\character\\sourceHuman\\_asset.json'
		return a new asset properly parented to its show and top dirs

		:raises KeyError
		"""

		# get show
		show = Show.fromDiskPath(path)
		assert show, f"no show found for asset disk path {path}"
		tokens = Path(path).parts
		assetTokens = tokens[tokens.index(show.name) + 1:]

		assetTokens = [i for i in assetTokens if not "." in i and not i.startswith("_")]
		#log(assetTokens)
		return show.access(show, assetTokens, one=True)

	@classmethod
	def fromPath(cls, path)->Asset:
		#log("init path", path)
		path = toAssetPath(path)
		#log("found path", path)
		show = Show.fromPath(path)
		#log("show", show, "path", path)
		return show.access(show, path=path[1:])

def toAssetPath(path)->list[str]:
	"""filter given path to start with a show token, strip
	out any file stuff, etc

	this won't work if we allow complex path expressions,
	might need some kind of RE to only strip top level
	"""
	if isinstance(path, str):
		path = path.replace(str(WP_ROOT), "")
		path = list(filter( None, libstr.multiSplit(path, [" ", ",", "/", "\\"],
		                         preserveSepChars=False
		                         )))
	return path

def topLevelAssetFiles(show:Show):
	"""list all paths for top-level assets in show - maybe should
	delegate to a show-based config but for now we chill.
	look for paths matching SHOW / asset / character / human
	"""
	searchDir = show.diskPath() / "*" / "*" / "*" / "_asset.json"
	return glob.glob(str(searchDir))

class AssetRoot(Pathable):
	"""simplifies all kinds of logic to have a persistent root node
	holding shows as first children"""

	def __init__(self):
		super().__init__(obj=self, name="wp")
		self._diskPath = WP_ROOT

	def diskPath(self)->Path:
		return self._diskPath

	def _buildBranchMap(self) ->dict[keyT, Pathable]:
		"""look at top-level folders under this show,
		allowing pathing into rich assets or the medial
		AssetFolder objects
		"""
		children = {}
		for childDir in self.diskPath().glob("*"):
			#log("childDir", childDir)
			if not childDir.is_dir(): continue
			child = self._buildChildPathable(
				childDir, name=childDir.name)
			if child is None: continue
			children[childDir.name] = child
		return children

	def _buildChildPathable(self, obj:Path, name:keyT):
		"""we pass a Path object as obj, check if that should be a full
		Asset wrapper or not"""
		if Show.isShowDir(obj):
			return Show(name=obj.parts[-1],
			            parent=self,
			            )

_root = None
def root()->AssetRoot:
	global _root
	if _root is None:
		_root = AssetRoot()
	return _root

if __name__ == '__main__':
	# for show in Show.shows():
	# 	print(show, topLevelAssetFiles(show))
	# 	show._buildBranchMap()
	p = "F:\\wp\\wpcore\\asset\\character\\sourceHuman\\_asset.json"
	a = Asset.fromDiskPath(p)
	print("retrieved asset", a)
	# are assets persistent?
	a2 = Asset.fromDiskPath(p)
	log("identical object?", a is a2, a == a2)
	# do we want them to be identical? do we care?

	# get from normal path
	a3 = Asset.fromPath("wpcore/asset/character/sourceHuman")
	log(a3)





