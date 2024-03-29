#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import sys
import traceback

from gambit import LineType, VocabType
from gambit_line_processor import GambitLineProcessor
from gambit_tokenizer import GambitTokenizer
from log import Log

from typing import Optional, List, Union

BASE_TYPES = [
	"Noun", "Verb", "Attribute", "Part", "Condition", "Constraint", "Exit",
]

STANDARD_TERMS = [
	"Setup", "PlayGame", "CalculateScore", "DetermineWinner"
]

class GambitVocab:
	"""Vocabulary manager for a GambitParser."""
	def __init__(self):
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
			self._addVocab(key, None, [VocabType.BASE])

	def contains(self, term) -> bool:
		return term in self.vocab
		
	def lookup(self, term) -> list:
		return self.vocab[term]

	def loadImportableTerms(self, import_file) -> None:
		with open(import_file, 'r') as file:
			for line in file:
				lineinfo = GambitLineProcessor.processLine(0, line)

				if lineinfo:
					type = lineinfo.lineType
					if type == LineType.DEF:
						keyword = lineinfo.keyword
						plural = lineinfo.altKeyword
						self.importable[keyword] = plural
					elif type == LineType.VALUES:
						items = [x.strip() for x in lineinfo.line.split(',')]
						for i in items:
							self.importable[i] = None

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
		info = [VocabType.LOCAL, types]
		if parent:
			info.append(parent)
		self._addVocab(key, keyPlural, info)
	
	def addEnumValue(self, key):
		info = [VocabType.LOCAL, "Value"]
		self._addVocab(key, None, info)
	
	def addTemplate(self, key, param):
		info = [VocabType.LOCAL, "Verb", param]
		self._addVocab(key, None, info)

	def addImport(self, key, plural):
		info = [VocabType.IMPORT, "_import.gm"]
		self._addVocab(key, plural, info)
		self.imports[key] = True

	def addGameImport(self, key, plural, filename):
		info = [VocabType.GAME_IMPORT, filename]
		self._addVocab(key, plural, info)
		self.old_imports[key] = True

	def _addVocab(self, key: str, keyPlural: Optional[str], info: list) -> None:
		self.vocab[key] = info
		self.referencedBy[key] = set()

		# Simple default plurals.
		if keyPlural is None:
			# "Bonus"
			if key[-2:] in ['us', 'ex']:
				keyPlural = key + "es"
			elif key[-1] == 's':
				keyPlural = key
			# "Factory", "Quarry", "City", but not "Donkey"
			elif key[-2:] in ['ry', 'ty']:
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
		template = GambitTokenizer.isTemplate(term)
		if template:
			(keyword, param) = template
			return self.isVocab(keyword) and self.isVocab(param)

		return False
	
	def importTerms(self, terms):
		for t in terms:
			if not t in self.importable:
				Log.error(f"Unknown term for import: {t}")
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
			if self.vocab[k][0] == VocabType.LOCAL and len(v) == 0:
				# Allow local definitions to overwrite imported defs.
				if not k in self.old_imports:
					Log.warning(f"Term is defined but never referenced: {k}")
			if self.vocab[k][0] == VocabType.IMPORT and len(v) == 0:
				Log.warning(f"Term is imported but never referenced: {k}")
