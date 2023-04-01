#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import annotations

import re

from gambit import CONSTRAINT_PREFIX, LOOKUP_TABLE_PREFIX
from gambit import (LT_COMMENT, LT_BLANK,
					LT_NAME, LT_IMPORT, LT_IMPORT_GAME, LT_SECTION, LT_SUBSECTION,
					LT_DEF, LT_TEMPLATE, LT_CONSTRAINT, LT_DESC)
from gambit import KEYWORD
from typing import List
from typing import Optional

class GambitLineInfo:
	"""Process a single line from a Gambit (.gm) file."""
	def __init__(self, type: str):
		self.lineType: str = type
		self.cost: Optional[int] = None
		self.indent: int = 0
		self.line: str  = ""
		self.lineComment: str = ""
		
		self.data: Any = None
		
		# Keyword for definitions and templates.
		self.keyword: Optional[str] = None
		
		# Alternate keywords (e.g., plural).
		self.altKeyword: Optional[str] = None
		
		self.types: List[str] = []
		self.parent: Optional[str] = None
		
		# Parameter for templates.
		self.param: Optional[str] = None
		
		self.tokens = None
	
	def setTokens(self, tokens) -> None:
		self.tokens = tokens

	@staticmethod
	def name(name: str) -> GambitLineInfo:
		info: GambitLineInfo = GambitLineInfo(LT_NAME)
		info.lineComment = name
		return info

	@staticmethod
	def importGame(name: str) -> GambitLineInfo:
		info: GambitLineInfo = GambitLineInfo(LT_IMPORT_GAME)
		info.data = name
		return info

	@staticmethod
	def importTerm(comment: str) -> GambitLineInfo:
		info: GambitLineInfo = GambitLineInfo(LT_IMPORT)
		info.data = [x.strip() for x in comment.split(',')]
		return info

	@staticmethod
	def section(name: str) -> GambitLineInfo:
		info: GambitLineInfo = GambitLineInfo(LT_SECTION)
		info.lineComment = name.strip()
		return info

	@staticmethod
	def subsection(name: str) -> GambitLineInfo:
		info: GambitLineInfo = GambitLineInfo(LT_SUBSECTION)
		info.lineComment = name.strip()
		return info

	@staticmethod
	def comment(indent: int, comment: str) -> GambitLineInfo:
		type: str = LT_COMMENT
		if comment == "":
			type = LT_BLANK
			indent = 0
		info: GambitLineInfo = GambitLineInfo(type)
		info.indent = indent
		info.lineComment = comment
		return info

	@staticmethod
	def templateDefinition(keyword: str, param: str, comment: str) -> GambitLineInfo:
		info: GambitLineInfo = GambitLineInfo(LT_TEMPLATE)
		info.cost = 1
		info.lineComment = comment
		info.keyword = keyword
		info.param = param
		return info

	@staticmethod
	def definition(keywords: List[str], defType: str, comment: str) -> GambitLineInfo:
		info: GambitLineInfo = GambitLineInfo(LT_DEF)
		info.cost = 1
		info.lineComment = comment

		info.keyword = keywords[0]
		info.altKeyword = None
		if len(keywords) == 2:
			info.altKeyword = keywords[1]
		elif len(keywords) > 2:
			raise Exception("Unexpected keyword group {0:s}".format('|'.join(keywords)))

		info.parent = None
		info.types = [defType]
		if defType.find(',') != -1:
			info.types = [x.strip() for x in defType.split(',')]
		else:
			m = re.match("(" + KEYWORD + ")\s+of\s+(" + KEYWORD + ")", defType)
			if m:
				info.types = [ m.group(1) ]
				info.parent = m.group(2)
		return info

	@staticmethod
	def constraintDescription(indent: int, line: str, comment: str) -> GambitLineInfo:
		info: GambitLineInfo = GambitLineInfo(LT_CONSTRAINT)
		info.cost = 1
		info.indent = indent
		info.line = line[1:].strip()  # Remove the leading '!'
		info.lineComment = comment
		return info

	@staticmethod
	def description(indent: int, line: str, comment: str) -> GambitLineInfo:
		cost = 1
		# Entries in a lookup table.
		if line[0] == LOOKUP_TABLE_PREFIX:
			cost = 0

		if indent == 0:
			raise Exception(f"Invalid line: {line}")

		info: GambitLineInfo = GambitLineInfo(LT_DESC)
		info.cost = cost
		info.indent = indent
		info.line = line
		info.lineComment = comment
		return info
