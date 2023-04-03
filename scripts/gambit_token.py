#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Token types.
T_WORD = "WORD"
T_STRING = "STRING"
T_REF = "REF"
T_TEMPLATE_REF = "TREF"

class GambitToken:
	"""Basic token and metadata."""
	def __init__(self, type: str, value: str):
		self.type = type
		self.value = value

