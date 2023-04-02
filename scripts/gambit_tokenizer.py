#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re

from gambit import KEYWORD, MULTI_KEYWORDS, TEMPLATE_KEYWORD

class GambitTokenizer:
	"""Simple tokenizer."""
	def __init__(self):
		pass

	# ==========
	# Parsing and Tokenizing
	# ==========
	
	@staticmethod
	def tokenize(str):
		out = []
		substrings = str.split('"')
		for i in range(0, len(substrings)):
			if i % 2:
				out.append('"{0:s}"'.format(substrings[i]))
			else:
				out.extend(substrings[i].split())
		return out

	@staticmethod
	def untokenize(tokens):
		return ' '.join(tokens)

	@staticmethod
	def isTemplate(term):
		m = re.match(TEMPLATE_KEYWORD, term)
		if m:
			keyword = m.group(1)
			param = m.group(2)
			return (keyword, param)
		return None

	# Strip non-alphanumeric from beginning/end of token.
	# Also remove contraction endings like "'s".
	@staticmethod
	def extractKeyword(word):
		m = re.match("([^A-Za-z0-9_]*)(" + KEYWORD + ")([^A-Za-z0-9_]*.*)", word)
		if m:
			return (m.group(1), m.group(2), m.group(3))
		return ("", word, "")

