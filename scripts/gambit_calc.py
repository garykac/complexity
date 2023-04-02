#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import sys
import traceback

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

class GambitCalc:
	"""Cost calculations for Gambit (.gm) files."""
	def __init__(self, parser, vocab):
		self.parser = parser
		self.vocab = vocab
		
		self.costTotal: int = 0
		self.sectionCosts = []
		self.subsectionCosts = {}

		# Special actions with 0 cost.
		self.freeActions = {}
		for a in FREE_ACTIONS:
			self.freeActions[a] = True
	
	# ==========
	# Calculating costs.
	# ==========
	
	# Update the costs of the individual lines.
	def updateCosts(self, lineInfo):
		maxLines = len(lineInfo)
		isVocabSection = False
		currDef = -1
		currDefCost = 0
		for i in range(0, maxLines):
			r = lineInfo[i]
			type = r.lineType

			if type == LT_SECTION:
				isVocabSection = False
				if r.name == "Vocabulary":
					isVocabSection = True

			elif type == LT_DEF or type == LT_TEMPLATE:
				# DEF must alwyas cost at least one.
				if currDef != -1 and isVocabSection and currDefCost == 0:
					lineInfo[currDef].cost = 1

				currDef = i
				currDefCost = 0

				# If a DEF has DESC indented under it, then the cost is
				# determined by the associated DESCs and the DEF itself is 0.
				# Otherwise (with no DESCs) the cost of the DEF is 1.
				if self.defHasDesc(lineInfo, i):
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
	def defHasDesc(self, lineInfo, iDef):
		if not lineInfo[iDef].lineType in [LT_DEF, LT_TEMPLATE]:
			self.error("Not a DEF on line {0:d}: {1:s}".format(iDef, lineInfo[iDef].lineType))
		maxLines = len(lineInfo)
		i = iDef + 1
		# Look ahead to search for DESC lines that follow the DEF.
		while i < maxLines:
			r = lineInfo[i]
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
	def calcTotalCost(self, lineInfo):
		self.costTotal = 0
		self.sectionCosts = []
		self.subsectionCosts = {}
		currentSection = None
		currentSubsection = None
		cost = 0
		for r in lineInfo:
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
				currentSection = r.name
				currentSubsection = None
				cost = 0
			elif type == LT_SUBSECTION:
				if currentSubsection:
					self.subsectionCosts[currentSection].append([currentSubsection, cost])
				else:
					self.sectionCosts.append([currentSection, cost])
				currentSubsection = r.name
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
