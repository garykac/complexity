#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re

from gambit import CONSTRAINT_PREFIX
from gambit import (NAME_KEYWORD, IMPORT_KEYWORD, IMPORT_GAME_KEYWORD, SECTION_KEYWORD,
					SUBSECTION_KEYWORD)
from gambit_line_info import GambitLineInfo

KEYWORD = "[A-Z][A-Za-z0-9_]*"
MULTI_KEYWORDS = "[A-Z][A-Za-z0-9\|_]*"
TEMPLATE_KEYWORD = "(" + KEYWORD + ")\<(" + KEYWORD + ")\>"
TAB_SIZE = 4

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
	def isTemplate(term):
		m = re.match(TEMPLATE_KEYWORD, term)
		if m:
			keyword = m.group(1)
			param = m.group(2)
			return (keyword, param)
		return None

	# Strip non-alphanumeric from beginning/end of token.
	# Also remove contraction endings like "'s".
	@staticmethod
	def extractKeyword(word):
		m = re.match("([^A-Za-z0-9_]*)(" + KEYWORD + ")([^A-Za-z0-9_]*.*)", word)
		if m:
			return (m.group(1), m.group(2), m.group(3))
		return ("", word, "")

	@staticmethod
	def processLine(line):
		comment = ""

		# Import base definitions from another file.
		if line.startswith(IMPORT_GAME_KEYWORD + ':'):
			return GambitLineInfo.importGame(line[len(IMPORT_GAME_KEYWORD)+1:].strip())

		# Declare imported terms.
		if line.startswith(IMPORT_KEYWORD + ':'):
			return GambitLineInfo.importTerm(line[len(IMPORT_KEYWORD)+1:].strip())

		if line.startswith(NAME_KEYWORD + ':'):
			return GambitLineInfo.name(line[len(NAME_KEYWORD)+1:].strip())
		if line.startswith(SECTION_KEYWORD + ':'):
			return GambitLineInfo.section(line[len(SECTION_KEYWORD)+1:].strip())
		if line.startswith(SUBSECTION_KEYWORD + ':'):
			return GambitLineInfo.subsection(line[len(SUBSECTION_KEYWORD)+1:].strip())

		# Separate out comments and handle empty lines.
		m = re.match("(.*?)//(.*)", line)
		if m:
			line = m.group(1)
			comment = m.group(2)
		comment = comment.strip()
		if line.strip() == "":
			indent = GambitLineProcessor.calcIndent(line)
			return GambitLineInfo.comment(indent, comment)
		line = line.rstrip()

		# TEMPLATE_TYPE: Verb
		m = re.match(TEMPLATE_KEYWORD + ":\s*Verb", line)
		if m:
			keyword = m.group(1)
			param = m.group(2)
			return GambitLineInfo.templateDefinition(keyword, param, comment)
		
		# NEW_TYPE: TYPE
		# NEW_TYPE|PLURAL: TYPE
		# NEW_ATTRIBUTE: Attribute of TYPE
		# NEW_TYPE: TYPE1, TYPE2
		m = re.match("(" + MULTI_KEYWORDS + "):\s*(.*)", line)
		if m:
			keyword = m.group(1)
			type = m.group(2)
			keywords = keyword.split('|')
			return GambitLineInfo.definition(keywords, type, comment)

		indent = GambitLineProcessor.calcIndent(line)
		line = line.strip()

		if line.startswith(CONSTRAINT_PREFIX):
			return GambitLineInfo.constraintDescription(indent, line, comment)
			
		return GambitLineInfo.description(indent, line, comment)
