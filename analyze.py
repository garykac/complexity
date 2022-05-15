#!/usr/bin/env python
# -*- coding: utf-8 -*-

import getopt
import os
import re
import sys

KEYWORD = "[A-Z][A-Za-z0-9_]*"
TAB_SIZE = 4

GM_CSS_PATH = "gm.css"
OUTPUT_DIR = "games"

FREE_ACTIONS = [
	"Then:",
	"Else:",
	"Otherwise:",
	"If you do:",
	"If any of:",
	"For each Player:",
]

def error(msg):
	print("ERROR: {0:s}".format(msg))
	exit()

def errorLine(line, msg):
	print(line)
	error(msg)

class GambitParser:
	"""Parser for Gambit (.gm) files."""
	def __init__(self):
		self.vocab = {}
		self.initVocab()

		self.vocabPlural = {}
		self.lines = []
		self.maxIndent = 0
		self.costTotal = 0
		self.gameTitle = "Unknown"

		# Special actions with 0 cost.
		self.freeActions = {}
		self.initFreeActions()
		
		# Dict of defs that reference this def.
		self.referencedBy = {}
	
	def initFreeActions(self):
		for a in FREE_ACTIONS:
			self.freeActions[a] = True
	
	def initVocab(self):
		self.vocab["Noun"] = ["BASE"]
		self.vocab["Verb"] = ["BASE"]
		self.vocab["Attribute"] = ["BASE"]
		self.vocab["Part"] = ["BASE"]
		self.vocab["Condition"] = ["BASE"]
		self.vocab["Constraint"] = ["BASE"]

	def calcIndent(self, str):
		m = re.match("(\t*)", str)
		if m:
			return len(m.group(1))
		m = re.match("( *)", str)
		if m:
			return len(m.group(1)) / TAB_SIZE
		return 0
	
	# ==========
	# Helper routines for adding new lines.
	# ==========
	
	def addBlankLine(self):
		self.lines.append(["BLANK"])

	def addSectionLine(self, title):
		self.lines.append(["SECTION", title])

	def addTitleLine(self, title):
		self.lines.append(["TITLE", title])

	def addCommentLine(self, indent, comment):
		if indent > self.maxIndent:
			self.maxIndent = indent
		self.lines.append(["COMMENT", indent, comment])

	def addDefinitionLine(self, cost, keyword, type, parent, comment):
		self.lines.append(["DEF", cost, keyword, type, parent, comment])
		
	def addConstraintLine(self, cost, indent, line, comment):
		if indent > self.maxIndent:
			self.maxIndent = indent
		self.lines.append(["CONSTRAINT", cost, indent, line, comment])

	def addDescriptionLine(self, cost, indent, line, comment):
		if indent > self.maxIndent:
			self.maxIndent = indent
		self.lines.append(["DESC", cost, indent, line, comment])

	def addComment(self, line, comment):
		indent = self.calcIndent(line)
		type = "COMMENT"
		if comment == "":
			self.addBlankLine()
			return
		elif indent == 0:
			if comment.startswith("SECTION:"):
				self.addSectionLine(comment[8:].strip())
				return
			elif comment.startswith("NAME:"):
				self.gameTitle = comment[5:].strip()
				self.addTitleLine(self.gameTitle)
				return
		self.addCommentLine(indent, comment)

	def addDefinition(self, keyword, type, comment):
		parent = None
		m = re.match("(" + KEYWORD + ")\s+of\s+(" + KEYWORD + ")", type)
		if m:
			type = m.group(1)
			parent = m.group(2)
			info = ["LOCAL", type, parent]
			if not parent in self.vocab:
				errorLine(self.originalLine, "Unknown parent: {0:s}".format(parent))
		else:
			info = ["LOCAL", type]
		if not type in self.vocab:
			errorLine(self.originalLine, "Unknown term: {0:s}".format(type))
		self.vocab[keyword] = info
		
		# Mapping from plural to canonical form.
		self.vocabPlural[keyword+"s"] = keyword
		
		self.addDefinitionLine(1, keyword, type, parent, comment)

	def addConstraint(self, line, comment):
		indent = self.calcIndent(line)
		line = line.strip()
		line = line[1:]  # Remove the leading '!'
		line = line.strip()
		self.addConstraintLine(1, indent, line, comment)

	def addDescription(self, line, comment):
		indent = self.calcIndent(line)
		line = line.strip()
		cost = 1
		# Entries in a lookup table.
		if line[0] == '*':
			cost = 0
		self.addDescriptionLine(cost, indent, line, comment)

	# ==========
	# Process a Gambit file to calculate cost and generate HTML.
	# ==========
	
	def process(self, filepath):
		with open(filepath, 'r') as file:
			for line in file:
				self.originalLine = line.rstrip()
				comment = ""
				
				if line.startswith("#include"):
					self.importFile(os.path.dirname(filepath), line[8:].strip())
					self.addComment("", line.strip())
					continue

				# Handle comments and empty lines.
				m = re.match("(.*?)//(.*)", line)
				if m:
					line = m.group(1)
					comment = m.group(2)
				comment = comment.strip()
				if line.strip() == "":
					self.addComment(line, comment)
					continue
				line = line.rstrip()

				# NEW_TYPE: TYPE
				# NEW_ATTRIBUTE: Attribute of TYPE
				m = re.match("(" + KEYWORD + "):\s*(.*)", line)
				if m:
					keyword = m.group(1)
					type = m.group(2)
					self.addDefinition(keyword, type, comment)
					continue

				if line.strip().startswith("!"):
					self.addConstraint(line, comment)
					continue
					
				self.addDescription(line, comment)
		
		self.updateCosts()
		self.calcCost()
		
		self.extractAllReferences()
		
		self.writeHtml(filepath)
	
	def importFile(self, dir, name):
		basename = os.path.basename(name)
		dirname = os.path.dirname(name)
		basename = self.convertInitialCapsToHyphenated(basename) + ".gm"
		with open(os.path.join(dir, dirname, basename), 'r') as file:
			for line in file:
				m = re.match("(" + KEYWORD + "):\s*(.*)", line)
				if m:
					keyword = m.group(1)
					self.vocab[keyword] = ["IMPORT", name]
					self.vocabPlural[keyword+"s"] = keyword
	
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
		
	def updateCosts(self):
		maxLines = len(self.lines)
		for i in range(0, maxLines):
			r = self.lines[i]
			type = r[0]
			if type == "DEF":
				# If a DEF has DESC indented under it, then the cost is
				# determined by the DESCs and the DEF is 0.
				# Otherwise the cost of the DEF is 1.
				if self.defHasDesc(i):
					r[1] = None
			elif type in ["DESC", "CONSTRAINT"]:
				(type, cost, indent, line, comment) = r
				if line in self.vocab:
					r[1] = 0
				if line in self.freeActions:
					r[1] = 0
				# Handle special case like: Discard it
				words = line.split()
				if len(words) == 2 and words[0] in self.vocab and words[1] == "it":
					r[1] = 0					
			elif not type in ['COMMENT', 'SECTION', 'TITLE', 'BLANK']:
				error("Unhandled type in updateCosts: {0:s}".format(type))

	# Return true if the DEF at the given index has at least one DESC
	# associated with it.
	def defHasDesc(self, iDef):
		maxLines = len(self.lines)
		i = iDef + 1
		while i < maxLines:
			r = self.lines[i]
			type = r[0]
			if type in ['DEF', 'BLANK']:
				return False
			if type == 'DESC' and r[2] == 1:
				return True
			if not type in ['COMMENT', 'SECTION', 'TITLE', 'CONSTRAINT']:
				error("Unhandled type in defHasDesc: {0:s}".format(type))
			i += 1
		return False
	
	def calcCost(self):
		self.costTotal = 0
		for r in self.lines:
			type = r[0]
			if type == "DEF":
				if r[1]:
					self.costTotal += r[1]
			elif type in ["DESC", "CONSTRAINT"]:
				self.costTotal += r[1]
			elif not type in ['COMMENT', 'SECTION', 'TITLE', 'BLANK']:
				error("Unhandled type in calcCost: {0:s}".format(type))
	
	def extractAllReferences(self):
		self.referencedBy = {}
		currDef = None
		for r in self.lines:
			type = r[0]
			if type == "DEF":
				(type, cost, keyword, type, parent, comment) = r
				currDef = keyword
				self.addRef(type, currDef)
				if parent:
					self.addRef(parent, currDef)
				self.extractReference(comment, currDef)
			elif type == "DESC":
				(type, cost, indent, line, comment) = r
				self.extractReference(line, currDef)
				self.extractReference(comment, currDef)
			elif type == "CONSTRAINT":
				(type, cost, indent, line, comment) = r
				self.extractReference(line, currDef)
				self.extractReference(comment, currDef)
			elif not type in ['COMMENT', 'SECTION', 'TITLE', 'BLANK']:
				error("Unhandled type in extractAllReferences: {0:s}".format(type))
		
	def addRef(self, ref, referencedBy):
		if ref == referencedBy:
			return
		if not ref in self.referencedBy:
			self.referencedBy[ref] = set()
		self.referencedBy[ref].add(referencedBy)

	# This method is similar to calcKeywordLinks. When updating, consider if
	# changes are needed both places.
	def extractReference(self, str, currDef):
		for word in str.split():
			# Strip non-alphanumeric from beginning/end of token.
			# Also remove contraction endings like "'s".
			m = re.match("([^A-Za-z0-9_]*)(" + KEYWORD + ")([^A-Za-z0-9_]*.*)", word)
			if m:
				word = m.group(2)

			# Normalize plural forms.
			canonicalForm = word
			if word in self.vocabPlural:
				canonicalForm = self.vocabPlural[word]
			
			if canonicalForm in self.vocab:
				self.addRef(canonicalForm, currDef)

	# ==========
	# Writing the table rows with the Gambit description.
	# ==========
	
	def writeTableRows(self, out):
		for r in self.lines:
			type = r[0]
			
			if type == "DESC":
				(type, cost, indent, line, comment) = r
				row = '<tr>'
				row += self.calcTableRowCostColumn(cost)
				row += self.calcTableRowDescColumn(indent, line, comment)
				row += '</tr>\n'
			elif type == "DEF":
				(type, cost, keyword, type, parent, comment) = r
				row = '<tr>'
				row += self.calcTableRowCostColumn(cost)
				defn = self.calcDefinition(keyword)
				fulltype = type
				if parent != None:
					fulltype += ' of {0:s}'.format(parent)
				row += self.calcTableRowDescColumn(0, fulltype, comment, "{0:s}: ".format(defn))
				row += '</tr>\n'
			elif type == "CONSTRAINT":
				(type, cost, indent, line, comment) = r
				row = '<tr>'
				row += self.calcTableRowCostColumn(cost)
				# &bull;&ddagger;&rArr;&oplus;&oast;&star;&starf;&diams;&xoplus;&Otimes;
				row += self.calcTableRowDescColumn(indent, line, comment, "&roplus; ")
				row += '</tr>\n'
			elif type == "BLANK":
				(type) = r
				row = '<tr>'
				row += self.calcTableRowCostColumn(None)
				row += self.calcTableRowDescColumn(0, "&nbsp;", "")
				row += '</tr>\n'
			elif type == "COMMENT":
				(type, indent, comment) = r
				row = '<tr>'
				row += self.calcTableRowCostColumn(None)
				row += self.calcTableRowDescColumn(indent, "", comment)
				row += '</tr>\n'
			elif type == "SECTION":
				(type, title) = r
				row = '<tr class="section">'
				row += self.calcTableRowCostColumn(None)
				row += '<td colspan={0:d}>{1:s}</td>'.format(self.maxIndent+1, title)
				row += '</tr>\n'
			elif type == "TITLE":
				(type, title) = r
				row = '<tr>'
				row += self.calcTableRowCostColumn(None)
				row += '<td colspan={0:d}>{1:s}</td>'.format(self.maxIndent+1, title)
				row += '</tr>\n'
			else:
				error("Unrecognized type in writeTableRows: {0:s}".format(type))
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
			
		if line != "":
			row += descPrefix
			row += self.calcKeywordLinks(line, required=True)
			if comment != "":
				row += ' &nbsp;&nbsp;&nbsp;&mdash; '
		if comment != "":
			row += '<span class="comment">'
			row += self.calcKeywordLinks(comment)
			row += '</span>'
		row += '</td>'
		return row
	
	def calcDefinition(self, keyword):
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

	# This method is similar to extractReferences. When updating, consider if
	# changes are needed both places.
	def calcKeywordLinks(self, line, required=False):
		words = []
		firstWord = True
		for word in line.split():
			# Skip over special initial characters.
			if firstWord and word == '*':
				words.append('*')
				# Don't update firstWord since the next word might be capitalized.
				continue
				
			prefix = ""
			postfix = ""
			# Strip non-alphanumeric from beginning/end of token.
			# Also remove contraction endings like "'s".
			m = re.match("([^A-Za-z0-9_]*)(" + KEYWORD + ")([^A-Za-z0-9_]*.*)", word)
			if m:
				prefix = m.group(1)
				word = m.group(2)
				postfix = m.group(3)

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
					words.append('{0:s}<abbr title="Defined in {1:s}">{2:s}</abbr>{3:s}'
							.format(prefix, info[1], word, postfix))
					
				else:
					words.append('{0:s}<a class="keyword" href="#{1:s}">{2:s}</a>{3:s}'
							.format(prefix, canonicalForm, word, postfix))
			elif required and not firstWord and word[0].isupper():
				errorLine("...{0:s}".format(line),
						'Unable to find definition for "{0:s}"'.format(word))
			else:
				words.append('{0:s}{1:s}{2:s}'.format(prefix, word, postfix))
			
			firstWord = False
			
		return ' '.join(words)
		
	def calcComment(self, comment):
		return '<span class="comment">{0:s}</span>'.format(comment)

	def lookupCanonicalForm(self, word):
		prefix = ""
		postfix = ""
		# Strip non-alphanumeric from beginning/end of token.
		m = re.match("([^A-Za-z0-9_]*)(" + KEYWORD + ")([^A-Za-z0-9_]*)", word)
		if m:
			prefix = m.group(1)
			word = m.group(2)
			postfix = m.group(3)
		if word in self.vocabPlural:
			return self.vocabPlural[word]
		
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

	def writeHtml(self, filepath):
		outfile = os.path.splitext(os.path.basename(filepath))[0] + ".html"
		outpath = os.path.join(OUTPUT_DIR, outfile)
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
		out.write('	<title>{0:s}</title>\n'.format(title))
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

def processAll(dir):
	for item in os.listdir(dir):
		path = os.path.join(dir, item)
		if os.path.isfile(path):
			ext = os.path.splitext(path)[1]
			if ext == ".gm":
				processOne(path)

def processOne(path):
	print("Analyzing {0:s}...".format(path))

	parser = GambitParser()
	parser.process(path)

def usage():
	print("Usage: %s <options>" % sys.argv[0])
	print("where <options> are:")
	print("  --verbose")  # verbose debug output

def main():
	try:
		opts, args = getopt.getopt(sys.argv[1:],
			'v',
			['verbose'])
	except getopt.GetoptError:
		usage()
		exit()

	verbose = False
	
	for opt, arg in opts:
		if opt in ('-v', '--verbose'):
			verbose = True

	processAll("src")
	#processOne("src/welcome-to-the-dungeon.gm")

if __name__ == '__main__':
	main()
