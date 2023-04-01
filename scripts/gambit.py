#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Special Gambit keywords.
NAME_KEYWORD = "NAME"
IMPORT_KEYWORD = "IMPORT"
GAME_IMPORT_KEYWORD = "GAME-IMPORT"
SECTION_KEYWORD = "SECTION"
SUBSECTION_KEYWORD = "SUBSECTION"

# User visible language symbols.
CONSTRAINT_PREFIX = "!"
LOOKUP_TABLE_PREFIX = "*"

# ==================
# Internal constants
# ==================

# Keyword regular expressions.
KEYWORD = "[A-Z][A-Za-z0-9_]*"
MULTI_KEYWORDS = "[A-Z][A-Za-z0-9\|_]*"
TEMPLATE_KEYWORD = "(" + KEYWORD + ")\<(" + KEYWORD + ")\>"

# Vocabulary types.
V_BASE = "BASE"
V_LOCAL = "LOCAL"
V_IMPORT = "IMPORT"
V_GAME_IMPORT = "GAME-IMPORT"

# Parser line types.
LT_COMMENT = "COMMENT"
LT_BLANK = "BLANK"
LT_NAME = "NAME"
LT_IMPORT = "IMPORT"
LT_GAME_IMPORT = "GAME-IMPORT"
LT_SECTION = "SECTION"
LT_SUBSECTION = "SUBSECTION"
LT_DEF = "DEF"
LT_TEMPLATE = "TEMPLATE"
LT_CONSTRAINT = "CONSTRAINT"
LT_DESC = "DESC"
