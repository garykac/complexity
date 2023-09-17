#!/usr/bin/env python
# -*- coding: utf-8 -*-

import getopt
import os
import re
import sys

from game_list_manager import GameListManager

SRC_DIR = "../src"
HTML_OUTPUT_FILE = "../index.html"
CSV_OUTPUT_FILE = "../data.csv"

def error(msg):
	print(f"ERROR: {msg}")
	exit()

class IndexBuilder:
	"""Parser for Gambit (.gm) files."""
	def __init__(self):
		self.games = {}
		self.children = {}
		self.buckets = [29, 59, 99, 199, 299]
		self.gameMgr = GameListManager()
		
	def loadGames(self):
		self.games = {}
		self.gameData = {}
		for (gameId, d) in self.gameMgr.nextGame():
			self.games[gameId] = d
			parentId = d.parent
			if parentId:
				self.children[parentId] = [ gameId ]

	def writeCsvData(self):
		with open(CSV_OUTPUT_FILE, 'w') as fp:
			for id, d in self.games.items():
				if d.export_csv == "true":
					title = d.title
					if d.subtitle:
						title += " " + d.subtitle
					bgg = str(d.bgg_weight)
					if bgg == "-":
						bgg = ""
					out = [title, bgg, str(d.getVocab()), str(d.getScore())]
					fp.write(','.join(out))
					fp.write('\n')


	def writeBucket(self, out, bucketMin, bucketMax):
		print("bucket", bucketMin, bucketMax)
		if bucketMax:
			out.write(f'<div class="section">{bucketMin}-{bucketMax}</div>\n')
		else:
			out.write(f'<div class="section">{bucketMin}+</div>\n')
		self.writeListHeader(out)
		
		# Find games in range.
		gameGroups = {}
		for id, info in self.games.items():
			parent = info.parent
			score = info.getScore()
			if parent:
				continue
			if score >= bucketMin and (not bucketMax or score <= bucketMax):
				if not score in gameGroups:
					gameGroups[score] = []
				gameGroups[score].append(id)
				print("adding", id, "to bucket")
		
		# Write out games
		for scoreGroup in sorted(gameGroups.keys()):
			for id in sorted(gameGroups[scoreGroup]):
				info = self.games[id]
				title = info.title
				subtitle = info.subtitle
				parent = info.parent
				score = info.getScore()
				self.writeListEntry(out, id, title, subtitle, score)
				if id in self.children:
					for idChild in self.children[id]:
						infoChild = self.games[idChild]
						title = infoChild.title
						subtitle = infoChild.subtitle
						parent = infoChild.parent
						scoreChild = infoChild.getScore()
						self.writeListEntry(out, idChild, title, subtitle, scoreChild, parentScore=score)

		self.writeListFooter(out)

	def writeHtml(self):
		bucketStart = 1
		with open(HTML_OUTPUT_FILE, 'w') as out:
			self.writeHtmlHeader(out)
			for bMax in self.buckets:
				self.writeBucket(out, bucketStart, bMax)
				bucketStart = bMax + 1
			self.writeBucket(out, bucketStart, None)
			self.writeHtmlFooter(out)

	def writeHtmlHeader(self, out):
		out.write('<!DOCTYPE html>\n')
		out.write('<html lang="en">\n')
		out.write('<head>\n')
		out.write('	<meta charset="utf-8" />\n')
		out.write('	<meta http-equiv="X-UA-Compatible" content="IE=edge" />\n')
		out.write('	<meta name="viewport" content="width=device-width, initial-scale=1" />\n')
		out.write('	<title>Boardgame Rule Complexity</title>\n')
		out.write('	<link rel="preconnect" href="https://fonts.googleapis.com">\n')
		out.write('	<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n')
		out.write('	<link href="https://fonts.googleapis.com/css2?family=Noto+Sans:ital,wght@0,400;0,600;0,700;1,400;1,600;1,700&display=swap" rel="stylesheet">\n')
		out.write('	<link rel="stylesheet" href="index.css">\n')
		out.write('</head>\n')
		out.write('<body>\n')
		out.write('<div class="container">\n')
		out.write('<div class="pagetitle">Boardgame Rule Complexity</div>\n')

	def writeListHeader(self, out):
		out.write('<div class="list">\n')

	def writeListEntry(self, out, id, title, subtitle, score, parentScore=None):
		out.write('<div class="entry">')
		out.write(f'<a href="games/{id[0]}/{id}.html">')
		out.write(f'<span class="title">{htmlify(title)}</span>')
		if subtitle:
			out.write('<br/>')
			out.write(f'<span class="subtitle">{htmlify(subtitle)}</span>')
		out.write('<br/>')
		if parentScore:
			out.write(f'<span class="score">({parentScore:d})+{score:d}</span>')
		else:
			out.write(f'<span class="score">{score:d}</span>')
		out.write('</a></div>\n')
	
	def writeListFooter(self, out):
		out.write('</div>\n')

	def writeHtmlFooter(self, out):
		out.write('<div class="footer">&nbsp;</div>\n')
		out.write('</div>\n')
		out.write('</body>\n')
		out.write('</html>\n')

	def build(self):
		self.loadGames()
		self.writeHtml()
		self.writeCsvData()

def htmlify(str):
	str = str.replace("&", "&amp;")
	return str
	
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

	builder = IndexBuilder()
	builder.build()

if __name__ == '__main__':
	main()
