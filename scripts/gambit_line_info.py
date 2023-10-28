#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import annotations

import re

from gambit import LinePrefix, LineType, RegEx
from gambit_token import TokenType
from gambit_tokenizer import GambitTokenizer
from log import Log

from typing import List
from typing import Optional

class GambitLineInfo:
	"""Process a single line from a Gambit (.gm) file."""
	def __init__(self, lineNum: int, type: str):
		self.lineNum: int = lineNum
		self.lineType: str = type
		self.cost: Optional[int] = None
		self.indent: int = 0
		self.line: str  = ""
		self.lineComment: str = ""
		
		self.name: str = ""
		self.data: Any = None
		
		# Keyword for definitions and templates.
		self.keyword: Optional[str] = None
		
		# Alternate keywords (e.g., plural).
		self.altKeyword: Optional[str] = None
		
		self.types: List[str] = []
		self.parent: Optional[str] = None
		
		# Parameter for templates.
		self.param: Optional[str] = None
		
		self.tokens = []
	
	@staticmethod
	def name(lineNum: int, name: str) -> GambitLineInfo:
		info: GambitLineInfo = GambitLineInfo(lineNum, LineType.NAME)
		info.name = name
		return info

	@staticmethod
	def importGame(lineNum: int, name: str) -> GambitLineInfo:
		info: GambitLineInfo = GambitLineInfo(lineNum, LineType.GAME_IMPORT)
		info.data = name
		return info

	@staticmethod
	def importTerm(lineNum: int, comment: str) -> GambitLineInfo:
		info: GambitLineInfo = GambitLineInfo(lineNum, LineType.IMPORT)
		info.data = [x.strip() for x in comment.split(',')]
		return info

	@staticmethod
	def section(lineNum: int, name: str) -> GambitLineInfo:
		info: GambitLineInfo = GambitLineInfo(lineNum, LineType.SECTION)
		info.name = name.strip()
		return info

	@staticmethod
	def subsection(lineNum: int, name: str) -> GambitLineInfo:
		info: GambitLineInfo = GambitLineInfo(lineNum, LineType.SUBSECTION)
		info.name = name.strip()
		return info

	@staticmethod
	def comment(lineNum: int, indent: int, comment: str) -> GambitLineInfo:
		type: str = LineType.COMMENT
		if comment == "":
			type = LineType.BLANK
			indent = 0
		info: GambitLineInfo = GambitLineInfo(lineNum, type)
		info.indent = indent
		info.lineComment = comment
		return info

	@staticmethod
	def templateDefinition(lineNum: int, keyword: str, param: str, comment: str) -> GambitLineInfo:
		info: GambitLineInfo = GambitLineInfo(lineNum, LineType.TEMPLATE)
		info.cost = 1
		info.lineComment = comment
		info.keyword = keyword
		info.param = param
		return info

	@staticmethod
	def definition(lineNum: int, keywords: List[str], defType: str, comment: str) -> GambitLineInfo:
		info: GambitLineInfo = GambitLineInfo(lineNum, LineType.DEF)
		info.cost = 1
		info.lineComment = comment

		info.keyword = keywords[0]
		info.altKeyword = None
		if len(keywords) == 2:
			info.altKeyword = keywords[1]
		elif len(keywords) > 2:
			Log.error(f"Unexpected keyword group {'|'.join(keywords)}", lineNum)

		info.parent = None
		info.types = [defType]
		if defType.find(',') != -1:
			info.types = [x.strip() for x in defType.split(',')]
		else:
			m = re.match("(" + RegEx.KEYWORD + ")\s+of\s+(" + RegEx.KEYWORD + ")", defType)
			if m:
				info.types = [ m.group(1) ]
				info.parent = m.group(2)
		return info

	@staticmethod
	def constraintDescription(lineNum: int, indent: int, line: str, comment: str) -> GambitLineInfo:
		info: GambitLineInfo = GambitLineInfo(lineNum, LineType.CONSTRAINT)
		info.cost = 1
		info.indent = indent
		info.line = line[len(LinePrefix.CONSTRAINT):].strip()  # Remove the leading '!'
		info.lineComment = comment
		return info

	@staticmethod
	def valuesDescription(lineNum: int, indent: int, line: str, comment: str) -> GambitLineInfo:
		info: GambitLineInfo = GambitLineInfo(lineNum, LineType.VALUES)
		info.cost = 1
		info.indent = indent
		info.line = line[len(LinePrefix.VALUES):].strip()  # Remove the leading 'Values:'
		info.lineComment = comment
		return info

	@staticmethod
	def description(lineNum: int, indent: int, line: str, comment: str) -> GambitLineInfo:
		cost = 1
		# Entries in a lookup table.
		if line[0] == LinePrefix.LOOKUP_TABLE:
			cost = 0

		if indent == 0:
			Log.line(lineNum, line)
			Log.error(f"Invalid line", lineNum)

		info: GambitLineInfo = GambitLineInfo(lineNum, LineType.DESC)
		info.cost = cost
		info.indent = indent
		info.line = line
		info.lineComment = comment
		return info

	def extractReferences(self, currDef, vocab):
		type = self.lineType

		if type == LineType.DEF:
			currDef = self.keyword
			for t in self.types:
				vocab.addReference(t, currDef)
			if self.parent:
				vocab.addReference(self.parent, currDef)
				typeInfo = f"{self.types[0]} of {self.parent}"
				self.tokens = self.extractReference(typeInfo, currDef, vocab)
			else:
				self.tokens = self.extractReference(', '.join(self.types), currDef, vocab)
			self.extractReference(self.lineComment, currDef, vocab, True)

		elif type == LineType.TEMPLATE:
			currDef = self.keyword
			vocab.addReference("Verb", currDef)
			self.tokens = ["Verb"]
			self.extractReference(self.lineComment, currDef, vocab, True)

		elif type in [LineType.DESC, LineType.CONSTRAINT, LineType.VALUES]:
			self.tokens = self.extractReference(self.line, currDef, vocab)
			self.extractReference(self.lineComment, currDef, vocab, True)
		
		elif not type in [
				LineType.COMMENT, LineType.IMPORT, LineType.GAME_IMPORT, LineType.NAME,
				LineType.SECTION, LineType.SUBSECTION, LineType.BLANK]:
			Log.errorInternal(f"Unhandled type in extractAllReferences: {type}", self.lineNum)

		return currDef
	
	def extractReference(self, line: str, currDef: str, vocab, inComment=False):
		lineNum = self.lineNum
		
		if line == "":
			return
		newWords: List[Union[str, List[str]]] = []
		firstWord = True
		for word in GambitTokenizer.split(line):
			# Skip over special initial characters.
			if firstWord and word == LinePrefix.LOOKUP_TABLE:
				newWords.append(LinePrefix.LOOKUP_TABLE)
				# Don't update firstWord since the next word might be capitalized.
				continue
				
			# Ignore strings.
			if word[0] == '"' and word[-1] == '"':
				newWords.append(word)
				continue

			# Look for template references like "Produce<Stone>".
			template = GambitTokenizer.isTemplate(word)
			if template:
				(keyword, param) = template
				vocab.addReference(keyword, currDef)
				vocab.addReference(param, currDef)
				newWords.append([TokenType.TEMPLATE_REF, keyword, param])
				continue

			# Strip non-alphanumeric from beginning/end of token.
			# Also remove contraction endings like "'s".
			(prefix, word0, postfix) = GambitTokenizer.extractKeyword(word)

			# Normalize plural forms.
			canonicalForm = vocab.normalize(word0)
			
			if vocab.contains(canonicalForm):
				vocab.addReference(canonicalForm, currDef)
				newWords.append([TokenType.REF, canonicalForm, prefix, word0, postfix])
			elif inComment:
				newWords.append(word)
			else:
				# Verify capitalized words.
				if firstWord and re.match(r'[A-Z].*[A-Z].*', word0):
					Log.line(lineNum, line)
					Log.error(f'Unable to find definition for "{word0}"', lineNum)
				elif not firstWord and word0[0].isupper():
					Log.line(lineNum, line)
					Log.error(f'Unable to find definition for "{word0}"', lineNum)
				newWords.append(word)

			firstWord = False
			if (word0 != "" and word0[-1] in ['.',':']) or (postfix != "" and postfix[-1] in ['.',':']):
				firstWord = True

		return newWords
