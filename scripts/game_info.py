#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re

import xml.etree.ElementTree as ET
from xml.etree.ElementTree import Element
from xml.etree.ElementTree import ElementTree

SRC_DIR = "../src"

class Tag:
	GAME = "game"
	
	# Game
	ID = "id"
	NAME = "name"
	DESIGNERS = "designers"
	YEAR = "year"
	PLAYERS = "players"
	TIME = "time"
	NOTES = "notes"
	BGG = "bgg"
	COMPLEXITY = "complexity"
	
	# Name
	TITLE = "title"
	SUBTITLE = "subtitle"
	PARENT = "parent"
	
	# Designers
	DESIGNER = "designer"
	
	# Players and Time
	MIN = "min"
	MAX = "max"
	
	# Notes
	P = "p"
	
	# BGG
	WEIGHT = "weight"
	#ID
	
	# Complexity
	VOCAB = "vocab"
	SCORE = "score"
	EXPORT = "export"

class GameInfo:
	"""Info for each game."""
	def __init__(self, id):
		self.id = id
		
		# Name
		self.title = None
		self.subtitle = None
		self.parent = None

		self.designers = []
		self.year = 0
		
		# Players
		self.players_min = 1
		self.players_max = 1
		
		# Game time
		self.time_min = 0
		self.time_max = 0
		
		self.notes = []

		self.export_csv = False
		
		# BoardGameGeek stats
		self.bgg_id = 0
		self.bgg_weight = 0
		
		# Complexity
		self.vocab = 0
		self.score = 0

		self.basepath = os.path.join(self.id[0], self.id)
		self.filepath = os.path.join(SRC_DIR, self.basepath)
		self.infopath = self.filepath + ".xml"

		self.load()
		self.hasChanges = False

	def setVocab(self, vocab):
		self.vocab = vocab
		self.hasChanges = True
	
	def setScore(self, score):
		self.score = score
		self.hasChanges = True
	
	def save(self):
		if not self.hasChanges:
			return
		
		with open(self.infopath, 'w') as fp:
			fp.write('<?xml version="1.0" encoding="UTF-8"?>\n')
			fp.write(f"<{Tag.GAME}>\n")
			fp.write(f"<{Tag.ID}>{self.id}</{Tag.ID}>\n")

			fp.write(f"<{Tag.NAME}>\n")
			fp.write(f"\t<{Tag.TITLE}>{escapeXmlEntities(self.title)}</{Tag.TITLE}>\n")
			if self.subtitle:
				fp.write(f"\t<{Tag.SUBTITLE}>{escapeXmlEntities(self.subtitle)}</{Tag.SUBTITLE}>\n")
			if self.parent:
				fp.write(f"\t<{Tag.PARENT}>{self.parent}</{Tag.PARENT}>\n")
			fp.write(f"</{Tag.NAME}>\n")

			if len(self.designers) != 0:
				fp.write(f"<{Tag.DESIGNERS}>\n")
				for d in self.designers:
					fp.write(f"\t<{Tag.DESIGNER}>{d}</{Tag.DESIGNER}>\n")
				fp.write(f"</{Tag.DESIGNERS}>\n")

			if self.year != 0:
				fp.write(f"<{Tag.YEAR}>{self.year}</{Tag.YEAR}>\n")

			fp.write(f"<{Tag.PLAYERS}>\n")
			fp.write(f"\t<{Tag.MIN}>{self.players_min}</{Tag.MIN}>\n")
			fp.write(f"\t<{Tag.MAX}>{self.players_max}</{Tag.MAX}>\n")
			fp.write(f"</{Tag.PLAYERS}>\n")

			fp.write(f"<{Tag.TIME}>\n")
			fp.write(f"\t<{Tag.MIN}>{self.time_min}</{Tag.MIN}>\n")
			fp.write(f"\t<{Tag.MAX}>{self.time_max}</{Tag.MAX}>\n")
			fp.write(f"</{Tag.TIME}>\n")

			if len(self.notes) != 0:
				fp.write(f"<{Tag.NOTES}>\n")
				for p in self.notes:
					fp.write(f"\t<{Tag.P}>{escapeXmlEntities(p)}</{Tag.P}>\n")
				fp.write(f"</{Tag.NOTES}>\n")

			fp.write(f"<{Tag.BGG}>\n")
			fp.write(f"\t<{Tag.ID}>{self.bgg_id}</{Tag.ID}>\n")
			fp.write(f"\t<{Tag.WEIGHT}>{self.bgg_weight}</{Tag.WEIGHT}>\n")
			fp.write(f"</{Tag.BGG}>\n")

			fp.write(f"<{Tag.COMPLEXITY}>\n")
			fp.write(f"\t<{Tag.VOCAB}>{self.vocab}</{Tag.VOCAB}>\n")
			fp.write(f"\t<{Tag.SCORE}>{self.score}</{Tag.SCORE}>\n")
			export = self.export_csv
			if export == "y":
				export = "true"
			elif export == "n":
				export = "false"
			fp.write(f"\t<{Tag.EXPORT}>{export}</{Tag.EXPORT}>\n")
			fp.write(f"</{Tag.COMPLEXITY}>\n")

			fp.write(f"</{Tag.GAME}>\n")

	def load(self):
		tree = ElementTree()
		tree.parse(self.infopath)
		root = tree.getroot()
		for el in root:
			(ns, tag) = splitTag(el.tag)
			match tag:
				case Tag.ID:
					if self.id != el.text:
						raise Exception(f"Game id doesn't match: {self.id} != {el.text} in {self.infopath}")
				case Tag.YEAR:
					self.year = el.text
				case Tag.NAME:
					self.load_name(el)
				case Tag.DESIGNERS:
					self.load_designers(el)
				case Tag.PLAYERS:
					self.load_players(el)
				case Tag.TIME:
					self.load_time(el)
				case Tag.NOTES:
					self.load_notes(el)
				case Tag.BGG:
					self.load_bgg(el)
				case Tag.COMPLEXITY:
					self.load_complexity(el)
				case _:
					raise Exception(f"Unknown tag '{tag}' in {self.infopath}")

	def load_name(self, elRoot):
		for el in elRoot:
			(ns, tag) = splitTag(el.tag)
			match tag:
				case Tag.TITLE:
					self.title = el.text
				case Tag.SUBTITLE:
					self.subtitle = el.text
				case Tag.PARENT:
					self.parent = el.text
				case _:
					raise Exception(f"Unknown tag '{tag}' in {self.infopath} <{Tag.NAME}>")

	def load_designers(self, elRoot):
		for el in elRoot:
			(ns, tag) = splitTag(el.tag)
			match tag:
				case Tag.DESIGNER:
					self.designers.append(el.text)
				case _:
					raise Exception(f"Unknown tag '{tag}' in {self.infopath} <{Tag.DESIGNERS}>")

	def load_players(self, elRoot):
		for el in elRoot:
			(ns, tag) = splitTag(el.tag)
			match tag:
				case Tag.MIN:
					self.players_min = el.text
				case Tag.MAX:
					self.players_max = el.text
				case _:
					raise Exception(f"Unknown tag '{tag}' in {self.infopath} <{Tag.PLAYERS}>")

	def load_time(self, elRoot):
		for el in elRoot:
			(ns, tag) = splitTag(el.tag)
			match tag:
				case Tag.MIN:
					self.time_min = el.text
				case Tag.MAX:
					self.time_max = el.text
				case _:
					raise Exception(f"Unknown tag '{tag}' in {self.infopath} <{Tag.TIME}>")

	def load_notes(self, elRoot):
		for el in elRoot:
			(ns, tag) = splitTag(el.tag)
			match tag:
				case Tag.P:
					self.notes.append(el.text)
				case _:
					raise Exception(f"Unknown tag '{tag}' in {self.infopath} <{Tag.NOTES}>")

	def load_bgg(self, elRoot):
		for el in elRoot:
			(ns, tag) = splitTag(el.tag)
			match tag:
				case Tag.ID:
					self.bgg_id = el.text
				case Tag.WEIGHT:
					self.bgg_weight = el.text
				case _:
					raise Exception(f"Unknown tag '{tag}' in {self.infopath} <{Tag.BGG}>")

	def load_complexity(self, elRoot):
		for el in elRoot:
			(ns, tag) = splitTag(el.tag)
			match tag:
				case Tag.VOCAB:
					self.vocab = int(el.text)
				case Tag.SCORE:
					self.score = int(el.text)
				case Tag.EXPORT:
					self.export_csv = el.text
				case _:
					raise Exception(f"Unknown tag '{tag}' in {self.infopath} <{Tag.COMPLEXITY}>")

def escapeXmlEntities(s):
	s = s.replace("&", "&amp;")
	return s
	
def splitTag(tag):
	namespace = ''
	m = re.match(r'\{(?P<namespace>.*)\}(?P<tag>.*)', tag)
	if m:
		namespace = m.group("namespace")
		tag = m.group("tag")
	return [namespace, tag]
