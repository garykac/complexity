#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Token types.
class TokenType:
	WORD = "WORD"
	STRING = "STRING"
	REF = "REF"
	TEMPLATE_REF = "TREF"

class GambitToken:
	"""Basic token and metadata."""
	def __init__(self, type: str, value: str):
		self.type = type
		self.value = value

