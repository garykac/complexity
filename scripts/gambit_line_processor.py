#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re

from gambit import Keyword, LinePrefix, RegEx, TAB_SIZE
from gambit_line_info import GambitLineInfo

class GambitLineProcessor:
	"""Process a single line from a Gambit (.gm) file."""
	def __init__(self):
		pass
	
	@staticmethod
	def calcIndent(str: str) -> int:
		m = re.match("(\t+)", str)
		if m:
			return len(m.group(1))
		m = re.match("( +)", str)
		if m:
			numSpaces = len(m.group(1))
			if numSpaces % TAB_SIZE == 0:
				return int(numSpaces / TAB_SIZE)
			else:
				raise Exception("Invalid leading whitespace. Use tabs or {0:d} spaces.".format(TAB_SIZE))
		return 0

	@staticmethod
	def processLine(lineNum, line):
		comment = ""

		# Import base definitions from another file.
		if line.startswith(Keyword.GAME_IMPORT + ':'):
			return GambitLineInfo.importGame(lineNum, line[len(Keyword.GAME_IMPORT)+1:].strip())

		# Declare imported terms.
		if line.startswith(Keyword.IMPORT + ':'):
			return GambitLineInfo.importTerm(lineNum, line[len(Keyword.IMPORT)+1:].strip())

		if line.startswith(Keyword.NAME + ':'):
			return GambitLineInfo.name(lineNum, line[len(Keyword.NAME)+1:].strip())
		if line.startswith(Keyword.SECTION + ':'):
			return GambitLineInfo.section(lineNum, line[len(Keyword.SECTION)+1:].strip())
		if line.startswith(Keyword.SUBSECTION + ':'):
			return GambitLineInfo.subsection(lineNum, line[len(Keyword.SUBSECTION)+1:].strip())

		# Separate out comments and handle empty lines.
		m = re.match("(.*?)//(.*)", line)
		if m:
			line = m.group(1)
			comment = m.group(2)
		comment = comment.strip()
		if line.strip() == "":
			indent = GambitLineProcessor.calcIndent(line)
			return GambitLineInfo.comment(lineNum, indent, comment)
		line = line.rstrip()

		# TEMPLATE_TYPE: Verb
		m = re.match(RegEx.TEMPLATE_KEYWORD + ":\s*Verb", line)
		if m:
			keyword = m.group(1)
			param = m.group(2)
			return GambitLineInfo.templateDefinition(lineNum, keyword, param, comment)
		
		# NEW_TYPE: TYPE
		# NEW_TYPE|PLURAL: TYPE
		# NEW_ATTRIBUTE: Attribute of TYPE
		# NEW_TYPE: TYPE1, TYPE2
		m = re.match("(" + RegEx.MULTI_KEYWORDS + "):\s*(.*)", line)
		if m:
			keyword = m.group(1)
			type = m.group(2)
			keywords = keyword.split('|')
			return GambitLineInfo.definition(lineNum, keywords, type, comment)

		indent = GambitLineProcessor.calcIndent(line)
		line = line.strip()

		if line.startswith(LinePrefix.CONSTRAINT):
			return GambitLineInfo.constraintDescription(lineNum, indent, line, comment)
			
		return GambitLineInfo.description(lineNum, indent, line, comment)
