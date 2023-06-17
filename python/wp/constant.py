
from __future__ import annotations
"""constants across all of wp"""

import typing as T

from pathlib import Path

from tree.lib.object import TypeNamespace


"""
all files on disk should have consistent orientation and scale

SCALE : 1 unit = 1 decimetre
ORIENTATION : X left, Y up, Z forward



"""


# path constants
WP_ROOT = Path(__file__).parent.parent.parent.parent
TEMPEST_ROOT = WP_ROOT / "tempest"
# work out how to get this from the environment when we need different projects lol
ASSET_ROOT = TEMPEST_ROOT / "asset"

TEST_TEMPEST_ROOT = WP_ROOT / "test_tempest"
# work out how to get this from the environment when we need different projects lol
TEST_ASSET_ROOT = TEST_TEMPEST_ROOT / "asset"

TESTING = False

def setTesting(testing:bool):
	"""sets the testing flag"""
	global TESTING
	TESTING = testing
	if testing:
		print("TESTING = TRUE")
		print("Now targeting assets in test directory")
		print("")

	else:
		print("TESTING = FALSE")
		print("# NOW AFFECTING PRODUCTION ASSETS # ")
		print("")

def getAssetRoot()->Path:
	"""returns the asset root path"""
	if TESTING:
		return TEST_ASSET_ROOT
	return ASSET_ROOT

print("wp init")
print("ROOT_PATH", WP_ROOT)
print("ASSET_ROOT_PATH", ASSET_ROOT)

class CurrentAssetProject(TypeNamespace):

	class _Base(TypeNamespace.base()):
		"""base class for asset project"""
		root : Path = Path("NONE")

	class Test(_Base):
		"""test asset project"""
		root = TEST_ASSET_ROOT

	class Tempest(_Base):
		"""tempest asset project"""
		root = ASSET_ROOT

