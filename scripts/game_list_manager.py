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
		self.loadList()
	
	def getGame(self, id):
		if not id in self.games or not self.games[id]:
			self.games[id] = GameInfo(id)
		return self.games[id]

	def nextGame(self):
		for id in self.gameOrder:
			yield (id, self.getGame(id))

	def loadList(self):
		with open(self.listfile, 'r') as fp:
			for line in fp:
				# Ignore comment lines.
				if line[0] == '#':
					continue
				id = line.strip()
				# Ignore "in progress" games.
				if id[-1] == '_':
					continue
				self.gameOrder.append(id)
				self.games[id] = None
