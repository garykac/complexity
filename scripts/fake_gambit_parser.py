#!/usr/bin/env python
# -*- coding: utf-8 -*-

from gambit_line_info import GambitLineInfo

class FakeGambitParser:
	"""Process a single line from a Gambit (.gm) file."""
	def __init__(self):
		self.lineNum = 0
		
		self.lines = []
		self.lineInfo = []
	
	def addBlankLine(self):
		self.lineNum += 1

		self.lines.append("")
		
		lineInfo = GambitLineInfo.comment(self.lineNum, 0, "")
		self.lineInfo.append(lineInfo)

	def addDefLine(self, keyword, type):
		self.lineNum += 1

		self.lines.append(f"{keyword}: {type}")
		
		lineInfo = GambitLineInfo.definition(self.lineNum, [keyword], type, "")
		self.lineInfo.append(lineInfo)

	def addDescLine(self, indent, desc, comment):
		self.lineNum += 1

		line = ("\t" * indent) + desc
		if comment:
			line += f" // {comment}"
		self.lines.append(line)

		lineInfo = GambitLineInfo.description(self.lineNum, indent, desc, comment)
		self.lineInfo.append(lineInfo)

	def addTemplateLine(self, keyword, param, comment):
		self.lineNum += 1

		line = f"{keyword}<{param}>"
		if comment:
			line += f" // {comment}"
		self.lines.append(line)

		lineInfo = GambitLineInfo.templateDefinition(self.lineNum, keyword, param, comment)
		self.lineInfo.append(lineInfo)
