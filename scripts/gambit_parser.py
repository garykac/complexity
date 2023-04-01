#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import sys
import traceback

from gambit_line_processor import GambitLineProcessor
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

BASE_TYPES = [
	"Noun", "Verb", "Attribute", "Part", "Condition", "Constraint", "Exit",
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

		self.vocab: dict[str, list] = {}
		self.vocabPlural: dict[str, str] = {}
		
		# Definitions that were imported (and possibly overwritten).
		self.old_imports = {}
		self.imports = {}
		
		# Term that are declared as imports.
		self.importable = {}
		
		self.lines: List[str] = []
		self.lineInfo: List[GambitLineInfo] = []
		self.lineNum: int = 0
		self.maxIndent: int = 0

		self.costTotal: int = 0
		self.sectionCosts = []

		self.gameTitle: str = "Unknown"

		self.currentDir: Optional[str] = None
	
		# Dict of defs that reference this def.
		self.referencedBy = {}

		self.initVocab()

		# Special actions with 0 cost.
		self.freeActions = {}
		self.initFreeActions()
	
	def initFreeActions(self) -> None:
		for a in FREE_ACTIONS:
			self.freeActions[a] = True
	
	def initVocab(self) -> None:
		for key in BASE_TYPES:
			self.addVocab(key, None, ["BASE"])
	
	def loadImportableTerms(self, import_file) -> None:
		with open(import_file, 'r') as file:
			for line in file:
				try:
					lineinfo = GambitLineProcessor.processLine(line)
				except Exception as ex:
					self.errorLine(str(ex))

				if lineinfo:
					if lineinfo.lineType == "DEF":
						keyword = lineinfo.keyword
						plural = lineinfo.altKeyword
						self.importable[keyword] = plural

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
		print("WARNING: {0:s}".format(msg))

	def warningLine(self, msg: str) -> None:
		print("WARNING {0:d}: {1:s}".format(self.lineNum, msg))

	# ==========
	# Vocabulary and Cross-reference
	# ==========
	
	def addVocab(self, key: str, keyPlural: Optional[str], info: list) -> None:
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
		if self.debug:
			print("addVocab", key, keyPlural, info)
		
	def isVocab(self, word: str) -> bool:
		# Normalize plural forms.
		canonicalForm: str = word
		if word in self.vocabPlural:
			canonicalForm = self.vocabPlural[word]

		return canonicalForm in self.vocab
	
	def isDefinedTerm(self, term: str) -> bool:
		if self.isVocab(term):
			return True

		# Check for templates.
		template = GambitLineProcessor.isTemplate(term)
		if template:
			(keyword, param) = template
			return self.isVocab(keyword) and self.isVocab(param)

		return False

	def addOldImportTerm(self, key: str) -> None:
		self.old_imports[key] = True
	
	def addImportTerm(self, key: str) -> None:
		self.imports[key] = True
	
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

			if type == "SECTION":
				isVocabSection = False
				if r.lineComment == "Vocabulary":
					isVocabSection = True

			elif type == "DEF" or type == "TEMPLATE":
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

			elif type in ["DESC", "CONSTRAINT"]:
				zeroCost = False
				line = r.line

				# Free actions are free.
				if line in self.freeActions:
					zeroCost = True

				# Lines that consist entirely of a single defined term are free.
				# The cost comes from the definition.
				if self.isDefinedTerm(line):
					zeroCost = True

				# TODO: Better detection of possible missing imports.
				# This will only catch it if the import is the only thing on the line.
				if (not zeroCost) and (line in self.importable):
					self.warning(f"Possibly missing import for {line}")

				# Handle special cases with Vocab
				words = Tokenizer.tokenize(line)

				# Lines that consist entirely of a defined terms are free.
				allDefined = True
				for w in words:
					if not self.isDefinedTerm(w):
						allDefined = False
				if allDefined:
					zeroCost = True

				# Handle "Discard xxx"
				if len(words) == 2 and self.isDefinedTerm(words[0]):
					# Handle: "Discard it"
					if words[1] in FREE_SUFFIX_WORDS:
						zeroCost = True
					# Handle: "Discard x2"
					if re.match(r'x\d+$', words[1]):
						zeroCost = True
				# Handle "Success:" and "Success: DrawCard"
				if words[0][-1] == ':' and self.isDefinedTerm(words[0][0:-1]):
					if len(words) == 1 or  self.isDefinedTerm(words[1]):
						zeroCost = True
				
				if zeroCost:
					r.cost = 0
				else:
					currDefCost += 1
			
			elif not type in ['COMMENT', 'IMPORT', 'OLDIMPORT', 'NAME', 'SUBSECTION', 'BLANK']:
				self.error("Unhandled type in updateCosts: {0:s}".format(type))

	# Return true if the DEF at the given index has at least one DESC
	# associated with it.
	def defHasDesc(self, iDef):
		if not self.lineInfo[iDef].lineType in ["DEF", "TEMPLATE"]:
			self.error("Not a DEF on line {0:d}: {1:s}".format(iDef, self.lineInfo[iDef].lineType))
		maxLines = len(self.lineInfo)
		i = iDef + 1
		# Look ahead to search for DESC lines that follow the DEF.
		while i < maxLines:
			r = self.lineInfo[i]
			type = r.lineType
			if type in ['DEF', 'BLANK', 'TEMPLATE']:
				return False
			if type == 'DESC' and r.indent == 1:
				return True
			if not type in ['COMMENT', 'SECTION', 'SUBSECTION', 'CONSTRAINT']:
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
			if type in ["DEF", "TEMPLATE", "DESC", "CONSTRAINT"]:
				if r.cost:
					self.costTotal += r.cost
					cost += r.cost
			elif type == "SECTION":
				if currentSubsection:
					self.subsectionCosts[currentSection].append([currentSubsection, cost])
				elif currentSection:
					self.sectionCosts.append([currentSection, cost])
				currentSection = r.lineComment
				currentSubsection = None
				cost = 0
			elif type == "SUBSECTION":
				if currentSubsection:
					self.subsectionCosts[currentSection].append([currentSubsection, cost])
				else:
					self.sectionCosts.append([currentSection, cost])
				currentSubsection = r.lineComment
				if not currentSection in self.subsectionCosts:
					self.subsectionCosts[currentSection] = []
				cost = 0
			elif not type in ['COMMENT', 'IMPORT', 'OLDIMPORT', 'NAME', 'SECTION', 'SUBSECTION', 'BLANK']:
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
		if type == "OLDIMPORT":
			self.oldImportFile(lineinfo.data)
		elif type == "IMPORT":
			self.importTerms(lineinfo.data)
		elif type == "DEF":
			parent = lineinfo.parent
			if parent and not parent in self.vocab:
				self.errorLine(f"Unknown parent: {parent}")
			for t in lineinfo.types:
				if not t in self.vocab:
					self.errorLine(f"Unknown term: {t}")

			info = ["LOCAL", lineinfo.types]
			if parent:
				info.append(parent)
			self.addVocab(lineinfo.keyword, lineinfo.altKeyword, info)
		elif type == "TEMPLATE":
			info = ["LOCAL", "Verb", lineinfo.param]
			self.addVocab(lineinfo.keyword, None, info)
		elif type == "NAME":
			self.gameTitle = lineinfo.lineComment
		elif type == "ERROR":
			self.errorLine(lineinfo.lineComment)
		elif not type in ['COMMENT', 'CONSTRAINT', 'DESC', 'SECTION', 'SUBSECTION', 'BLANK']:
			self.error(f"Unhandled type in processLine: {type}")

		# Record the max indent level so that we can format the HTML table correctly.
		if lineinfo.indent > self.maxIndent:
			self.maxIndent = lineinfo.indent

	def importTerms(self, terms):
		for t in terms:
			if not t in self.importable:
				self.errorLine(f"Unknown term for import: {t}")
			keyword = t
			plural = self.importable[t]
			info = ["IMPORT", "_import.gm"]
			self.addVocab(keyword, plural, info)
			self.addImportTerm(keyword)

	def oldImportFile(self, name):
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
					if type == "DEF":
						keyword = lineinfo.keyword
						plural = lineinfo.altKeyword
						info = ["OLDIMPORT", name]
						self.addVocab(keyword, plural, info)
						self.addOldImportTerm(keyword)
	
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
			if type == "DEF":
				currDef = r.keyword
				for t in r.types:
					self.addRef(t, currDef)
				if r.parent:
					self.addRef(r.parent, currDef)
					r.setTokens(self.extractReference(i, f"{r.types[0]} of {r.parent}", currDef))
				else:
					r.setTokens(self.extractReference(i, ', '.join(r.types), currDef))
				self.extractReference(i, r.lineComment, currDef, True)
			elif type == "TEMPLATE":
				currDef = r.keyword
				self.addRef("Verb", currDef)
				r.setTokens(["Verb"])
				self.extractReference(i, r.lineComment, currDef, True)
			elif type == "DESC":
				r.setTokens(self.extractReference(i, r.line, currDef))
				self.extractReference(i, r.lineComment, currDef, True)
			elif type == "CONSTRAINT":
				r.setTokens(self.extractReference(i, r.line, currDef))
				self.extractReference(i, r.lineComment, currDef, True)
			elif not type in ['COMMENT', 'IMPORT', 'OLDIMPORT', 'NAME', 'SECTION', 'SUBSECTION', 'BLANK']:
				self.error("Unhandled type in extractAllReferences: {0:s}".format(type))
	
	# Record that |refTerm| is referenced by |refBy|.
	# |refBy| makes a reference to |refTerm|.
	def addRef(self, refTerm, refBy):
		if refTerm == refBy:
			return
		#if not refTerm in self.referencedBy:
		#	self.referencedBy[refTerm] = set()
		self.referencedBy[refTerm].add(refBy)

	def lookupCanonicalForm(self, word):
		# Strip non-alphanumeric from beginning/end of token.
		(prefix, word, postfix) = GambitLineProcessor.extractKeyword(word)
		if word in self.vocabPlural:
			return self.vocabPlural[word]
	
	def checkReferences(self):
		for k,v in self.referencedBy.items():
			# Ignore standard terms (entry points like "Setup").
			if k in STANDARD_TERMS:
				continue
			# If defined locally but no references.
			if self.vocab[k][0] == "LOCAL" and len(v) == 0:
				# Allow local definitions to overwrite imported defs.
				if not k in self.old_imports:
					msg = "Term is defined but never referenced: {0:s}".format(k)
					self.warning(msg) if self.useWarnings else self.error(msg)
			if self.vocab[k][0] == "IMPORT" and len(v) == 0:
				msg = f"Term is imported but never referenced: {k}"
				self.warning(msg) if self.useWarnings else self.error(msg)
	
	def extractReference(self, lineNum: int, line: str, currDef: str, inComment=False):
		if line == "":
			return
		newWords: List[Union[str, List[str]]] = []
		firstWord = True
		for word in Tokenizer.tokenize(line):
			# Skip over special initial characters.
			if firstWord and word == '*':
				newWords.append('*')
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
				self.addRef(keyword, currDef)
				self.addRef(param, currDef)
				newWords.append(["TREF", keyword, param])
				continue

			# Strip non-alphanumeric from beginning/end of token.
			# Also remove contraction endings like "'s".
			(prefix, word0, postfix) = GambitLineProcessor.extractKeyword(word)

			# Normalize plural forms.
			canonicalForm = word0
			if word0 in self.vocabPlural:
				canonicalForm = self.vocabPlural[word0]
			
			if canonicalForm in self.vocab:
				self.addRef(canonicalForm, currDef)
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
