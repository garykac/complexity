#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import sys
import traceback

from gambit import LOOKUP_TABLE_PREFIX
from gambit import (LT_COMMENT, LT_BLANK,
					LT_NAME, LT_IMPORT, LT_GAME_IMPORT, LT_SECTION, LT_SUBSECTION,
					LT_DEF, LT_TEMPLATE, LT_CONSTRAINT, LT_DESC)
from gambit import V_BASE, V_LOCAL, V_IMPORT, V_GAME_IMPORT
from gambit import T_REF, T_TEMPLATE_REF
from gambit_line_processor import GambitLineProcessor
from tokenizer import Tokenizer

from typing import Optional, List, Union

BASE_TYPES = [
	"Noun", "Verb", "Attribute", "Part", "Condition", "Constraint", "Exit",
]

STANDARD_TERMS = [
	"Setup", "PlayGame", "CalculateScore", "DetermineWinner"
]

class GambitVocab:
	"""Vocabulary manager for a GambitParser."""
	def __init__(self, parser):
		self.parser = parser

		self.vocab: dict[str, list] = {}
		
		# Dictionary that maps plurals to the normalized form.
		self.vocabPlural: dict[str, str] = {}
		
		# Definitions that were imported (and possibly overwritten).
		self.old_imports = {}
		self.imports = {}
		
		# Term that are defined in the import file.
		self.importable = {}
		
		# Dict of defs that reference this def.
		self.referencedBy = {}

		for key in BASE_TYPES:
			self._addVocab(key, None, [V_BASE])

	def contains(self, term) -> bool:
		return term in self.vocab
		
	def lookup(self, term) -> list:
		return self.vocab[term]

	def loadImportableTerms(self, import_file) -> None:
		with open(import_file, 'r') as file:
			for line in file:
				try:
					lineinfo = GambitLineProcessor.processLine(line)
				except Exception as ex:
					self.parser.errorLine(str(ex))

				if lineinfo:
					if lineinfo.lineType == LT_DEF:
						keyword = lineinfo.keyword
						plural = lineinfo.altKeyword
						self.importable[keyword] = plural

	# ==========
	# Vocabulary
	# ==========

	def normalize(self, word: str) -> str:
		canonicalForm: str = word
		if word in self.vocabPlural:
			canonicalForm = self.vocabPlural[word]
		return canonicalForm
		
	def isVocab(self, word: str) -> bool:
		return self.normalize(word) in self.vocab
	
	def addDef(self, key, keyPlural, types, parent):
		info = [V_LOCAL, types]
		if parent:
			info.append(parent)
		self._addVocab(key, keyPlural, info)
	
	def addTemplate(self, key, param):
		info = [V_LOCAL, "Verb", param]
		self._addVocab(key, None, info)

	def addImport(self, key, plural):
		info = [V_IMPORT, "_import.gm"]
		self._addVocab(key, plural, info)
		self.imports[key] = True

	def addGameImport(self, key, plural, filename):
		info = [V_GAME_IMPORT, filename]
		self._addVocab(key, plural, info)
		self.old_imports[key] = True

	def _addVocab(self, key: str, keyPlural: Optional[str], info: list) -> None:
		self.vocab[key] = info
		self.referencedBy[key] = set()

		# Simple default plurals.
		if keyPlural is None:
			# "Bonus"
			if key[-2:] == 'us':
				keyPlural = key + "es"
			elif key[-1] == 's':
				keyPlural = key
			# "Factory", "Quarry", "City", but not "Donkey"
			elif key[-2:] == 'ry' or key[-2:] == 'ty':
				keyPlural = key[0:-1] + "ies"
			# "Domino"
			elif key[-1:] == 'o':
				keyPlural = key + "es"
			else:
				keyPlural = key + "s"

		# Mapping from plural to canonical form.
		self.vocabPlural[keyPlural] = key

	def isDefinedTerm(self, term: str) -> bool:
		if self.isVocab(term):
			return True

		# Check for templates.
		template = GambitLineProcessor.isTemplate(term)
		if template:
			(keyword, param) = template
			return self.isVocab(keyword) and self.isVocab(param)

		return False
	
	def importTerms(self, terms):
		for t in terms:
			if not t in self.importable:
				self.errorLine(f"Unknown term for import: {t}")
			keyword = t
			plural = self.importable[t]
			self.addImport(keyword, plural)

	def isImportable(self, term) -> bool:
		return term in self.importable

	# ================
	# Cross-references
	# ================

	# Record that |refTerm| is referenced by |refBy|.
	# |refBy| makes a reference to |refTerm|.
	def addReference(self, refTerm, refBy) -> None:
		if refTerm == refBy:
			return
		#if not refTerm in self.referencedBy:
		#	self.referencedBy[refTerm] = set()
		self.referencedBy[refTerm].add(refBy)

	def getReferencesTo(self, term) -> List[str]:
		refs = []
		if term in self.referencedBy:
			refs = sorted(self.referencedBy[term])
		return refs

	def checkReferences(self):
		for k,v in self.referencedBy.items():
			# Ignore standard terms (entry points like "Setup").
			if k in STANDARD_TERMS:
				continue
			# If defined locally but no references.
			if self.vocab[k][0] == V_LOCAL and len(v) == 0:
				# Allow local definitions to overwrite imported defs.
				if not k in self.old_imports:
					msg = "Term is defined but never referenced: {0:s}".format(k)
					self.parser.warning(msg)
			if self.vocab[k][0] == V_IMPORT and len(v) == 0:
				msg = f"Term is imported but never referenced: {k}"
				self.parser.warning(msg)

	def extractReferences(self, lineNum, currDef, lineInfo):
		type = lineInfo.lineType
		if type == LT_DEF:
			currDef = lineInfo.keyword
			for t in lineInfo.types:
				self.addReference(t, currDef)
			if lineInfo.parent:
				self.addReference(lineInfo.parent, currDef)
				typeInfo = f"{lineInfo.types[0]} of {lineInfo.parent}"
				lineInfo.setTokens(self.extractReference(lineNum, typeInfo, currDef))
			else:
				lineInfo.setTokens(self.extractReference(lineNum, ', '.join(lineInfo.types), currDef))
			self.extractReference(lineNum, lineInfo.lineComment, currDef, True)
		elif type == LT_TEMPLATE:
			currDef = lineInfo.keyword
			self.addReference("Verb", currDef)
			lineInfo.setTokens(["Verb"])
			self.extractReference(lineNum, lineInfo.lineComment, currDef, True)
		elif type == LT_DESC:
			lineInfo.setTokens(self.extractReference(lineNum, lineInfo.line, currDef))
			self.extractReference(lineNum, lineInfo.lineComment, currDef, True)
		elif type == LT_CONSTRAINT:
			lineInfo.setTokens(self.extractReference(lineNum, lineInfo.line, currDef))
			self.extractReference(lineNum, lineInfo.lineComment, currDef, True)
		elif not type in [LT_COMMENT, LT_IMPORT, LT_GAME_IMPORT, LT_NAME, LT_SECTION, LT_SUBSECTION, LT_BLANK]:
			self.error("Unhandled type in extractAllReferences: {0:s}".format(type))
		return currDef
	
	def extractReference(self, lineNum: int, line: str, currDef: str, inComment=False):
		if line == "":
			return
		newWords: List[Union[str, List[str]]] = []
		firstWord = True
		for word in Tokenizer.tokenize(line):
			# Skip over special initial characters.
			if firstWord and word == LOOKUP_TABLE_PREFIX:
				newWords.append(LOOKUP_TABLE_PREFIX)
				# Don't update firstWord since the next word might be capitalized.
				continue
				
			# Ignore strings.
			if word[0] == '"' and word[-1] == '"':
				newWords.append(word)
				continue

			# Look for template references like "Produce<Stone>".
			template = GambitLineProcessor.isTemplate(word)
			if template:
				(keyword, param) = template
				self.addReference(keyword, currDef)
				self.addReference(param, currDef)
				newWords.append([T_TEMPLATE_REF, keyword, param])
				continue

			# Strip non-alphanumeric from beginning/end of token.
			# Also remove contraction endings like "'s".
			(prefix, word0, postfix) = GambitLineProcessor.extractKeyword(word)

			# Normalize plural forms.
			canonicalForm = self.normalize(word0)
			
			if self.contains(canonicalForm):
				self.addReference(canonicalForm, currDef)
				newWords.append([T_REF, canonicalForm, prefix, word0, postfix])
			elif inComment:
				newWords.append(word)
			else:
				# Verify capitalized words.
				if firstWord and re.match(r'[A-Z].*[A-Z].*', word0):
					#raise Exception('Unable to find definition for "{0:s}"'.format(word0))
					self.errorLine(f"Unable to find definition for '{word0}'", lineNum)
				elif not firstWord and word0[0].isupper():
					#raise Exception('Unable to find definition for "{0:s}"'.format(word0))
					self.errorLine(f"Unable to find definition for '{word0}'", lineNum)
				newWords.append(word)

			firstWord = False
			if (word0 != "" and word0[-1] in ['.',':']) or (postfix != "" and postfix[-1] in ['.',':']):
				firstWord = True

		return newWords
