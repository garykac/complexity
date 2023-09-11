#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

from game_info import GameInfo

SRC_DIR = "../src"
LIST_FILE = "_list.txt"


class GameListManager:
	"""Manager for the list of games."""
	def __init__(self):
		self.games = {}
		self.gameOrder = []

		self.listfile = os.path.join(SRC_DIR, LIST_FILE)
		self.load()
		
	def nextGame(self):
		for id in self.gameOrder:
			yield (id, self.games[id])

	def getVocab(self, id):
		return self.games[id].vocab

	def updateVocab(self, id, vocab):
		self.games[id].setVocab(vocab)
	
	def getScore(self, id):
		return self.games[id].score

	def updateScore(self, id, score):
		self.games[id].setScore(score)
	
	def load(self):
		with open(self.listfile, 'r') as fp:
			for line in fp:
				# Ignore comment lines.
				if line[0] == '#':
					continue
				id = line.strip()
				self.gameOrder.append(id)
				self.games[id] = GameInfo(id)

	def save(self):
		for gameId in self.gameOrder:
			self.games[gameId].save()
