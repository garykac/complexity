#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import sys
import traceback

from gambit import LineType, SectionName
from gambit_line_processor import GambitLineProcessor
from gambit_tokenizer import GambitTokenizer
from gambit_vocab import GambitVocab
from log import Log

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
	def __init__(self, vocab):
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
		isVocabSection = False
		currDef = -1
		currDefCost = 0
		for r in lineInfo:
			type = r.lineType

			if type == LineType.SECTION:
				isVocabSection = False
				if r.name == "Vocabulary":
					isVocabSection = True

			elif type == LineType.DEF or type == LineType.TEMPLATE:
				# DEF must always cost at least one in the Vocabulary section.
				if currDef != -1 and isVocabSection and currDefCost == 0:
					# Update previous Vocab def if doesn't have any cost.
					lineInfo[currDef].cost = 1

				currDef = r.lineNum - 1  # "-1" for 0-based index.
				currDefCost = 0

				# If a DEF has DESC indented under it, then the cost is
				# determined by the associated DESCs and the DEF itself is 0.
				# Otherwise (with no indented DESCs) the cost of the DEF is 1.
				if self.defHasDesc(lineInfo, currDef):
					# Set to None instead of 0 so that the cost column is left blank.
					r.cost = None

			elif type == LineType.VALUES:
				currDefCost += 1

			elif type in [LineType.DESC, LineType.CONSTRAINT]:
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
					Log.warning(f"Possibly missing import for {line}", r.lineNum)

				# Handle special cases with Vocab
				words = GambitTokenizer.split(line)

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
			
			elif not type in [LineType.COMMENT, LineType.IMPORT, LineType.GAME_IMPORT, LineType.NAME, LineType.SUBSECTION, LineType.BLANK]:
				Log.errorInternal(f"Unhandled type in updateCosts: {type}")

	# Return true if the DEF at the given index has at least one DESC
	# associated with it.
	def defHasDesc(self, lineInfo, iDef):
		if not lineInfo[iDef].lineType in [LineType.DEF, LineType.TEMPLATE]:
			Log.errorInternal(f"Not a DEF on line {iDef}: {lineInfo[iDef].lineType}")
		maxLines = len(lineInfo)
		i = iDef + 1
		# Look ahead to search for DESC lines that follow the DEF.
		while i < maxLines:
			r = lineInfo[i]
			type = r.lineType
			if type in [LineType.DEF, LineType.BLANK, LineType.TEMPLATE]:
				return False
			if type in [LineType.DESC, LineType.VALUES] and r.indent == 1:
				return True
			if not type in [LineType.COMMENT, LineType.SECTION, LineType.SUBSECTION, LineType.CONSTRAINT]:
				Log.errorInternal(f"Unhandled type in defHasDesc: {type}")
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

			if type in [
					LineType.DEF, LineType.TEMPLATE, LineType.DESC, LineType.CONSTRAINT,
					LineType.VALUES]:
				if r.cost:
					self.costTotal += r.cost
					cost += r.cost

			elif type == LineType.SECTION:
				if currentSubsection:
					self.subsectionCosts[currentSection].append([currentSubsection, cost])
				elif currentSection:
					self.sectionCosts.append([currentSection, cost])
				currentSection = r.name
				currentSubsection = None
				cost = 0

			elif type == LineType.SUBSECTION:
				if currentSubsection:
					self.subsectionCosts[currentSection].append([currentSubsection, cost])
				else:
					self.sectionCosts.append([currentSection, cost])
				currentSubsection = r.name
				if not currentSection in self.subsectionCosts:
					self.subsectionCosts[currentSection] = []
				cost = 0

			elif not type in [
					LineType.COMMENT, LineType.IMPORT, LineType.GAME_IMPORT, LineType.NAME,
					LineType.SECTION, LineType.SUBSECTION, LineType.BLANK]:
				Log.errorInternal(f"Unhandled type in calcTotalCost: {type}")
		
		# Record cost for last section.
		if currentSection:
			if currentSubsection:
				self.subsectionCosts[currentSection].append([currentSubsection, cost])
			else:
				self.sectionCosts.append([currentSection, cost])
	
	def getSummary(self):
		summary = []
		total = 0
		for s in self.sectionCosts:
			name, cost = s
			subs = []
			if name in self.subsectionCosts:
				# If there is a top-level cost for a section with subsections, then this
				# is the cost not associated with any of the subsections. We need to track
				# it in an unnamed subsection.
				if cost != 0:
					subs.append(['-', cost])
				for sub in self.subsectionCosts[name]:
					subName, subCost = sub
					cost += subCost
					subs.append([subName, subCost])
			total += cost
			
			if name != SectionName.ASSUMPTIONS:
				summary.append([name, cost, subs])
		return [total, summary]
