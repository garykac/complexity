#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import annotations

import sys

class Log:
	"""Display error."""
	def __init__(self):
		pass
	
	@staticmethod
	def line(lineNum: int, lineStr: str) -> None:
		print(f"LINE {lineNum}: {lineStr}")

	@staticmethod
	def error(msg: str, lineNum: int = -1) -> None:
		if lineNum > 0:
			print(f"ERROR ({lineNum}): {msg}")
		else:
			print(f"ERROR: {msg}")

		#traceback.print_exc()
		#if self.quitOnError:
		sys.exit(0)
		#raise Exception(msg)

	@staticmethod
	def errorInternal(msg: str, lineNum: int = -1) -> None:
		if lineNum > 0:
			print(f"INTERNAL ERROR ({lineNum}): {msg}")
		else:
			print(f"INTERNAL ERROR: {msg}")

		#traceback.print_exc()
		raise Exception(msg)

	@staticmethod
	def warning(msg: str, lineNum: int = -1) -> None:
		if lineNum > 0:
			print(f"WARNING ({lineNum}): {msg}")
		else:
			print(f"WARNING: {msg}")
