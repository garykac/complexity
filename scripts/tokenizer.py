#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import traceback

class Tokenizer:
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
