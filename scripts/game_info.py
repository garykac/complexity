#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re

import xml.etree.ElementTree as ET
from xml.etree.ElementTree import Element
from xml.etree.ElementTree import ElementTree

SRC_DIR = "../src"

class Tag:
	GAME = "game"              # ATTR = "id"
	
	# Game
	NAME = "name"
	DESIGNERS = "designers"
	GENERAL = "general"
	NOTES = "notes"
	BGG = "bgg"                # ATTR = "id"
	COMPLEXITY = "complexity"
	
	# Name
	TITLE = "title"
	SUBTITLE = "subtitle"
	PARENT = "parent"
	
	# Designers
	DESIGNER = "designer"

	# General info
	PUBLISHED = "published"    # ATTR = "year"
	AGE = "age"                # ATTR = "min"
	PLAYERS = "players"        # ATTR = "min", "max"
	TIME = "time"              # ATTR = "min", "max"

	# Notes
	P = "p"
	
	# BGG
	WEIGHT = "weight"          # ATTR = "date", "avg"
	
	# Complexity
	RULEBOOK = "rulebook"
	VOCAB = "vocab"
	SCORE = "score"
	EXPORT = "export"

class Attr:
	# <game>,<bgg>
	ID = "id"

	# <general> : <published>
	YEAR = "year"
	
	# <general> : <age>,<players>,<time>
	MIN = "min"
	MAX = "max"
	
	# <bgg> : <weight>
	DATE = "date"
	AVG = "avg"
	
	# <complexity> : <score>
	NAME = "name"
	COST = "cost"
	
class GameInfo:
	"""Info for each game."""
	def __init__(self, id):
		self.id = id
		
		# Name
		self.title = None
		self.subtitle = None
		self.parent = None

		self.designers = []
		self.year = None
		self.age = None
		
		# Players
		self.players_min = 1
		self.players_max = 1
		
		# Game time
		self.time_min = 0
		self.time_max = 0
		
		self.notes = []
		
		# BoardGameGeek stats
		self.bgg_id = 0
		self.bgg_weight = 0
		self.bgg_weight_date = None
		
		# Complexity
		self.rulebook = None
		self.vocab = 0
		self.score = 0
		self.export_csv = False

		self.basepath = os.path.join(self.id[0], self.id)
		self.filepath = os.path.join(SRC_DIR, self.basepath)
		self.infopath = self.filepath + ".xml"

		self.load()
		self.hasChanges = False

	def updateVocab(self, vocab):
		if vocab != self.vocab:
			self.vocab = vocab
			self.hasChanges = True
		self.hasChanges = True
	
	def updateScore(self, score):
		if score != self.score:
			self.score = score
			self.hasChanges = True
		self.hasChanges = True
	
	def save(self):
		if not self.hasChanges:
			return
		
		with open(self.infopath, 'w') as fp:
			# Strip off in-progress marker, if present.
			id = self.id
			if id[-1] == '_':
				id = id[:-1]

			fp.write('<?xml version="1.0" encoding="UTF-8"?>\n')
			fp.write(f'<{Tag.GAME} id="{id}">\n')

			self.save_name(fp)
			self.save_designers(fp)
			self.save_general(fp)
			self.save_notes(fp)
			self.save_bgg(fp)
			self.save_complexity(fp)

			fp.write(f"</{Tag.GAME}>\n")

	def save_name(self, fp):
		fp.write(f"<{Tag.NAME}>\n")
		fp.write(f"\t<{Tag.TITLE}>{escapeXmlEntities(self.title)}</{Tag.TITLE}>\n")
		if self.subtitle:
			fp.write(f"\t<{Tag.SUBTITLE}>{escapeXmlEntities(self.subtitle)}</{Tag.SUBTITLE}>\n")
		if self.parent:
			fp.write(f"\t<{Tag.PARENT}>{self.parent}</{Tag.PARENT}>\n")
		fp.write(f"</{Tag.NAME}>\n")

	def save_designers(self, fp):
		if len(self.designers) != 0:
			fp.write(f"<{Tag.DESIGNERS}>\n")
			for d in self.designers:
				fp.write(f"\t<{Tag.DESIGNER}>{d}</{Tag.DESIGNER}>\n")
			fp.write(f"</{Tag.DESIGNERS}>\n")

	def save_general(self, fp):
		fp.write(f"<{Tag.GENERAL}>\n")

		if self.year:
			fp.write(f'\t<{Tag.PUBLISHED} {Attr.YEAR}="{self.year}" />\n')

		if self.age:
			fp.write(f'\t<{Tag.AGE} {Attr.MIN}="{self.age}" />\n')

		fp.write(f'\t<{Tag.PLAYERS}')
		fp.write(f' {Attr.MIN}="{self.players_min}"')
		fp.write(f' {Attr.MAX}="{self.players_max}"')
		fp.write(f' />\n')

		fp.write(f'\t<{Tag.TIME}')
		fp.write(f' {Attr.MIN}="{self.time_min}"')
		fp.write(f' {Attr.MAX}="{self.time_max}"')
		fp.write(f' />\n')

		fp.write(f"</{Tag.GENERAL}>\n")

	def save_notes(self, fp):
		if len(self.notes) != 0:
			fp.write(f"<{Tag.NOTES}>\n")
			for p in self.notes:
				fp.write(f"\t<{Tag.P}>{escapeXmlEntities(p)}</{Tag.P}>\n")
			fp.write(f"</{Tag.NOTES}>\n")

	def save_bgg(self, fp):
		if self.bgg_id and self.bgg_id != 0:
			fp.write(f'<{Tag.BGG} {Attr.ID}="{self.bgg_id}">\n')
		else:
			fp.write(f'<{Tag.BGG}>\n')

		fp.write(f'\t<{Tag.WEIGHT}')
		if self.bgg_weight_date:
			fp.write(f' {Attr.DATE}="{self.bgg_weight_date}"')
		fp.write(f' {Attr.AVG}="{self.bgg_weight}"')
		fp.write(f' />\n')

		fp.write(f'</{Tag.BGG}>\n')

	def save_complexity(self, fp):
		fp.write(f"<{Tag.COMPLEXITY}>\n")
		if self.rulebook:
			fp.write(f"\t<{Tag.RULEBOOK}>{self.rulebook}</{Tag.RULEBOOK}>\n")
		fp.write(f"\t<{Tag.VOCAB}>{self.vocab}</{Tag.VOCAB}>\n")

		fp.write(f'\t<{Tag.SCORE}')
		fp.write(f' {Attr.COST}="{self.score}"')
		fp.write(f' />\n')

		fp.write(f"\t<{Tag.EXPORT}>{self.export_csv}</{Tag.EXPORT}>\n")
		fp.write(f"</{Tag.COMPLEXITY}>\n")

	def load(self):
		tree = ElementTree()
		tree.parse(self.infopath)
		root = tree.getroot()
		
		#if not Attr.ID in root.attrib:
		#	raise Exception(f"Missing game id in {self.infopath}")
		#id = root.attrib[Attr.ID]
		#if self.id != id and self.id != f"{id}_":
		#	raise Exception(f"Game id doesn't match: {self.id} != {id} in {self.infopath}")
				
		for el in root:
			(ns, tag) = splitTag(el.tag)
			match tag:
				case Tag.NAME:
					self.load_name(el)
				case Tag.DESIGNERS:
					self.load_designers(el)
				case Tag.GENERAL:
					self.load_general(el)
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

	def load_general(self, elRoot):
		for el in elRoot:
			(ns, tag) = splitTag(el.tag)
			match tag:
				case Tag.PUBLISHED:
					self.load_published(el)
				case Tag.AGE:
					self.load_age(el)
				case Tag.PLAYERS:
					self.load_players(el)
				case Tag.TIME:
					self.load_time(el)
				case _:
					raise Exception(f"Unknown tag '{tag}' in {self.infopath} <{Tag.GENERAL}>")

	def load_published(self, elPublished):
		for attrName, attrValue in elPublished.attrib.items():
			match attrName:
				case Attr.YEAR:
					self.year = attrValue
				case _:
					raise Exception(f"Unknown attribute '{attrName}' in {self.infopath} <{Tag.PUBLISHED}>")

	def load_age(self, elAge):
		for attrName, attrValue in elAge.attrib.items():
			match attrName:
				case Attr.MIN:
					self.age = attrValue
				case _:
					raise Exception(f"Unknown attribute '{attrName}' in {self.infopath} <{Tag.AGE}>")

	def load_players(self, elPlayers):
		for attrName, attrValue in elPlayers.attrib.items():
			match attrName:
				case Attr.MIN:
					self.players_min = attrValue
				case Attr.MAX:
					self.players_max = attrValue
				case _:
					raise Exception(f"Unknown attribute '{attrName}' in {self.infopath} <{Tag.PLAYERS}>")

	def load_time(self, elTime):
		for attrName, attrValue in elTime.attrib.items():
			match attrName:
				case Attr.MIN:
					self.time_min = attrValue
				case Attr.MAX:
					self.time_max = attrValue
				case _:
					raise Exception(f"Unknown attribute '{attrName}' in {self.infopath} <{Tag.TIME}>")

	def load_notes(self, elRoot):
		for el in elRoot:
			(ns, tag) = splitTag(el.tag)
			match tag:
				case Tag.P:
					self.notes.append(el.text)
				case _:
					raise Exception(f"Unknown tag '{tag}' in {self.infopath} <{Tag.NOTES}>")

	def load_bgg(self, bggRoot):
		for attrName, attrValue in bggRoot.attrib.items():
			match attrName:
				case Attr.ID:
					self.bgg_id = attrValue
				case _:
					raise Exception(f"Unknown attribute '{attrName}' in {self.infopath} <{Tag.BGG}>")

		for el in bggRoot:
			(ns, tag) = splitTag(el.tag)
			match tag:
				case Tag.WEIGHT:
					if Attr.AVG in el.attrib:
						self.bgg_weight = el.attrib[Attr.AVG]
					if Attr.DATE in el.attrib:
						self.bgg_weight_date = el.attrib[Attr.DATE]
				case _:
					raise Exception(f"Unknown tag '{tag}' in {self.infopath} <{Tag.BGG}>")

	def load_complexity(self, elRoot):
		for el in elRoot:
			(ns, tag) = splitTag(el.tag)
			match tag:
				case Tag.RULEBOOK:
					self.rulebook = el.text
				case Tag.VOCAB:
					self.vocab = int(el.text)
				case Tag.SCORE:
					if Attr.COST in el.attrib:
						self.score = el.attrib[Attr.COST]
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
