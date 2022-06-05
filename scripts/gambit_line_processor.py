#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re

KEYWORD = "[A-Z][A-Za-z0-9_]*"
MULTI_KEYWORDS = "[A-Z][A-Za-z0-9\|_]*"
TEMPLATE_KEYWORD = "(" + KEYWORD + ")\<(" + KEYWORD + ")\>"
TAB_SIZE = 4

class GambitLineProcessor:
	"""Process a single line from a Gambit (.gm) file."""
	def __init__(self):
		pass
	
	@staticmethod
	def calcIndent(str):
		m = re.match("(\t+)", str)
		if m:
			return len(m.group(1))
		m = re.match("( +)", str)
		if m:
			numSpaces = len(m.group(1))
			if numSpaces % 4 == 0:
				return int(numSpaces / TAB_SIZE)
			else:
				raise Exception("Invalid leading whitespace. Use tabs or {0:d} spaces.".format(TAB_SIZE))
		return 0

	# ==========
	# Helper routines for adding new lines to the array.
	# ==========
	
	@staticmethod
	def addImport(comment):
		return {
			'type': "IMPORT",
			'cost': None,
			'indent': 0,
			'line': "",
			'comment': comment,
		}

	@staticmethod
	def addComment(line, comment):
		indent = GambitLineProcessor.calcIndent(line)
		info = {
			'type': "COMMENT",
			'cost': None,
			'indent': indent,
			'line': "",
			'comment': comment
		}
		type = "COMMENT"
		if comment == "":
			info['type'] = "BLANK"
			indent = 0
			info['indent'] = indent
		elif indent == 0:
			if comment.startswith("SECTION:"):
				info['type'] = "SECTION"
				info['comment'] = comment[8:].strip()
			elif comment.startswith("SUBSECTION:"):
				info['type'] = "SUBSECTION"
				info['comment'] = comment[11:].strip()
			elif comment.startswith("NAME:"):
				info['type'] = "NAME"
				info['comment'] = comment[5:].strip()
			elif comment.startswith("BGG Weight:"):
				# Ignore
				return None

		return info

	@staticmethod
	def addTemplateDefinition(keyword, param, comment):
		return {
			'type': "TEMPLATE",
			'cost': 1,
			'indent': 0,
			'line': "",
			'comment': comment,
			'keyword': keyword,
			'param': param,
		}

	@staticmethod
	def addDefinition(keywords, type, comment):
		keyword = keywords[0]
		keywordPlural = None
		if len(keywords) == 2:
			keywordPlural = keywords[1]
		elif len(keywords) > 2:
			raise Exception("Unexpected keyword group {0:s}".format('|'.join(keywords)))

		parent = None
		types = [type]
		if type.find(',') != -1:
			types = [x.strip() for x in type.split(',')]
		else:
			m = re.match("(" + KEYWORD + ")\s+of\s+(" + KEYWORD + ")", type)
			if m:
				types = [ m.group(1) ]
				parent = m.group(2)
		
		return {
			'type': "DEF",
			'cost': 1,
			'indent': 0,
			'line': "",
			'comment': comment,
			'keyword': keyword,
			'alt-keyword': keywordPlural,
			'types': types,
			'parent': parent,
		}

	@staticmethod
	def addConstraintDescription(line, comment):
		indent = GambitLineProcessor.calcIndent(line)
		line = line.strip()
		line = line[1:]  # Remove the leading '!'
		line = line.strip()

		return {
			'type': "CONSTRAINT",
			'cost': 1,
			'indent': indent,
			'line': line,
			'comment': comment,
		}

	@staticmethod
	def addDescription(line, comment):
		indent = GambitLineProcessor.calcIndent(line)
		line = line.strip()
		cost = 1
		# Entries in a lookup table.
		if line[0] == '*':
			cost = 0

		return {
			'type': "DESC",
			'cost': cost,
			'indent': indent,
			'line': line,
			'comment': comment,
		}

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
		if line.startswith("#import"):
			return GambitLineProcessor.addImport(line[8:].strip())

		# Separate out comments and handle empty lines.
		m = re.match("(.*?)//(.*)", line)
		if m:
			line = m.group(1)
			comment = m.group(2)
		comment = comment.strip()
		if line.strip() == "":
			return GambitLineProcessor.addComment(line, comment)
		line = line.rstrip()

		# TEMPLATE_TYPE: Verb
		m = re.match(TEMPLATE_KEYWORD + ":\s*Verb", line)
		if m:
			keyword = m.group(1)
			param = m.group(2)
			return GambitLineProcessor.addTemplateDefinition(keyword, param, comment)
		
		# NEW_TYPE: TYPE
		# NEW_TYPE|PLURAL: TYPE
		# NEW_ATTRIBUTE: Attribute of TYPE
		# NEW_TYPE: TYPE1, TYPE2
		m = re.match("(" + MULTI_KEYWORDS + "):\s*(.*)", line)
		if m:
			keyword = m.group(1)
			type = m.group(2)
			keywords = keyword.split('|')
			return GambitLineProcessor.addDefinition(keywords, type, comment)

		if line.strip().startswith("!"):
			return GambitLineProcessor.addConstraintDescription(line, comment)
			
		return GambitLineProcessor.addDescription(line, comment)