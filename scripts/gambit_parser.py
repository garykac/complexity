#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import traceback

from gambit_line_processor import GambitLineProcessor
from tokenizer import Tokenizer

FREE_ACTIONS = [
	"Then:",
	"Else:",
	"Otherwise:",
	"If you do:",
	"If you don't:",
	"If any of:",
	"If all of:",
	"For each Player:",
	"For each other Player:",
	"Choose one:",
	# Conditions
	"Any of:",
]

# Handle suffix words like "Discard it" or "Shuffle them"
FREE_SUFFIX_WORDS = [
	"it",
	"them",
]

class GambitParser:
	"""Parser for Gambit (.gm) files."""
	def __init__(self):
		self.debug = False
		self.useWarnings = True

		self.vocab = {}
		self.vocabPlural = {}
		
		# Definitions that were imported (and possibly overwritten).
		self.imports = {}
		
		self.lines = []
		self.lineNum = 0
		self.maxIndent = 0

		self.costTotal = 0
		self.sectionCosts = []

		self.gameTitle = "Unknown"

		self.currentDir = None
	
		# Dict of defs that reference this def.
		self.referencedBy = {}

		self.initVocab()

		# Special actions with 0 cost.
		self.freeActions = {}
		self.initFreeActions()
	
	def initFreeActions(self):
		for a in FREE_ACTIONS:
			self.freeActions[a] = True
	
	def initVocab(self):
		for key in ["Noun", "Verb", "Attribute", "Part", "Condition", "Constraint", "Exit"]:
			self.addVocab(key, None, ["BASE"])

	def errorLine(self, msg):
		print("LINE {0:d}: {1:s}".format(self.lineNum, self.currentLine))
		self.error(msg)

	def error(self, msg):
		print("ERROR: {0:s}".format(msg))
		traceback.print_exc()
		raise Exception(msg)
		#exit(0)

	def warning(self, msg):
		print("WARNING: {0:s}".format(msg))

	# ==========
	# Vocabulary and Cross-reference
	# ==========
	
	def addVocab(self, key, keyPlural, info):
		self.vocab[key] = info
		self.referencedBy[key] = set()

		# Simple default plurals.
		if keyPlural == None:
			if key[-1] == 's':
				keyPlural = key
			# Factory, Quarry, City, but not Donkey
			elif key[-2:] == 'ry' or key[-2:] == 'ty':
				keyPlural = key[0:-1] + "ies"
			else:
				keyPlural = key + "s"

		# Mapping from plural to canonical form.
		self.vocabPlural[keyPlural] = key
		if self.debug:
			print("addVocab", key, keyPlural, info)
		
	def isVocab(self, word):
		# Normalize plural forms.
		canonicalForm = word
		if word in self.vocabPlural:
			canonicalForm = self.vocabPlural[word]

		return canonicalForm in self.vocab
	
	def isDefinedTerm(self, term):
		if self.isVocab(term):
			return True

		# Check for templates.
		template = GambitLineProcessor.isTemplate(term)
		if template:
			(keyword, param) = template
			return self.isVocab(keyword) and self.isVocab(param)

		return False

	def addImportTerm(self, key):
		self.imports[key] = True
	
	# ==========
	# Calculating costs.
	# ==========
	
	# Update the costs of the individual lines.
	def updateCosts(self):
		maxLines = len(self.lines)
		for i in range(0, maxLines):
			r = self.lines[i]
			type = r['type']
			if type == "DEF" or type == "TEMPLATE":
				# If a DEF has DESC indented under it, then the cost is
				# determined by the associated DESCs and the DEF itself is 0.
				# Otherwise (with no DESCs) the cost of the DEF is 1.
				if self.defHasDesc(i):
					# Set to None instead of 0 so that the cost column is left blank.
					r['cost'] = None
			elif type in ["DESC", "CONSTRAINT"]:
				# Lines that consist entirely of a single defined term are free.
				# The cost comes from the definition.
				if self.isDefinedTerm(r['line']):
					r['cost'] = 0
				# Free actions are free.
				if r['line'] in self.freeActions:
					r['cost'] = 0

				# Handle special cases with Vocab
				words = Tokenizer.tokenize(r['line'])
				# Handle "Discard xxx"
				if len(words) == 2 and self.isDefinedTerm(words[0]):
					# Handle: "Discard it"
					if words[1] in FREE_SUFFIX_WORDS:
						r['cost'] = 0
					# Handle: "Discard x2"
					if re.match(r'x\d+$', words[1]):
						r['cost'] = 0
				# Handle "Success:" and "Success: DrawCard"
				if words[0][-1] == ':' and self.isDefinedTerm(words[0][0:-1]):
					if len(words) == 1 or  self.isDefinedTerm(words[1]):
						r['cost'] = 0
			elif not type in ['COMMENT', 'IMPORT', 'NAME', 'SECTION', 'SUBSECTION', 'BLANK']:
				self.error("Unhandled type in updateCosts: {0:s}".format(type))

	# Return true if the DEF at the given index has at least one DESC
	# associated with it.
	def defHasDesc(self, iDef):
		if not self.lines[iDef]['type'] in ["DEF", "TEMPLATE"]:
			self.error("Not a DEF on line {0:d}: {1:s}".format(iDef, self.lines[iDef]['type']))
		maxLines = len(self.lines)
		i = iDef + 1
		# Look ahead to search for DESC lines that follow the DEF.
		while i < maxLines:
			r = self.lines[i]
			type = r['type']
			if type in ['DEF', 'BLANK', 'TEMPLATE']:
				return False
			if type == 'DESC' and r['indent'] == 1:
				return True
			if not type in ['COMMENT', 'SECTION', 'SUBSECTION', 'CONSTRAINT']:
				self.error("Unhandled type in defHasDesc: {0:s}".format(type))
			i += 1
		return False
	
	# Calculate the total cost for the game.
	def calcTotalCost(self):
		self.costTotal = 0
		self.sectionCosts = []
		currentSection = None
		sectionCost = 0
		for r in self.lines:
			type = r['type']
			if type in ["DEF", "TEMPLATE"]:
				if r['cost']:
					self.costTotal += r['cost']
					sectionCost += r['cost']
			elif type in ["DESC", "CONSTRAINT"]:
				self.costTotal += r['cost']
				sectionCost += r['cost']
			elif type == "SECTION":
				if currentSection:
					self.sectionCosts.append([currentSection, sectionCost])
				currentSection = r['comment']
				sectionCost = 0
			elif not type in ['COMMENT', 'IMPORT', 'NAME', 'SECTION', 'SUBSECTION', 'BLANK']:
				self.error("Unhandled type in calcTotalCost: {0:s}".format(type))
		
		# Record cost for last section.
		if currentSection:
			self.sectionCosts.append([currentSection, sectionCost])
	
	# ==========
	# Process a Gambit file to calculate cost and generate HTML.
	# ==========
	
	def process(self, src_dir, filepath):
		self.currentDir = src_dir
		with open(filepath, 'r') as file:
			self.lineNum = 0
			for line in file:
				self.processLine(line)
		
		self.updateCosts()
		self.calcTotalCost()
		
		self.extractAllReferences()

	def processLine(self, line):
		self.currentLine = line
		self.lineNum += 1
		try:
			lineinfo = GambitLineProcessor.processLine(line)
		except Exception as ex:
			self.errorLine(str(ex))
		
		# |lineinfo| is a dict with:
		#   'type'
		#   'cost'
		#   'indent'
		#   'line'
		#   'comment'
		# plus additional values depending on the |type|.
		if lineinfo:
			self.lines.append(lineinfo)
			type = lineinfo['type']
			if type == "IMPORT":
				self.importFile(lineinfo['comment'])
			elif type == "DEF":
				parent = lineinfo['parent']
				if parent and not parent in self.vocab:
					self.errorLine("Unknown parent: {0:s}".format(parent))
				for t in lineinfo['types']:
					if not t in self.vocab:
						self.errorLine("Unknown term: {0:s}".format(t))

				info = ["LOCAL", lineinfo['types']]
				if parent:
					info.append(parent)
				self.addVocab(lineinfo['keyword'], lineinfo['alt-keyword'], info)
			elif type == "TEMPLATE":
				info = ["LOCAL", "Verb", lineinfo['param']]
				self.addVocab(lineinfo['keyword'], None, info)
			elif type == "NAME":
				self.gameTitle = lineinfo['comment']
			elif not type in ['COMMENT', 'CONSTRAINT', 'DESC', 'SECTION', 'SUBSECTION', 'BLANK']:
				self.error("Unhandled type in processLine: {0:s}".format(type))

			# Record the max indent level so that we can format the HTML table correctly.
			if lineinfo['indent'] > self.maxIndent:
				self.maxIndent = lineinfo['indent']

		return lineinfo

	def importFile(self, name):
		basename = os.path.basename(name)
		dirname = os.path.dirname(name)
		basename = self.convertInitialCapsToHyphenated(basename) + ".gm"
		with open(os.path.join(self.currentDir, dirname, basename), 'r') as file:
			for line in file:
				try:
					lineinfo = GambitLineProcessor.processLine(line)
				except Exception as ex:
					self.errorLine(str(ex))

				if lineinfo:
					type = lineinfo['type']
					if type == "DEF":
						keyword = lineinfo['keyword']
						plural = lineinfo['alt-keyword']
						info = ["IMPORT", name]
						self.addVocab(keyword, plural, info)
						self.addImportTerm(keyword)
	
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
		for r in self.lines:
			type = r['type']
			if type == "DEF":
				currDef = r['keyword']
				for t in r['types']:
					self.addRef(t, currDef)
				if r['parent']:
					self.addRef(r['parent'], currDef)
					r['tokens'] = self.extractReference(
						"{0:s} of {1:s}".format(r['types'][0], r['parent']), currDef)
				else:
					r['tokens'] = self.extractReference(', '.join(r['types']), currDef)
				self.extractReference(r['comment'], currDef, True)
			elif type == "TEMPLATE":
				currDef = r['keyword']
				self.addRef("Verb", currDef)
				r['tokens'] = ["Verb"]
				self.extractReference(r['comment'], currDef, True)
			elif type == "DESC":
				r['tokens'] = self.extractReference(r['line'], currDef)
				self.extractReference(r['comment'], currDef, True)
			elif type == "CONSTRAINT":
				(type, cost, indent, line, comment) = r
				r['tokens'] = self.extractReference(r['line'], currDef)
				self.extractReference(r['comment'], currDef, True)
			elif not type in ['COMMENT', 'IMPORT', 'NAME', 'SECTION', 'SUBSECTION', 'BLANK']:
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
			# If defined locally but no references.
			if self.vocab[k][0] == "LOCAL" and len(v) == 0:
				# Allow local definitions to overwrite imported defs.
				if not k in self.imports:
					msg = "Term is defined but never referenced: {0:s}".format(k)
					self.warning(msg) if self.useWarnings else self.error(msg)
	
	def extractReference(self, str, currDef, inComment=False):
		if str == "":
			return
		newWords = []
		firstWord = True
		for word in Tokenizer.tokenize(str):
			# Skip over special initial characters.
			if firstWord and word == '*':
				newWords.append('*')
				# Don't update firstWord since the next word might be capitalized.
				continue
				
			# Ignore strings.
			if word[0] == '"' and word[-1] == '"':
				newWords.append(word)
				continue

			# Look for template references.
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
					raise Exception('Unable to find definition for "{0:s}"'.format(word0))
				elif not firstWord and word0[0].isupper():
					raise Exception('Unable to find definition for "{0:s}"'.format(word0))
				newWords.append(word)

			firstWord = False
			if (word0 != "" and word0[-1] == '.') or (postfix != "" and postfix[-1] == '.'):
				firstWord = True

		return newWords
