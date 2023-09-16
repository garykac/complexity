#!/usr/bin/env python
# -*- coding: utf-8 -*-

TAB_SIZE = 4

# Special section names.
class SectionName:
	ASSUMPTIONS = "Assumptions"
	VOCABULARY = "Vocabulary"

# Special Gambit keywords.
class Keyword:
	NAME = "NAME"
	IMPORT = "IMPORT"
	GAME_IMPORT = "GAME-IMPORT"
	SECTION = "SECTION"
	SUBSECTION = "SUBSECTION"

# User visible language symbols.
class LinePrefix:
	CONSTRAINT = "!"
	LOOKUP_TABLE = "*"

# ==================
# Internal constants
# ==================

# Keyword regular expressions.
class RegEx:
	KEYWORD = "[A-Z][A-Za-z0-9_]*"
	MULTI_KEYWORDS = "[A-Z][A-Za-z0-9\|_]*"
	TEMPLATE_KEYWORD = "(" + KEYWORD + ")\<(" + KEYWORD + ")\>"

# Vocabulary types.
class VocabType:
	BASE = "BASE"
	LOCAL = "LOCAL"
	IMPORT = "IMPORT"
	GAME_IMPORT = "GAME-IMPORT"

# Parser line types.
class LineType:
	COMMENT = "COMMENT"
	BLANK = "BLANK"
	NAME = "NAME"
	IMPORT = "IMPORT"
	GAME_IMPORT = "GAME-IMPORT"
	SECTION = "SECTION"
	SUBSECTION = "SUBSECTION"
	DEF = "DEF"
	TEMPLATE = "TEMPLATE"
	CONSTRAINT = "CONSTRAINT"
	DESC = "DESC"
