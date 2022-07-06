#!/usr/bin/env python
# -*- coding: utf-8 -*-

import getopt
import os
import sys

from gambit_html_exporter import GambitHtmlExporter
from gambit_parser import GambitParser

SRC_DIR = "../src"
OUTPUT_DIR = "../games"
LIST_FILE = "_list.txt"

def warning(msg):
	print("WARNING: {0:s}".format(msg))

class Analyzer:
	"""Analyze Gambit (.gm) files."""
	def __init__(self):
		self.debug = False
		self.showCost = False
		self.useWarnings = True

		self.games = None
	
	# ==========
	# Game list
	# ==========
	
	def loadGameList(self):
		if self.games:
			return

		if not os.path.isdir(OUTPUT_DIR):
			os.makedirs(OUTPUT_DIR)
		listfile = os.path.join(SRC_DIR, LIST_FILE)

		self.games = {}
		with open(listfile, 'r') as file:
			for line in file:
				(id, title, subtitle, parentId, score) = line.strip().split(';')
				self.games[id] = [title, subtitle, parentId, score]

	def updateIndexList(self, id, newScore):
		if not id in self.games:
			warning("Unable to update score for {0:s}".format(id))
			return
		(title, subtitle, parentId, score) = self.games[id]
		if score != newScore:
			# Update the score in the games dict.
			self.games[id][3] = newScore

			# Update _list.txt
			listfile = os.path.join(SRC_DIR, LIST_FILE)
			with open(listfile, 'w') as out:
				for key, value in self.games.items():
					(title, subtitle, parentId, score) = value					
					out.write(';'.join([key, title, subtitle, str(parentId), str(score)]))
					out.write('\n')
			
	# ==========
	# Process .GM files
	# ==========
	
	def processAll(self):
		self.loadGameList()
		for id in self.games:
			self.processOne(id)

	def processOne(self, id):
		print("Analyzing {0:s}...".format(id))
		self.loadGameList()
		if not id in self.games:
			warning('Unable to find "{0:s}" in game list'.format(id))

		parser = GambitParser()
		parser.setWarnOnTodo()

		filename = "{0:s}.gm".format(id)
		filepath = os.path.join(SRC_DIR, filename)
		parser.process(SRC_DIR, filepath)

		cost = parser.costTotal
		self.updateIndexList(id, cost)
		if self.showCost:
			print("   = {0:d}".format(cost))
			for s in parser.sectionCosts:
				print(s)

		parser.checkReferences()

		htmlExporter = GambitHtmlExporter(parser)
		outfile = "{0:s}.html".format(id)
		outpath = os.path.join(OUTPUT_DIR, outfile)
		htmlExporter.writeHtml(outpath)

def usage():
	print("Usage: %s <options>" % sys.argv[0])
	print("where <options> are:")
	print("  --game <id>")  # process a single game
	print("  --verbose")  # verbose debug output

def main():
	try:
		opts, args = getopt.getopt(sys.argv[1:],
			'g:v',
			['game=', 'verbose'])
	except getopt.GetoptError:
		usage()
		exit()

	gameId = None
	verbose = False
	
	for opt, arg in opts:
		if opt in ('-g', '--game'):
			gameId = arg
		if opt in ('-v', '--verbose'):
			verbose = True

	analyzer = Analyzer()
	if gameId:
		analyzer.showCost = True
		analyzer.processOne(gameId)
	else:
		analyzer.processAll()

if __name__ == '__main__':
	main()
