#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import traceback

from gambit_line_processor import GambitLineProcessor

GM_CSS_PATH = "gm.css"

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
		self.showCost = False
		self.useWarnings = True

		self.reset()

		# Special actions with 0 cost.
		self.freeActions = {}
		self.initFreeActions()
	
	def reset(self):
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
	
	def showCostAtEnd(self):
		self.showCost = True
	
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
			# Factory, Quarry, but not Donkey
			elif key[-2] == 'ry':
				keyPlural = key[0:-2] + "ries"
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
				words = self.tokenize(r['line'])
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

	# This method is similar to calcKeywordLinks. When updating, consider if
	# changes are needed both places.
	def extractReference(self, str, currDef):
		for word in self.tokenize(str):
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

	# This method is similar to extractReferences. When updating, consider if
	# changes are needed both places.
	#
	# |line| - string to process
	# |required| - True if it should verify that the keyword is defined
	def calcKeywordLinks(self, line, required=False):
		words = []
		firstWord = True
		for word in self.tokenize(line):
			# Skip over special initial characters.
			if firstWord and word == '*':
				words.append('*')
				# Don't update firstWord since the next word might be capitalized.
				continue
				
			# Ignore strings.
			if word[0] == '"' and word[-1] == '"':
				words.append(word)
				continue

			# Look for template references.
			template = GambitLineProcessor.isTemplate(word)
			if template:
				(keyword, param) = template
				words.append('<a class="keyword" href="#{0:s}">{0:s}</a>&lt;<a class="keyword" href="#{1:s}">{1:s}</a>&gt;'
						.format(keyword, param))
				continue

			# Strip non-alphanumeric from beginning/end of keyword token.
			# Also remove contraction endings like "'s".
			(prefix, word, postfix) = GambitLineProcessor.extractKeyword(word)

			# Normalize plural forms.
			canonicalForm = word
			if word in self.vocabPlural:
				canonicalForm = self.vocabPlural[word]

			if canonicalForm in self.vocab:
				info = self.vocab[canonicalForm]
				scope = info[0]
				if scope == "BASE":
					words.append('{0:s}{1:s}{2:s}'.format(prefix, word, postfix))
				elif scope == "IMPORT":
					words.append('{0:s}<abbr title="Imported from {1:s}">{2:s}</abbr>{3:s}'
							.format(prefix, info[1], word, postfix))
					
				else:
					words.append('{0:s}<a class="keyword" href="#{1:s}">{2:s}</a>{3:s}'
							.format(prefix, canonicalForm, word, postfix))
			elif required and not firstWord and word[0].isupper():
				errorLine("...{0:s}".format(line),
						'Unable to find definition for "{0:s}"'.format(word))
			else:
				words.append('{0:s}{1:s}{2:s}'.format(prefix, self.htmlify(word), postfix))
			
			firstWord = False
			
		return self.untokenize(words)
		
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
	
	# ==========
	# Writing the HTML file
	# ==========
	
	def htmlify(self, str):
		str = str.replace("&", "&amp;")
		return str
	
	def writeTableRows(self, out):
		for r in self.lines:
			type = r['type']
			prefix = ""
			line = r['line']
			comment = r['comment']
			rowclass = None

			if type == "DEF":
				defn = self.calcDefinitionHtml(r['keyword'])
				prefix = "{0:s}: ".format(defn)
				if r['parent'] != None:
					line = '{0:s} of {1:s}'.format(r['types'][0], r['parent'])
				else:
					line = ', '.join(r['types'])
			elif type == "TEMPLATE":
				defn = self.calcTemplateHtml(r['keyword'], r['param'])
				prefix = "{0:s}: ".format(defn)
				line = "Verb"
			elif type == "CONSTRAINT":
				# &bull;&ddagger;&rArr;&oplus;&oast;&star;&starf;&diams;&xoplus;&Otimes;
				prefix = "&roplus; "
			elif type == "BLANK":
				prefix = "&nbsp;"
			elif type == "IMPORT":
				comment = "#import {0:s}".format(comment)
			elif type == "SECTION":
				rowclass = "section"
			elif type == "SUBSECTION":
				rowclass = "subsection"
			elif not type in ["COMMENT", "CONSTRAINT", "DESC", "NAME"]:
				error("Unrecognized type in writeTableRows: {0:s}".format(type))

			if rowclass:
				row = '<tr class="{0:s}">'.format(rowclass)
			else:
				row = '<tr>'

			row += self.calcTableRowCostColumn(r['cost'])

			if rowclass:
				row += '<td colspan={0:d}>{1:s}</td>'.format(self.maxIndent+1, comment)
			else:
				row += self.calcTableRowDescColumn(r['indent'], line, comment, prefix)

			row += '</tr>\n'

			out.write(row)

	def calcTableRowCostColumn(self, cost):
		if cost != None:
			return '<td class="cost">{0:d}</td>'.format(cost)
		return '<td class="cost"></td>'
	
	def calcTableRowDescColumn(self, indent, line, comment, descPrefix = ""):
		row = '<td></td>' * indent

		colspan = self.maxIndent + 1 - indent
		if colspan == 1:
			row += '<td class="desc">'
		else:
			row += '<td class="desc" colspan={0:d}>'.format(colspan)
			
		if line != "" or descPrefix != "":
			row += descPrefix
			row += self.calcKeywordLinks(line, required=True)
			if comment != "":
				row += ' &nbsp;&nbsp;&nbsp;&mdash; '
		if comment != "":
			row += '<span class="comment">{0:s}</span>'.format(self.htmlify(comment))
		row += '</td>'
		return row
	
	def calcTemplateHtml(self, keyword, param):
		refs = []
		if keyword in self.referencedBy:
			refs = sorted(self.referencedBy[keyword])
		defn = '<div class="def-container">'
		defn += '<a class="def" id="{0:s}">{0:s}&lt;{1:s}&gt;</a>'.format(keyword, param)

		defn += '<div class="def-menu">'
		if len(refs) != 0:
			defn += '<div class="def-menu-title">Referenced&nbsp;by:</div>'
			for ref in refs:
				defn += '<a href="#{0:s}">{0:s}</a>'.format(ref)
		else:
			defn += '<div class="def-menu-title">No&nbsp;references</div>'
		defn += '</div>'
		defn += '</div>'
		return defn

	def calcDefinitionHtml(self, keyword):
		refs = []
		if keyword in self.referencedBy:
			refs = sorted(self.referencedBy[keyword])
		defn = '<div class="def-container">'
		defn += '<a class="def" id="{0:s}">{0:s}</a>'.format(keyword)

		defn += '<div class="def-menu">'
		if len(refs) != 0:
			defn += '<div class="def-menu-title">Referenced&nbsp;by:</div>'
			for ref in refs:
				defn += '<a href="#{0:s}">{0:s}</a>'.format(ref)
		else:
			defn += '<div class="def-menu-title">No&nbsp;references</div>'
		defn += '</div>'
		defn += '</div>'
		return defn

	def writeTableHeader(self, out):
		out.write('<table>\n')

		colgroup = '<colgroup><col class="cost">'
		for x in range(self.maxIndent):
			colgroup += '<col class="indent">'
		colgroup += '<col></colgroup>\n'
		out.write(colgroup)

		thead = '<thead><tr><th class="cost">Cost</th>'
		thead += '<th colspan={0:d}>Description</th>'.format(self.maxIndent+1)
		thead += '</tr></thead>\n'
		out.write(thead)

	def writeTableFooter(self, out):
		out.write('</table>\n')

	def writeHtml(self, outpath):
		with open(outpath, 'w') as out:
			self.writeHtmlHeader(out, self.gameTitle, self.costTotal)
			self.writeTableHeader(out)
			self.writeTableRows(out)
			self.writeTableFooter(out)
			self.writeHtmlFooter(out)

	def writeHtmlHeader(self, out, title, costTotal):
		out.write('<!DOCTYPE html>\n')
		out.write('<html lang="en">\n')
		out.write('<head>\n')
		out.write('	<meta charset="utf-8" />\n')
		out.write('	<meta http-equiv="X-UA-Compatible" content="IE=edge" />\n')
		out.write('	<meta name="viewport" content="width=device-width, initial-scale=1" />\n')
		out.write('	<title>{0:s}</title>\n'.format(self.htmlify(title)))
		out.write('	<link rel="preconnect" href="https://fonts.googleapis.com">\n')
		out.write('	<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n')
		out.write('	<link href="https://fonts.googleapis.com/css2?family=Noto+Sans:ital,wght@0,400;0,600;0,700;1,400;1,600;1,700&display=swap" rel="stylesheet">\n')
		out.write('<style>\n')

		with open(GM_CSS_PATH, 'r') as file:
			for line in file:
				out.write(line)

		out.write('</style>\n')
		out.write('</head>\n')
		out.write('<body>\n')
		out.write('<div class="container">\n')
		out.write('<div class="title">{0:s}</div>\n'.format(title))
		out.write('<div class="summary">Learning Complexity: {0:d}</div>\n'.format(costTotal))
	
	def writeHtmlFooter(self, out):
		out.write('<div class="footer">&nbsp;</div>\n')
		out.write('</div>\n')
		out.write('</body>\n')
		out.write('</html>\n')

	# ==========
	# Parsing and Tokenizing
	# ==========
	
	def tokenize(self, str):
		out = []
		substrings = str.split('"')
		for i in range(0, len(substrings)):
			if i % 2:
				out.append('"{0:s}"'.format(substrings[i]))
			else:
				out.extend(substrings[i].split())
		return out

	def untokenize(self, tokens):
		return ' '.join(tokens)
