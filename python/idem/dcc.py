
from __future__ import annotations
import typing as T, types

import sys, os, subprocess, threading, importlib

from pathlib import Path
import orjson, inspect

from argparse import ArgumentParser

from wplib import log, WP_PY_RESOURCE_PATH, WP_ROOT, WP_ROOT_PATH, WP_PY_ROOT

"""
idem-specific DCC classes shouldn't do too much, just
run the program and pass in functions to execute at startup - 
for now.

maybe it's worth having a single higher class to represent DCC overall,
to start up headless sessions, servers? import, export?
could do.

to state the obvious, dcc domain code should not depend on idem

- associate right dcc launch with class - get exe path

don't care about software versions for now, just get it working

a core dcc package like wpm could define core operations to run on startup
then wpm defines pipeline ops to run on startup
then idem defines random idem stuff to run on startup
then individual assets, shots, etc - 
there's a lot of stuff we could want to stack on certain events for dccs
absolutely NO idea how to do any of that, for now we hardcode a single file

DCCProcess - lightweight class representing bare bones of program, accessed
	from without and within session - not inherited.

DCCSession - inherited DCC specific class, only accessible from within domain

"""


class DCC:
	dccName = ""

	def __init__(self, processName:str):
		# process name is idem-side identifier for live process, independent of DCC scene name
		self.processName = processName
		self.process = None

	@classmethod
	def getConfig(cls)->dict:
		from idem import getConfig
		return getConfig()

	@classmethod
	def argParser(cls)->ArgumentParser:
		"""idem-specific parser to pull out idem params from CLI"""
		parser = ArgumentParser()
		# parser.add_argument("idem_params"#, required=False
		#                     )
		return parser

	def idemStartupFilePath(self)->Path:
		"""by default, look for a 'startuptemplate.py' file
		next to this definition

		this should only include idem-specific startup, and should run
		AFTER any general code base work for the dcc
		"""
		return Path(inspect.getfile(type(self))).parent / "startup.py"

	def startupFormattedFilePath(self,
	                             processName:str=""
	                             ):
		""" return scratch file, NOT VERSIONED
		replace WP_ROOT token in path with proper py root -
		TODO: a proper expansion system for paths like Houdini does it"""
		processName = processName or self.processName
		configPath = self.getConfig()["scratchDir"]
		configPath = configPath.replace("$WP_PY_ROOT", str(WP_PY_ROOT))
		return Path(configPath) / processName

	def formatStartupFile(self,
	                      templatePath:Path,
	                      args:tuple,
	                      kwargs:dict,
	                      outputPath:Path
	                      ):
		"""format the code file passed to DCC on startup -
		pass only primitives as arguments here,
		once process is started up, an RPC link can be used to
		send more complex information"""
		baseStr = templatePath.read_text()
		formattedStr = baseStr.replace("$ARGS", str(args)).replace("$KWARGS", str(kwargs))
		outputPath.write_text(formattedStr)

	@classmethod
	def iconPath(cls)->Path:
		return WP_PY_RESOURCE_PATH / "icon" / (cls.dccName + ".png")

	def launch(self,
	           #startupFn=None
	           idemParams:dict
	           ):
		raise NotImplementedError

