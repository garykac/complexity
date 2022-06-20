#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import traceback

from gambit_line_processor import GambitLineProcessor
from tokenizer import Tokenizer

GM_CSS_PATH = "gm.css"

class GambitHtmlExporter:
	"""HTML exporter for Gambit (.gm) files."""
	def __init__(self, parser):
		self.parser = parser
		self.gameTitle = parser.gameTitle
		self.costTotal = parser.costTotal
		self.maxIndent = parser.maxIndent

	def htmlify(self, str):
		str = str.replace("&", "&amp;")
		return str
	
	def writeHtml(self, outpath):
		with open(outpath, 'w') as out:
			self.writeHtmlHeader(out, self.gameTitle, self.costTotal)
			self.writeHtmlCostSummary(out, self.parser.sectionCosts, self.costTotal)
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
		out.write('<div class="title">{0:s}</div>\n\n'.format(title))

	def writeHtmlCostSummary(self, out, sectionCosts, costTotal):
		out.write('<table class="summary">\n')
		out.write('<colgroup><col class="summary-first-column"><col class="summary-column"><col class="summary-column"></colgroup>\n')
		out.write('<tr><td colspan="3"><b>Rule Complexity</b></td></tr>\n')
		for s in sectionCosts:
			(name, cost) = s
			out.write('<tr><td class="summary-first-column">')
			out.write(name)
			out.write('</td><td class="summary-column">')
			out.write(str(cost))
			out.write('</td><td class="summary-column">')
			out.write("{0:.1f}%".format(100 * cost / costTotal))
			out.write('</td></tr>\n')
		out.write('<tr><td class="summary-first-column"><b>Total</b></td>')
		out.write('<td class="summary-column"><b>{0:d}</b></td>'.format(costTotal))
		out.write('<td class="summary-column"></td></tr>\n')
		out.write('</table>\n\n')

	def writeHtmlFooter(self, out):
		out.write('<div class="footer">&nbsp;</div>\n')
		out.write('</div>\n')
		out.write('</body>\n')
		out.write('</html>\n')

	def writeTableHeader(self, out):
		out.write('<table class="main">\n')

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

	def writeTableRows(self, out):
		for r in self.parser.lines:
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
				raise Exception("Unrecognized type in writeTableRows: {0:s}".format(type))

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
		if keyword in self.parser.referencedBy:
			refs = sorted(self.parser.referencedBy[keyword])
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
		if keyword in self.parser.referencedBy:
			refs = sorted(self.parser.referencedBy[keyword])
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
	# TODO: Precalculate these links and store them in the |self.parser.lines|.
	#
	# |line| - string to process
	# |required| - True if it should verify that the keyword is defined
	def calcKeywordLinks(self, line, required=False):
		words = []
		firstWord = True
		for word in Tokenizer.tokenize(line):
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
			if word in self.parser.vocabPlural:
				canonicalForm = self.parser.vocabPlural[word]

			if canonicalForm in self.parser.vocab:
				info = self.parser.vocab[canonicalForm]
				scope = info[0]
				if scope == "BASE":
					words.append('{0:s}{1:s}{2:s}'.format(prefix, word, postfix))
				elif scope == "IMPORT":
					words.append('{0:s}<abbr title="Imported from {1:s}">{2:s}</abbr>{3:s}'
							.format(prefix, info[1], word, postfix))
					
				else:
					words.append('{0:s}<a class="keyword" href="#{1:s}">{2:s}</a>{3:s}'
							.format(prefix, canonicalForm, word, postfix))
			elif required:
				if firstWord and re.match(r'[A-Z].*[A-Z].*', word):
					raise Exception('Unable to find definition for "{0:s}"'.format(word))
				elif not firstWord and word[0].isupper():
					raise Exception('Unable to find definition for "{0:s}"'.format(word))
				else:
					words.append('{0:s}{1:s}{2:s}'.format(prefix, self.htmlify(word), postfix))
			else:
				words.append('{0:s}{1:s}{2:s}'.format(prefix, self.htmlify(word), postfix))
			
			firstWord = False
			if (word != "" and word[-1] == '.') or (postfix != "" and postfix[-1] == '.'):
				firstWord = True
			
		return Tokenizer.untokenize(words)
