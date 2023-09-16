#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import traceback

from gambit import LineType, VocabType
from gambit_line_info import GambitLineInfo
from gambit_line_processor import GambitLineProcessor
from gambit_token import TokenType

GM_CSS_PATH = "gm.css"

class GambitHtmlExporter:
	"""HTML exporter for Gambit (.gm) files."""
	def __init__(self, parser, gameInfo):
		self.parser = parser
		self.gameInfo = gameInfo
		self.gameTitle = parser.gameTitle
		self.maxIndent = parser.maxIndent

		self.calc = parser.calc
		self.costTotal = parser.calc.costTotal

	def writeHtml(self, outpath):
		with open(outpath, 'w') as out:
			self.writeHtmlHeader(out, self.gameTitle, self.costTotal)
			self.writeHtmlCostSummary(out, self.calc)
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
		out.write(f'	<title>{htmlify(title)}</title>\n')
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
		out.write(f'<div class="title">{htmlify(self.gameInfo.title)}</div>\n')
		subtitle = self.gameInfo.subtitle
		if subtitle:
			out.write(f'<div class="subtitle">{htmlify(self.gameInfo.subtitle)}</div>\n')
		designers = ', '.join(self.gameInfo.designers)
		out.write(f'<div class="designer">{designers}</div>\n')
		year = self.gameInfo.year
		if not year:
			year = ""
		out.write(f'<div class="year">{year}</div>\n\n')

	def writeHtmlCostSummary(self, out, calc):
		(costTotal, sections) = calc.getSummary()

		hasSubsections = (len(calc.subsectionCosts) != 0)

		out.write('<table class="summary">\n')

		# For games with no subsections:
		# +-------------------------------+
		# |      Rule complexity          |
		# +-----------------+------+------+
		# | section         | cost |   %  |
		# +-----------------+------+------+
		# | section         | cost |   %  |
		# +-----------------+------+------+
		# | Total           | cost | 100% |
		# +-----------------+------+------+
		if not hasSubsections:
			out.write('<colgroup>')
			out.write('<col class="summary-section-name">')
			out.write('<col class="summary-data">')
			out.write('<col class="summary-data">')
			out.write('</colgroup>\n')

			out.write('<tr><td colspan="3"><b>Rule Complexity</b></td></tr>\n')
			for s in sections:
				(name, cost, subs) = s
				out.write('<tr>')
				out.write('<td class="summary-section-name">')
				out.write(name)
				out.write('</td><td class="summary-data">')
				self.writeHtmlCost(out, cost)
				out.write('</td><td class="summary-data">')
				self.writeHtmlCostPercentage(out, cost, self.costTotal)
				out.write('</td></tr>\n')
		
			out.write('<tr><td class="summary-section-name"><b>Total</b></td>')
			out.write('<td class="summary-data"><b>{0:d}</b></td>'.format(self.costTotal))
			out.write('<td class="summary-data"><b>100%</b></td></tr>\n')

		# For games with subsections:
		# +--------------------------------------------+
		# |            Rule complexity                 |
		# +-----------------+------+------+------+-----+
		# | section         | cost |      |   %  |     |
		# +-----------------+------+------+------+-----+
		# | section w/ subs | cost |      |   %  |     | <- cost/% for entire section
		# +----+------------+------+------+------+-----+
		# |    | subsection |      | cost |      |  %  |
		# +----+------------+------+------+------+-----+
		# |    | subsection |      | cost |      |  %  |
		# +----+------------+------+------+------+-----+
		# | section         | cost |      |   %  |     |
		# +-----------------+------+------+------+-----+
		# | Total           | cost |      | 100% |     |
		# +-----------------+------+------+------+-----+
		else:
			out.write('<colgroup>')
			out.write('<col class="summary-subsection-indent">')
			out.write('<col class="summary-subsection-name">')
			out.write('<col class="summary-subdata">')
			out.write('<col class="summary-subdata">')
			out.write('<col class="summary-subdata">')
			out.write('<col class="summary-subdata">')
			out.write('</colgroup>\n')

			out.write('<tr><td colspan="6"><b>Rule Complexity</b></td></tr>\n')
			for s in sections:
				(name, cost, subs) = s
				self.writeHtmlCostSection(out, name, cost)
				for sub in subs:
					(subname, subcost) = sub
					self.writeHtmlCostSubsection(out, subname, subcost)

			out.write('<tr><td colspan=2 class="summary-section-name"><b>Total</b></td>')
			out.write('<td class="summary-subdata"><b>{0:d}</b></td>'.format(self.costTotal))
			out.write('<td class="summary-subdata"></td>')
			out.write('<td class="summary-subdata"><b>100%</b></td>')
			out.write('<td class="summary-subdata"></td>')
			out.write('</tr>\n')

		out.write('</table>\n\n')

	def writeHtmlCostSection(self, out, name, cost):
		out.write('<tr>')
		out.write('<td colspan=2 class="summary-section-name">')
		out.write(name)
		out.write('</td>')
		out.write('<td class="summary-subdata">')
		self.writeHtmlCost(out, cost)
		out.write('</td>')
		out.write('<td class="summary-subdata"></td>')
		out.write('<td class="summary-subdata">')
		self.writeHtmlCostPercentage(out, cost, self.costTotal)
		out.write('</td>')
		out.write('<td class="summary-subdata"></td>')
		out.write('</tr>\n')

	def writeHtmlCostSubsection(self, out, name, cost):
		out.write('<tr>')
		out.write('<td class="summary-subsection-indent">')
		out.write('<td class="summary-subsection-name">')
		out.write(name)
		out.write('</td>')
		out.write('<td class="summary-subdata"></td>')
		out.write('<td class="summary-subdata">')
		out.write(str(cost))
		out.write('</td>')
		out.write('<td class="summary-subdata"></td>')
		out.write('<td class="summary-subdata">')
		self.writeHtmlCostPercentage(out, cost, self.costTotal)
		out.write('</td>')
		out.write('</tr>\n')

	def writeHtmlCost(self, out, cost):
		if cost:
			out.write(str(cost))
		else:
			out.write("-")		

	def writeHtmlCostPercentage(self, out, cost, total):
		if cost:
			out.write("{0:.1f}%".format(100 * cost / total))
		else:
			out.write("-")		

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
		
		if len(self.gameInfo.notes) != 0:
			thead += self.calcNotes()
		
		out.write(thead)

	def calcNotes(self):
		notes = ''
		lineInfo = GambitLineInfo(-1, LineType.COMMENT)
		for n in self.gameInfo.notes:
			notes += '<tr>'
			notes += self.calcTableRowCostColumn(None)
			notes += self.calcTableRowDescColumn(lineInfo, n, "")
			notes += '</tr>\n'
		return notes
	
	def writeTableFooter(self, out):
		out.write('</table>\n')

	def writeTableRows(self, out):
		for r in self.parser.lineInfo:
			type = r.lineType
			prefix = ""
			line = r.line
			comment = r.lineComment
			rowclass = None

			if type == LineType.DEF:
				defn = self.calcDefinitionHtml(r.keyword)
				prefix = "{0:s}: ".format(defn)
				if r.parent != None:
					line = '{0:s} of {1:s}'.format(r.types[0], r.parent)
				else:
					line = ', '.join(r.types)
			elif type == LineType.TEMPLATE:
				defn = self.calcTemplateHtml(r.keyword, r.param)
				prefix = "{0:s}: ".format(defn)
				line = "Verb"
			elif type == LineType.CONSTRAINT:
				# &roplus;&bull;&ddagger;&rArr;&oplus;&oast;&star;&starf;&diams;&xoplus;&Otimes;
				prefix = "&#9888; " # "!" in triangle
			elif type == LineType.BLANK:
				prefix = "&nbsp;"
			elif type == LineType.GAME_IMPORT:
				#comment = "#import {0:s}".format(comment)
				continue
			elif type == LineType.IMPORT:
				comment = ', '.join(r.data)
			elif type == LineType.SECTION:
				rowclass = "section"
			elif type == LineType.SUBSECTION:
				rowclass = "subsection"
			elif type == LineType.NAME:
				continue
			elif not type in [LineType.COMMENT, LineType.CONSTRAINT, LineType.DESC]:
				raise Exception("Unrecognized type in writeTableRows: {0:s}".format(type))

			if rowclass:
				row = '<tr class="{0:s}">'.format(rowclass)
			else:
				row = '<tr>'

			row += self.calcTableRowCostColumn(r.cost)

			if rowclass:
				row += '<td colspan={0:d}>{1:s}</td>'.format(self.maxIndent+1, r.name)
			else:
				row += self.calcTableRowDescColumn(r, comment, prefix)

			row += '</tr>\n'

			out.write(row)

	def calcTableRowCostColumn(self, cost):
		if cost != None:
			return '<td class="cost">{0:d}</td>'.format(cost)
		return '<td class="cost"></td>'
	
	def calcTableRowDescColumn(self, lineInfo, comment, descPrefix):
		indent = lineInfo.indent
		line = lineInfo.line
		
		row = '<td></td>' * indent

		colspan = self.maxIndent + 1 - indent
		if colspan == 1:
			row += '<td class="desc">'
		else:
			row += '<td class="desc" colspan={0:d}>'.format(colspan)
			
		if line != "" or descPrefix != "":
			row += descPrefix
			row += self.calcKeywordLinks(lineInfo)
			if comment != "":
				row += ' &nbsp;&nbsp;&nbsp;&mdash; '
		if comment != "":
			row += '<span class="comment">{0:s}</span>'.format(htmlify(comment))
		row += '</td>'
		return row
	
	def calcTemplateHtml(self, keyword, param):
		refs = self.parser.vocab.getReferencesTo(keyword)
		defn = '<div class="def-container">'
		defn += f'<a class="def" id="{keyword}">{keyword}&lt;{param}&gt;</a>'

		defn += '<div class="def-menu">'
		if len(refs) != 0:
			defn += '<div class="def-menu-title">Referenced&nbsp;by:</div>'
			for ref in refs:
				defn += f'<a href="#{ref}">{ref}</a>'
		else:
			defn += '<div class="def-menu-title">No&nbsp;references</div>'
		defn += '</div>'
		defn += '</div>'
		return defn

	def calcDefinitionHtml(self, keyword):
		refs = self.parser.vocab.getReferencesTo(keyword)
		defn = '<div class="def-container">'
		defn += f'<a class="def" id="{keyword}">{keyword}</a>'

		defn += '<div class="def-menu">'
		if len(refs) != 0:
			defn += '<div class="def-menu-title">Referenced&nbsp;by:</div>'
			for ref in refs:
				defn += f'<a href="#{ref}">{ref}</a>'
		else:
			defn += '<div class="def-menu-title">No&nbsp;references</div>'
		defn += '</div>'
		defn += '</div>'
		return defn

	def calcKeywordLinks(self, lineInfo):
		line = lineInfo.line
		tokens = lineInfo.tokens
		
		newWords = []
		for t in tokens:
			if isinstance(t, list):
				ttype = t[0]

				if ttype in [TokenType.WORD, TokenType.STRING]:
					newWords.append(t.value)
				elif ttype == TokenType.TEMPLATE_REF:
					(ttype, keyword, param) = t
					newWords.append('<a class="keyword" href="#{0:s}">{0:s}</a>&lt;<a class="keyword" href="#{1:s}">{1:s}</a>&gt;'
							.format(keyword, param))

				elif ttype == TokenType.REF:
					(ttype, canonicalForm, prefix, word, postfix) = t
					info = self.parser.vocab.lookup(canonicalForm)
					scope = info[0]
					if scope == VocabType.BASE:
						newWords.append('{0:s}{1:s}{2:s}'.format(prefix, word, postfix))
					elif scope == VocabType.GAME_IMPORT:
						newWords.append('{0:s}<abbr title="Imported from {1:s}">{2:s}</abbr>{3:s}'
								.format(prefix, info[1], word, postfix))
					elif scope == VocabType.IMPORT:
						newWords.append(f'{prefix}<abbr title="Imported term">{word}</abbr>{postfix}')
					else:
						newWords.append('{0:s}<a class="keyword" href="#{1:s}">{2:s}</a>{3:s}'
								.format(prefix, canonicalForm, word, postfix))
				else:
					raise Exception('Unknown token type: {0:s}'.format(ttype))
			else:
				newWords.append(t)

		return ' '.join(newWords)

def htmlify(str):
	str = str.replace("&", "&amp;")
	return str
