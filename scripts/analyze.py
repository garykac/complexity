#!/usr/bin/env python
# -*- coding: utf-8 -*-

import getopt
import os
import sys

from gambit_html_exporter import GambitHtmlExporter
from game_list_manager import GameListManager
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
		self.gameMgr = GameListManager()
	
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
		for (gameId, d) in self.gameMgr.nextGame():
			self.games[gameId] = d

	def updateGameList(self, id, newScore, newVocab):
		if not id in self.games:
			warning("Unable to update score for {0:s}".format(id))
			return
		oldScore = self.gameMgr.getScore(id)
		oldVocab = self.gameMgr.getVocab(id)
		if oldScore != newScore or oldVocab != newVocab:
			self.gameMgr.updateVocab(id, newVocab)
			self.gameMgr.updateScore(id, newScore)
			self.gameMgr.save()
			
	# ==========
	# Process .GM files
	# ==========
	
	def processAll(self, options):
		self.loadGameList()
		for id in self.games:
			self.processOne(id, options)

	def processOne(self, id, options):
		print("Analyzing {0:s}...".format(id))
		self.loadGameList()
		if not id in self.games:
			warning('Unable to find "{0:s}" in game list'.format(id))

		parser = GambitParser(options)
		parser.setWarnOnTodo()

		parser.loadImportableTerms(os.path.join(SRC_DIR, "_import.gm"))

		filename = "{0:s}.gm".format(id)
		filepath = os.path.join(SRC_DIR, filename)
		parser.process(SRC_DIR, filepath)

		cost = parser.calc.costTotal
		vocab = parser.getVocabCost()
		self.updateGameList(id, cost, vocab)
		if self.showCost:
			print("   = {0:d}".format(cost))
			for s in parser.calc.sectionCosts:
				print(s)
			for s in parser.calc.subsectionCosts:
				print(s, parser.calc.subsectionCosts[s])

		parser.checkReferences()

		htmlExporter = GambitHtmlExporter(parser, self.games[id])
		outfile = "{0:s}.html".format(id)
		outpath = os.path.join(OUTPUT_DIR, outfile)
		htmlExporter.writeHtml(outpath)

def usage():
	print("Usage: %s [<options>] [<game>]" % sys.argv[0])
	print("where <options> are:")
	print("  --verbose [-v]")  # verbose debug output
	print("  --warnings [-w]")  # verbose debug output
	print("if <game> is not specified, then all games will be processed")

def main():
	try:
		opts, args = getopt.getopt(sys.argv[1:],
			'vw',
			['verbose', 'warnings'])
	except getopt.GetoptError:
		usage()
		exit()

	options = {
		'verbose': False,
		'warnings': False,
	}

	for opt, arg in opts:
		if opt in ('-v', '--verbose'):
			options['verbose'] = True
		if opt in ('-w', '--warnings'):
			options['warnings'] = True
		

	analyzer = Analyzer()
	if args:
		analyzer.showCost = True
		for gameId in args:
			analyzer.processOne(gameId, options)
	else:
		analyzer.processAll(options)

if __name__ == '__main__':
	main()
