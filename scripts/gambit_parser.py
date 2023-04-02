#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import sys
import traceback

from gambit import (LT_COMMENT, LT_BLANK,
					LT_NAME, LT_IMPORT, LT_GAME_IMPORT, LT_SECTION, LT_SUBSECTION,
					LT_DEF, LT_TEMPLATE, LT_CONSTRAINT, LT_DESC)
from gambit_calc import GambitCalc
from gambit_line_processor import GambitLineProcessor
from gambit_vocab import GambitVocab
from tokenizer import Tokenizer

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
		self.quitOnError: bool = False

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
	
		self.vocab = GambitVocab(self)
		self.calc = GambitCalc(self, self.vocab)

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
		self.calc.updateCosts(self.lineInfo)

	# Return true if the DEF at the given index has at least one DESC
	# associated with it.
	def defHasDesc(self, iDef):
		return False
	
	# Calculate the total cost for the game.
	def calcTotalCost(self):
		self.calc.calcTotalCost(self.lineInfo)
	
	def getVocabCost(self):
		return self.calc.getVocabCost()

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
			self.gameTitle = lineinfo.name
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
			currDef = self.vocab.extractReferences(i, currDef, self.lineInfo[i])
	
	def checkReferences(self):
		self.vocab.checkReferences()
	
