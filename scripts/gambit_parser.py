#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import sys
import traceback

from gambit import LineType
from gambit_calc import GambitCalc
from gambit_line_processor import GambitLineProcessor
from gambit_vocab import GambitVocab
from log import Log

from typing import Optional, List, Union

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

		if 'warnings' in options:
			self.useWarnings = options['warnings']
		if 'verbose' in options:
			self.verbose = options['verbose']

		self.lines: List[str] = []
		self.lineInfo: List[GambitLineInfo] = []
		self.lineNum: int = 0
		self.maxIndent: int = 0

		self.gameTitle: str = "Unknown"

		self.currentDir: Optional[str] = None
	
		self.vocab = GambitVocab()
		self.calc = GambitCalc(self.vocab)

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
			Log.line(num, self.lines[num-1])
		self.error(msg)

	def error(self, msg: str) -> None:
		Log.error(msg)

	def warning(self, msg: str) -> None:
		if not self.useWarnings:
			self.error(msg)
		Log.warning(msg)

	def warningLine(self, msg: str) -> None:
		num = self.lineNum
		Log.line(num, self.lines[num-1])
		Log.warning(msg, num)

	# ==========
	# Calculating costs.
	# ==========
	
	def updateCosts(self):
		# Update the costs of the individual lines.
		self.calc.updateCosts(self.lineInfo)

		# Calculate the total cost for the game.
		self.calc.calcTotalCost(self.lineInfo)

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
					self.warningLine(f"Unresolved TODO {line.strip()}")
		
		self.extractAllReferences()

		self.updateCosts()
		
	def processLine(self, line):
		self.lineNum += 1
		self.lines.append(line.rstrip())

		lineinfo = GambitLineProcessor.processLine(self.lineNum, line)
		
		# |lineinfo| is GambitLineInfo.
		self.lineInfo.append(lineinfo)
		type = lineinfo.lineType
		if type == LineType.GAME_IMPORT:
			self.importGameFile(lineinfo.data)
		elif type == LineType.IMPORT:
			self.vocab.importTerms(lineinfo.data)
		elif type == LineType.DEF:
			parent = lineinfo.parent
			if parent and not self.vocab.contains(parent):
				self.errorLine(f"Unknown parent: {parent}")
			for t in lineinfo.types:
				if not self.vocab.contains(t):
					self.errorLine(f"Unknown term: {t}")

			self.vocab.addDef(lineinfo.keyword, lineinfo.altKeyword, lineinfo.types, parent)
		elif type == LineType.VALUES:
			items = [x.strip() for x in lineinfo.line.split(',')]
			for i in items:
				self.vocab.addDef(i, None, "Value", None)
		elif type == LineType.TEMPLATE:
			self.vocab.addTemplate(lineinfo.keyword, lineinfo.param)
		elif type == LineType.NAME:
			self.gameTitle = lineinfo.name
		elif type == "ERROR":
			self.errorLine(lineinfo.lineComment)
		elif not type in [
				LineType.COMMENT, LineType.CONSTRAINT, LineType.DESC, LineType.SECTION,
				LineType.SUBSECTION, LineType.BLANK]:
			self.error(f"Unhandled type in processLine: {type}")

		# Record the max indent level so that we can format the HTML table correctly.
		if lineinfo.indent > self.maxIndent:
			self.maxIndent = lineinfo.indent

	def importGameFile(self, name):
		basename = os.path.basename(name)
		dirname = os.path.dirname(name)
		basename = self.convertInitialCapsToHyphenated(basename) + ".gm"
		with open(os.path.join(self.currentDir, dirname, basename[0], basename), 'r') as file:
			for line in file:
				lineinfo: GambitLineInfo = GambitLineProcessor.processLine(self.lineNum, line)

				if lineinfo:
					type = lineinfo.lineType
					if type == LineType.DEF:
						keyword = lineinfo.keyword
						plural = lineinfo.altKeyword
						self.vocab.addGameImport(keyword, plural, name)
					elif type == LineType.VALUES:
						items = [x.strip() for x in lineinfo.line.split(',')]
						for i in items:
							self.vocab.addGameImport(i, None, name)
	
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
		for lineInfo in self.lineInfo:
			currDef = lineInfo.extractReferences(currDef, self.vocab)
	
	def checkReferences(self):
		self.vocab.checkReferences()
	
