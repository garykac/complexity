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
	"Choose one:",
	"Any of:",
]

# Handle suffix words like "Discard it" or "Shuffle them"
FREE_SUFFIX_WORDS = [
	"it",
	"them",
]

def warning(msg):
	print("WARNING: {0:s}".format(msg))

def error(msg):
	print("ERROR: {0:s}".format(msg))
	raise Exception(msg)

def errorLine(line, msg):
	print(line)
	error(msg)

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
					if re.match('x\d+$', words[1]):
						r['cost'] = 0
				# Handle "Success:" and "Success: DrawCard"
				if words[0][-1] == ':' and self.isDefinedTerm(words[0][0:-1]):
					if len(words) == 1 or  self.isDefinedTerm(words[1]):
						r['cost'] = 0
			elif not type in ['COMMENT', 'IMPORT', 'NAME', 'SECTION', 'SUBSECTION', 'BLANK']:
				error("Unhandled type in updateCosts: {0:s}".format(type))

	# Return true if the DEF at the given index has at least one DESC
	# associated with it.
	# If the DEF has at least one DESC, then the cost comes from the DESC lines.
	# Otherwise, the DEF is assigned a cost of 1.
	def defHasDesc(self, iDef):
		maxLines = len(self.lines)
		i = iDef + 1
		# Look ahead to search for DESC lines that follow the DEF.
		while i < maxLines:
			r = self.lines[i]
			type = r['type']
			if type in ['DEF', 'BLANK']:
				return False
			if type == 'DESC' and r['indent'] == 1:
				return True
			if not type in ['COMMENT', 'SECTION', 'SUBSECTION', 'CONSTRAINT']:
				error("Unhandled type in defHasDesc: {0:s}".format(type))
			i += 1
		return False
	
	# Calculate the total cost for the game.
	def calcTotalCost(self):
		self.costTotal = 0
		for r in self.lines:
			type = r['type']
			if type == "DEF" or type == "TEMPLATE":
				if r['cost']:
					self.costTotal += r['cost']
			elif type in ["DESC", "CONSTRAINT"]:
				self.costTotal += r['cost']
			elif not type in ['COMMENT', 'IMPORT', 'NAME', 'SECTION', 'SUBSECTION', 'BLANK']:
				error("Unhandled type in calcTotalCost: {0:s}".format(type))
	
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
		self.lineNum += 1
		try:
			lineinfo = GambitLineProcessor.processLine(line)
		except Exception as ex:
			errorLine("LINE {0:d}: {1:s}".format(self.lineNum, line.rstrip()), str(ex))
			traceback.print_exc()
		
		if lineinfo:
			self.lines.append(lineinfo)
			type = lineinfo['type']
			if type == "IMPORT":
				self.importFile(lineinfo['comment'])
			elif type == "DEF":
				parent = lineinfo['parent']
				if parent and not parent in self.vocab:
					error("Unknown parent: {0:s}".format(parent))
				for t in lineinfo['types']:
					if not t in self.vocab:
						error("Unknown term: {0:s}".format(t))

				info = ["LOCAL", lineinfo['types']]
				if parent:
					info.append(parent)
				self.addVocab(lineinfo['keyword'], lineinfo['alt-keyword'], info)
			elif type == "TEMPLATE":
				info = ["LOCAL", "Verb", lineinfo['param']]
				self.addVocab(lineinfo['keyword'], None, info)
			elif type == "NAME":
				self.gameTitle = lineinfo['comment']

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
					errorLine("IMPORT {0:s}: {1:s}".format(name, line.rstrip()), str(ex))
					traceback.print_exc()

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
				self.extractReference(r['comment'], currDef)
			elif type == "TEMPLATE":
				currDef = r['keyword']
				self.addRef("Verb", currDef)
				self.extractReference(r['comment'], currDef)
			elif type == "DESC":
				self.extractReference(r['line'], currDef)
				self.extractReference(r['comment'], currDef)
			elif type == "CONSTRAINT":
				(type, cost, indent, line, comment) = r
				self.extractReference(r['line'], currDef)
				self.extractReference(r['comment'], currDef)
			elif not type in ['COMMENT', 'IMPORT', 'NAME', 'SECTION', 'SUBSECTION', 'BLANK']:
				error("Unhandled type in extractAllReferences: {0:s}".format(type))
	
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
					warning(msg) if self.useWarnings else error(msg)
	
	# This method is similar to calcKeywordLinks. When updating, consider if
	# changes are needed both places.
	def extractReference(self, str, currDef):
		for word in Tokenizer.tokenize(str):
			# Ignore strings (or first/last word in a string).
			# Note: This will not skip middle words in string: "skip not not not skip"
			if word[0] == '"' or word[-1] == '"':
				continue

			# Look for template references.
			template = GambitLineProcessor.isTemplate(word)
			if template:
				(keyword, param) = template
				self.addRef(keyword, currDef)
				self.addRef(param, currDef)
				continue

			# Strip non-alphanumeric from beginning/end of token.
			# Also remove contraction endings like "'s".
			(prefix, word, postfix) = GambitLineProcessor.extractKeyword(word)

			# Normalize plural forms.
			canonicalForm = word
			if word in self.vocabPlural:
				canonicalForm = self.vocabPlural[word]
			
			if canonicalForm in self.vocab:
				self.addRef(canonicalForm, currDef)

