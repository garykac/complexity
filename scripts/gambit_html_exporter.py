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
			self.writeHtmlCostSummary(out, self.parser)
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

	def writeHtmlCostSummary(self, out, parser):
		sectionCosts = parser.sectionCosts
		subsectionCosts = parser.subsectionCosts

		out.write('<table class="summary">\n')

		out.write('<colgroup>')
		out.write('<col class="summary-section-indent">')
		out.write('<col class="summary-subsection-column">')
		out.write('<col class="summary-column">')
		out.write('<col class="summary-column">')
		out.write('</colgroup>\n')

		out.write('<tr><td colspan="4"><b>Rule Complexity</b></td></tr>\n')
		for s in sectionCosts:
			(name, cost) = s
			if name in subsectionCosts:
				self.writeHtmlCostSection(out, name, None)
				self.writeHtmlCostSubsection(out, "-", cost)
				for sub in subsectionCosts[name]:
					(subname, subcost) = sub
					self.writeHtmlCostSubsection(out, subname, subcost)
			else:
				self.writeHtmlCostSection(out, name, cost)

		out.write('<tr><td colspan=2 class="summary-first-column"><b>Total</b></td>')
		out.write('<td class="summary-column"><b>{0:d}</b></td>'.format(self.parser.costTotal))
		out.write('<td class="summary-column"></td></tr>\n')

		out.write('</table>\n\n')

	def writeHtmlCostSection(self, out, name, cost):
		out.write('<tr>')
		out.write('<td colspan=2 class="summary-section-column">')
		out.write(name)
		out.write('</td><td class="summary-column">')
		if cost:
			out.write(str(cost))
		else:
			out.write("-")		
		out.write('</td><td class="summary-column">')
		if cost:
			out.write("{0:.1f}%".format(100 * cost / self.parser.costTotal))
		else:
			out.write("-")		
		out.write('</td></tr>\n')

	def writeHtmlCostSubsection(self, out, name, cost):
		out.write('<tr>')
		out.write('<td class="summary-section-indent">')
		out.write('<td class="summary-subsection-column">')
		out.write(name)
		out.write('</td><td class="summary-column">')
		out.write(str(cost))
		out.write('</td><td class="summary-column">')
		out.write("{0:.1f}%".format(100 * cost / self.parser.costTotal))
		out.write('</td></tr>\n')

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
			tokens = None
			if 'tokens' in r:
				tokens = r['tokens']
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
				# &roplus;&bull;&ddagger;&rArr;&oplus;&oast;&star;&starf;&diams;&xoplus;&Otimes;
				prefix = "&#9888; " # "!" in triangle
			elif type == "BLANK":
				prefix = "&nbsp;"
			elif type == "OLDIMPORT":
				#comment = "#import {0:s}".format(comment)
				continue
			elif type == "IMPORT":
				comment = ', '.join(comment)
			elif type == "SECTION":
				rowclass = "section"
			elif type == "SUBSECTION":
				rowclass = "subsection"
			elif type == "NAME":
				continue
			elif not type in ["COMMENT", "CONSTRAINT", "DESC"]:
				raise Exception("Unrecognized type in writeTableRows: {0:s}".format(type))

			if rowclass:
				row = '<tr class="{0:s}">'.format(rowclass)
			else:
				row = '<tr>'

			row += self.calcTableRowCostColumn(r['cost'])

			if rowclass:
				row += '<td colspan={0:d}>{1:s}</td>'.format(self.maxIndent+1, comment)
			else:
				row += self.calcTableRowDescColumn(r['indent'], line, tokens, comment, prefix)

			row += '</tr>\n'

			out.write(row)

	def calcTableRowCostColumn(self, cost):
		if cost != None:
			return '<td class="cost">{0:d}</td>'.format(cost)
		return '<td class="cost"></td>'
	
	def calcTableRowDescColumn(self, indent, line, tokens, comment, descPrefix = ""):
		row = '<td></td>' * indent

		colspan = self.maxIndent + 1 - indent
		if colspan == 1:
			row += '<td class="desc">'
		else:
			row += '<td class="desc" colspan={0:d}>'.format(colspan)
			
		if line != "" or descPrefix != "":
			row += descPrefix
			row += self.calcKeywordLinks(line, tokens)
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

	def calcKeywordLinks(self, line, tokens):
		if not tokens:
			return Tokenizer.untokenize(line.split())
		
		newWords = []
		for t in tokens:
			if isinstance(t, list):
				ttype = t[0]
				if ttype == "TREF":
					(ttype, keyword, param) = t
					newWords.append('<a class="keyword" href="#{0:s}">{0:s}</a>&lt;<a class="keyword" href="#{1:s}">{1:s}</a>&gt;'
							.format(keyword, param))
				elif ttype == "REF":
					(ttype, canonicalForm, prefix, word, postfix) = t
					info = self.parser.vocab[canonicalForm]
					scope = info[0]
					if scope == "BASE":
						newWords.append('{0:s}{1:s}{2:s}'.format(prefix, word, postfix))
					elif scope == "OLDIMPORT":
						newWords.append('{0:s}<abbr title="Imported from {1:s}">{2:s}</abbr>{3:s}'
								.format(prefix, info[1], word, postfix))
					elif scope == "IMPORT":
						newWords.append(f'{prefix}<abbr title="Imported term">{word}</abbr>{postfix}')
								
					else:
						newWords.append('{0:s}<a class="keyword" href="#{1:s}">{2:s}</a>{3:s}'
								.format(prefix, canonicalForm, word, postfix))
				else:
					raise Exception('Unknown token type: {0:s}'.format(ttype))
			else:
				newWords.append(t)

		return Tokenizer.untokenize(newWords)
