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
from gambit_line_processor import GambitLineProcessor
from gambit_vocab import GambitVocab
from tokenizer import Tokenizer

from typing import Optional, List, Union

FREE_ACTIONS = [
	"Then:",
	"Else:",
	"Otherwise:",
	"If you do:",
	"If you don't:",
	"If any of:",
	"If all of:",
	"For each Player:",	# TODO: generalize to "For each <term>:"
	"For each other Player:",
	"Choose one:",
	"Choose one of:",
	# Conditions
	"Any of:",
]

# Handle suffix words like "Discard it" or "Shuffle them"
FREE_SUFFIX_WORDS = [
	"it",
	"them",
]

STANDARD_TERMS = [
	"Setup", "PlayGame", "CalculateScore", "DetermineWinner"
]

class GambitParser:
	"""Parser for Gambit (.gm) files."""
	def __init__(self, options):
		self.debug: bool = False
		self.verbose: bool = False
		self.useWarnings: bool = False
		self.warnOnTodo: bool = False
		self.quitOnError: bool = False

		if 'warnings' in options:
			self.useWarnings = options['warnings']
		if 'verbose' in options:
			self.verbose = options['verbose']

		self.lines: List[str] = []
		self.lineInfo: List[GambitLineInfo] = []
		self.lineNum: int = 0
		self.maxIndent: int = 0

		self.costTotal: int = 0
		self.sectionCosts = []

		self.gameTitle: str = "Unknown"

		self.currentDir: Optional[str] = None
	
		self.vocab = GambitVocab(self)

		# Special actions with 0 cost.
		self.freeActions = {}
		self.initFreeActions()
	
	def initFreeActions(self) -> None:
		for a in FREE_ACTIONS:
			self.freeActions[a] = True
	
	def loadImportableTerms(self, importFile) -> None:
		self.vocab.loadImportableTerms(importFile)

	# Provide a warning if there are TODO comments left in the source file.
	def setWarnOnTodo(self) -> None:
		self.warnOnTodo = True

	def errorLine(self, msg: str, lineNum: int = -1) -> None:
		num = -1
		if lineNum != -1:
			num = lineNum
		elif self.lineNum > 0:
			num = self.lineNum
		if num > 0:
			print(f"LINE {num}: {self.lines[num-1]}")
		self.error(msg)

	def error(self, msg: str) -> None:
		print("ERROR: {0:s}".format(msg))
		#traceback.print_exc()
		if self.quitOnError:
			sys.exit(0)
		raise Exception(msg)

	def warning(self, msg: str) -> None:
		if not self.useWarnings:
			self.error(msg)
		print("WARNING: {0:s}".format(msg))

	def warningLine(self, msg: str) -> None:
		print("WARNING {0:d}: {1:s}".format(self.lineNum, msg))

	# ==========
	# Calculating costs.
	# ==========
	
	# Update the costs of the individual lines.
	def updateCosts(self):
		maxLines = len(self.lineInfo)
		isVocabSection = False
		currDef = -1
		currDefCost = 0
		for i in range(0, maxLines):
			r = self.lineInfo[i]
			type = r.lineType

			if type == LT_SECTION:
				isVocabSection = False
				if r.lineComment == "Vocabulary":
					isVocabSection = True

			elif type == LT_DEF or type == LT_TEMPLATE:
				# DEF must alwyas cost at least one.
				if currDef != -1 and isVocabSection and currDefCost == 0:
					self.lineInfo[currDef].cost = 1

				currDef = i
				currDefCost = 0

				# If a DEF has DESC indented under it, then the cost is
				# determined by the associated DESCs and the DEF itself is 0.
				# Otherwise (with no DESCs) the cost of the DEF is 1.
				if self.defHasDesc(i):
					# Set to None instead of 0 so that the cost column is left blank.
					r.cost = None

			elif type in [LT_DESC, LT_CONSTRAINT]:
				zeroCost = False
				line = r.line

				# Free actions are free.
				if line in self.freeActions:
					zeroCost = True

				# Lines that consist entirely of a single defined term are free.
				# The cost comes from the definition.
				if self.vocab.isDefinedTerm(line):
					zeroCost = True

				# TODO: Better detection of possible missing imports.
				# This will only catch it if the import is the only thing on the line.
				if (not zeroCost) and self.vocab.isImportable(line):
					self.warning(f"Possibly missing import for {line}")

				# Handle special cases with Vocab
				words = Tokenizer.tokenize(line)

				# Lines that consist entirely of a defined terms are free.
				allDefined = True
				for w in words:
					if not self.vocab.isDefinedTerm(w):
						allDefined = False
				if allDefined:
					zeroCost = True

				# Handle "Discard xxx"
				if len(words) == 2 and self.vocab.isDefinedTerm(words[0]):
					# Handle: "Discard it"
					if words[1] in FREE_SUFFIX_WORDS:
						zeroCost = True
					# Handle: "Discard x2"
					if re.match(r'x\d+$', words[1]):
						zeroCost = True
				# Handle "Success:" and "Success: DrawCard"
				if words[0][-1] == ':' and self.vocab.isDefinedTerm(words[0][0:-1]):
					if len(words) == 1 or  self.vocab.isDefinedTerm(words[1]):
						zeroCost = True
				
				if zeroCost:
					r.cost = 0
				else:
					currDefCost += 1
			
			elif not type in [LT_COMMENT, LT_IMPORT, LT_GAME_IMPORT, LT_NAME, LT_SUBSECTION, LT_BLANK]:
				self.error("Unhandled type in updateCosts: {0:s}".format(type))

	# Return true if the DEF at the given index has at least one DESC
	# associated with it.
	def defHasDesc(self, iDef):
		if not self.lineInfo[iDef].lineType in [LT_DEF, LT_TEMPLATE]:
			self.error("Not a DEF on line {0:d}: {1:s}".format(iDef, self.lineInfo[iDef].lineType))
		maxLines = len(self.lineInfo)
		i = iDef + 1
		# Look ahead to search for DESC lines that follow the DEF.
		while i < maxLines:
			r = self.lineInfo[i]
			type = r.lineType
			if type in [LT_DEF, LT_BLANK, LT_TEMPLATE]:
				return False
			if type == LT_DESC and r.indent == 1:
				return True
			if not type in [LT_COMMENT, LT_SECTION, LT_SUBSECTION, LT_CONSTRAINT]:
				self.error("Unhandled type in defHasDesc: {0:s}".format(type))
			i += 1
		return False
	
	# Calculate the total cost for the game.
	def calcTotalCost(self):
		self.costTotal = 0
		self.sectionCosts = []
		self.subsectionCosts = {}
		currentSection = None
		currentSubsection = None
		cost = 0
		for r in self.lineInfo:
			type = r.lineType
			if type in [LT_DEF, LT_TEMPLATE, LT_DESC, LT_CONSTRAINT]:
				if r.cost:
					self.costTotal += r.cost
					cost += r.cost
			elif type == LT_SECTION:
				if currentSubsection:
					self.subsectionCosts[currentSection].append([currentSubsection, cost])
				elif currentSection:
					self.sectionCosts.append([currentSection, cost])
				currentSection = r.lineComment
				currentSubsection = None
				cost = 0
			elif type == LT_SUBSECTION:
				if currentSubsection:
					self.subsectionCosts[currentSection].append([currentSubsection, cost])
				else:
					self.sectionCosts.append([currentSection, cost])
				currentSubsection = r.lineComment
				if not currentSection in self.subsectionCosts:
					self.subsectionCosts[currentSection] = []
				cost = 0
			elif not type in [LT_COMMENT, LT_IMPORT, LT_GAME_IMPORT, LT_NAME, LT_SECTION, LT_SUBSECTION, LT_BLANK]:
				self.error("Unhandled type in calcTotalCost: {0:s}".format(type))
		
		# Record cost for last section.
		if currentSection:
			if currentSubsection:
				self.subsectionCosts[currentSection].append([currentSubsection, cost])
			else:
				self.sectionCosts.append([currentSection, cost])
	
	def getVocabCost(self):
		for s in self.sectionCosts:
			if s[0] == "Vocabulary":
				return s[1]
		return 0

	# ==========
	# Process a Gambit file to calculate cost and generate HTML.
	# ==========
	
	def process(self, src_dir, filepath):
		self.currentDir = src_dir
		with open(filepath, 'r') as file:
			self.lineNum = 0
			for line in file:
				self.processLine(line)
				if self.warnOnTodo and line.find("TODO") != -1:
					self.warningLine("Unresolved TODO {0:s}".format(line.strip()))
		
		self.extractAllReferences()

		self.updateCosts()
		self.calcTotalCost()
		
	def processLine(self, line):
		self.lineNum += 1
		self.lines.append(line.rstrip())

		try:
			lineinfo = GambitLineProcessor.processLine(line)
		except Exception as ex:
			self.errorLine(str(ex))
		
		# |lineinfo| is GambitLineInfo
		# plus additional values depending on the |lineType|.
		self.lineInfo.append(lineinfo)
		type = lineinfo.lineType
		if type == LT_GAME_IMPORT:
			self.importGameFile(lineinfo.data)
		elif type == LT_IMPORT:
			self.vocab.importTerms(lineinfo.data)
		elif type == LT_DEF:
			parent = lineinfo.parent
			if parent and not self.vocab.contains(parent):
				self.errorLine(f"Unknown parent: {parent}")
			for t in lineinfo.types:
				if not self.vocab.contains(t):
					self.errorLine(f"Unknown term: {t}")

			self.vocab.addDef(lineinfo.keyword, lineinfo.altKeyword, lineinfo.types, parent)
		elif type == LT_TEMPLATE:
			self.vocab.addTemplate(lineinfo.keyword, lineinfo.param)
		elif type == LT_NAME:
			self.gameTitle = lineinfo.lineComment
		elif type == "ERROR":
			self.errorLine(lineinfo.lineComment)
		elif not type in [LT_COMMENT, LT_CONSTRAINT, LT_DESC, LT_SECTION, LT_SUBSECTION, LT_BLANK]:
			self.error(f"Unhandled type in processLine: {type}")

		# Record the max indent level so that we can format the HTML table correctly.
		if lineinfo.indent > self.maxIndent:
			self.maxIndent = lineinfo.indent

	def importGameFile(self, name):
		basename = os.path.basename(name)
		dirname = os.path.dirname(name)
		basename = self.convertInitialCapsToHyphenated(basename) + ".gm"
		with open(os.path.join(self.currentDir, dirname, basename), 'r') as file:
			for line in file:
				try:
					lineinfo: GambitLineInfo = GambitLineProcessor.processLine(line)
				except Exception as ex:
					self.errorLine(str(ex))

				if lineinfo:
					type = lineinfo.lineType
					if type == LT_DEF:
						keyword = lineinfo.keyword
						plural = lineinfo.altKeyword
						self.vocab.addGameImport(keyword, plural, name)
	
	def convertInitialCapsToHyphenated(self, name):
		matches = [m.start(0) for m in re.finditer("[A-Z]", name)]
		if not matches:
			return name
		newName = ""
		iName = 0
		for iCap in matches:
			for i in range(iName, iCap):
				newName += name[i]
			if iCap != 0:
				newName += '-'
			newName += name[iCap].lower()
			iName = iCap + 1
		newName += name[iName:]
		return newName
		
	def extractAllReferences(self):
		currDef = None
		for i in range(len(self.lineInfo)):
			r = self.lineInfo[i]
			type = r.lineType
			if type == LT_DEF:
				currDef = r.keyword
				for t in r.types:
					self.vocab.addReference(t, currDef)
				if r.parent:
					self.vocab.addReference(r.parent, currDef)
					r.setTokens(self.extractReference(i, f"{r.types[0]} of {r.parent}", currDef))
				else:
					r.setTokens(self.extractReference(i, ', '.join(r.types), currDef))
				self.extractReference(i, r.lineComment, currDef, True)
			elif type == LT_TEMPLATE:
				currDef = r.keyword
				self.vocab.addReference("Verb", currDef)
				r.setTokens(["Verb"])
				self.extractReference(i, r.lineComment, currDef, True)
			elif type == LT_DESC:
				r.setTokens(self.extractReference(i, r.line, currDef))
				self.extractReference(i, r.lineComment, currDef, True)
			elif type == LT_CONSTRAINT:
				r.setTokens(self.extractReference(i, r.line, currDef))
				self.extractReference(i, r.lineComment, currDef, True)
			elif not type in [LT_COMMENT, LT_IMPORT, LT_GAME_IMPORT, LT_NAME, LT_SECTION, LT_SUBSECTION, LT_BLANK]:
				self.error("Unhandled type in extractAllReferences: {0:s}".format(type))
	
	def lookupCanonicalForm(self, word):
		# Strip non-alphanumeric from beginning/end of token.
		(prefix, word, postfix) = GambitLineProcessor.extractKeyword(word)
		if word in self.vocabPlural:
			return self.vocabPlural[word]
	
	def checkReferences(self):
		self.vocab.checkReferences()
	
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
				self.vocab.addReference(keyword, currDef)
				self.vocab.addReference(param, currDef)
				newWords.append(["TREF", keyword, param])
				continue

			# Strip non-alphanumeric from beginning/end of token.
			# Also remove contraction endings like "'s".
			(prefix, word0, postfix) = GambitLineProcessor.extractKeyword(word)

			# Normalize plural forms.
			canonicalForm = self.vocab.normalize(word0)
			
			if self.vocab.contains(canonicalForm):
				self.vocab.addReference(canonicalForm, currDef)
				newWords.append(["REF", canonicalForm, prefix, word0, postfix])
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
