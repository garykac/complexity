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

def warning(msg):
	print(f"WARNING: {msg}")

class Analyzer:
	"""Analyze Gambit (.gm) files."""
	def __init__(self):
		self.debug = False
		self.showCost = False
		self.useWarnings = True

		self.gameMgr = GameListManager()
	
	# ==========
	# Process .GM files
	# ==========
	
	def processAll(self, options):
		for (id, gameInfo) in self.gameMgr.nextGame():
			self.processOne(id, options)

	def processOne(self, id, options):
		print(f"Analyzing {id}...")
		if not os.path.isdir(OUTPUT_DIR):
			os.makedirs(OUTPUT_DIR)
		gameInfo = self.gameMgr.getGame(id)

		parser = GambitParser(options)
		parser.setWarnOnTodo()

		parser.loadImportableTerms(os.path.join(SRC_DIR, "_import.gm"))

		filename = f"{gameInfo.basepath}.gm"
		filepath = os.path.join(SRC_DIR, filename)
		parser.process(SRC_DIR, filepath)

		summary = parser.calc.getSummary()
		gameInfo.updateScore(summary)
		gameInfo.save()

		if self.showCost:
			self.printCost(parser.calc)
		
		parser.checkReferences()

		htmlExporter = GambitHtmlExporter(parser, gameInfo)
		outfile = f"{gameInfo.basepath}.html"
		outpath = os.path.join(OUTPUT_DIR, outfile)
		dir = os.path.dirname(outpath)
		if not os.path.isdir(dir):
			os.makedirs(dir)
		htmlExporter.writeHtml(outpath)
	
	def printCost(self, calc):
		scoreTotal, sections = calc.getSummary()
		hasSubsections = (len(calc.subsectionCosts) != 0)
		if hasSubsections:
			print("+------------------------------------------------+")
			for s in sections:
				name, cost, subs = s
				percent = 100 * (cost / scoreTotal)
				print(f"| {name:<20} {cost:>3}        {percent:>5.1f}%         |")
				for sub in subs:
					subname, subcost = sub
					percent = 100 * (subcost / scoreTotal)
					print(f"|    {subname:<20}   {subcost:>3}           {percent:>5.1f}% |")
			name = "Total"
			percent = 100
			print(f"| {name:<20} {scoreTotal:>3}        {percent:>5.1f}%         |")
			print("+------------------------------------------------+")
		else:
			print("+------------------------------------+")
			for s in sections:
				name, cost, subs = s
				percent = 100 * (cost / scoreTotal)
				print(f"| {name:<20} {cost:>3}    {percent:>5.1f}% |")
			name = "Total"
			percent = 100
			print(f"| {name:<20} {scoreTotal:>3}    {percent:>5.1f}% |")
			print("+------------------------------------+")

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
