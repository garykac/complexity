#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

SRC_DIR = "../src"
LIST_FILE = "_list.txt"


def isComment(line):
	return line[0] == '#'


class GameListManager:
	"""Manager for the list of games."""
	def __init__(self):
		self.games = {}
		self.gameOrder = []

		self.listfile = os.path.join(SRC_DIR, LIST_FILE)
		self.load()

	def nextGame(self):
		for id in self.gameOrder:
			if isComment(id):
				continue
			yield (id, self.games[id])

	def getVocab(self, id):
		return self.games[id]['vocab']

	def updateVocab(self, id, vocab):
		self.games[id]['vocab'] = vocab
	
	def getScore(self, id):
		return self.games[id]['score']

	def updateScore(self, id, score):
		self.games[id]['score'] = score
	
	def load(self):
		with open(self.listfile, 'r') as fp:
			for line in fp:
				if isComment(line):
					self.gameOrder.append(line)
					continue
				(id, title, subtitle, parentId, exportCsv, bggWeight, vocab, score) = line.strip().split(';')
				info = {
					'title': title,
					'subtitle': subtitle,
					'parent-id': parentId,
					'export-csv': exportCsv,
					'bgg-weight': bggWeight,  # Leave as string. May be '-'.
					'vocab': int(vocab),
					'score': int(score),
				}
				self.gameOrder.append(id)
				self.games[id] = info

	def save(self):
		with open(self.listfile, 'w') as fp:
			for gameId in self.gameOrder:
				if isComment(gameId):
					fp.write(gameId)
					continue
				d = self.games[gameId]
				out = [gameId, d['title'], d['subtitle'], d['parent-id'], d['export-csv'], d['bgg-weight'], str(d['vocab']), str(d['score'])]
				fp.write(';'.join(out))
				fp.write('\n')
