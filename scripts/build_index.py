#!/usr/bin/env python
# -*- coding: utf-8 -*-

import getopt
import os
import re
import sys

SRC_DIR = "../src"
LIST_FILE = "_list.txt"
OUTPUT_FILE = "../index.html"

def error(msg):
	print("ERROR: {0:s}".format(msg))
	exit()

class IndexBuilder:
	"""Parser for Gambit (.gm) files."""
	def __init__(self):
		self.vocab = {}
		self.games = {}
		self.children = {}
		self.buckets = [30, 75, 120]
		
	def writeTableFooter(self, out):
		out.write('</table>\n')

	def loadGames(self):
		listfile = os.path.join(SRC_DIR, LIST_FILE)
		self.games = {}
		with open(listfile, 'r') as file:
			for line in file:
				(id, title, subtitle, parentId, score) = line.strip().split(';')
				self.games[id] = [title, subtitle, parentId, int(score)]
				if parentId:
					self.children[parentId] = [ id ]

	def writeBucket(self, out, bucketMin, bucketMax):
		print("bucket", bucketMin, bucketMax)
		if bucketMax:
			out.write('<div class="section">{0:d}-{1:d}</div>\n'.format(bucketMin, bucketMax))
		else:
			out.write('<div class="section">{0:d}+</div>\n'.format(bucketMin))
		self.writeListHeader(out)
		
		# Find games in range.
		games = {}
		for id, value in self.games.items():
			(title, subtitle, parent, score) = value
			if parent:
				continue
			if score >= bucketMin and (not bucketMax or score <= bucketMax):
				if not score in games:
					games[score] = []
				games[score].append(id)
				print("adding", id, "to bucket")
		
		# Write out games
		for score in sorted(games.keys()):
			for id in sorted(games[score]):
				(title, subtitle, parent, s) = self.games[id]
				self.writeListEntry(out, id, title, subtitle, score)
				if id in self.children:
					for idChild in self.children[id]:
						(title, subtitle, parent, scoreChild) = self.games[idChild]
						self.writeListEntry(out, idChild, title, subtitle, scoreChild, parentScore=score)

		self.writeListFooter(out)

	def writeHtml(self):
		bucketStart = 1
		with open(OUTPUT_FILE, 'w') as out:
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
		out.write('	<title>Boardgame Learning Complexity</title>')
		out.write('	<link rel="preconnect" href="https://fonts.googleapis.com">\n')
		out.write('	<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n')
		out.write('	<link href="https://fonts.googleapis.com/css2?family=Noto+Sans:ital,wght@0,400;0,600;0,700;1,400;1,600;1,700&display=swap" rel="stylesheet">\n')
		out.write('	<link rel="stylesheet" href="index.css">\n')
		out.write('</head>\n')
		out.write('<body>\n')
		out.write('<div class="container">\n')
		out.write('<div class="pagetitle">Boardgame Learning Complexity</div>\n')

	def writeListHeader(self, out):
		out.write('<div class="list">\n')

	def writeListEntry(self, out, id, title, subtitle, score, parentScore=None):
		out.write('<div class="entry">')
		out.write('<a href="games/{0:s}.html">'.format(id))
		out.write('<span class="title">{0:s}</span>'.format(title))
		if subtitle:
			out.write('<br/>')
			out.write('<span class="subtitle">{0:s}</span>'.format(subtitle))
		out.write('<br/>')
		if parentScore:
			out.write('<span class="score">({0:d})+{1:d}</span>'.format(parentScore, score))
		else:
			out.write('<span class="score">{0:d}</span>'.format(score))
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
