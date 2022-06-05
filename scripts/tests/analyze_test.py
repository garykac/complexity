from unittest import mock

from .. analyze import GambitParser

def test_tokenizer_simple():
    parser = GambitParser()
    out = parser.tokenize("Sample string")
    assert len(out) == 2
    out = parser.tokenize("A sample string with more words")
    assert len(out) == 6

def test_tokenizer_string():
    parser = GambitParser()
    out = parser.tokenize('Sample line with "a" string')
    assert len(out) == 5
    assert out[3] == '"a"'

    out = parser.tokenize('Sample line with "a multi word" string')
    assert len(out) == 5
    assert out[3] == '"a multi word"'

    out = parser.tokenize('"A string" at the beginning')
    assert len(out) == 4
    assert out[0] == '"A string"'

    out = parser.tokenize('At the end, "a string"')
    assert len(out) == 4
    assert out[3] == '"a string"'

def test_processLine_empty():
    parser = GambitParser()
    checkLineType(parser, "", "BLANK", None, 0, "", "")
    checkLineType(parser, "  ", "BLANK", None, 0, "", "")
    checkLineType(parser, "\t", "BLANK", None, 1, "", "")
    checkLineType(parser, " \t ", "BLANK", None, 0, "", "")

def test_processLine_import():
    parser = GambitParser()
    checkLineType(parser, "#import file", "IMPORT", None, 0, "", "file")

def test_processLine_comment():
    parser = GambitParser()
    checkLineType(parser, "// comment", "COMMENT", None, 0, "", "comment")
    checkLineType(parser, "\t// comment", "COMMENT", None, 1, "", "comment")
    checkLineType(parser, "\t\t// comment", "COMMENT", None, 2, "", "comment")
    # Spaces don't count for indent.
    checkLineType(parser, "  // comment", "COMMENT", None, 0, "", "comment")
    checkLineType(parser, "    // comment", "COMMENT", None, 0, "", "comment")
    # Trailing spaces.
    checkLineType(parser, "\t// comment   ", "COMMENT", None, 1, "", "comment")

def test_processLine_commentSpecial():
    parser = GambitParser()
    checkLineType(parser, "// SECTION: title", "SECTION", None, 0, "", "title")
    checkLineType(parser, "// SUBSECTION: title", "SUBSECTION", None, 0, "", "title")
    assert parser.processLine("// NAME: title") == None
    assert parser.processLine("// BGG Weight: title") == None
    # Not detected if they are indented.
    checkLineType(parser, "\t// SECTION: title", "COMMENT", None, 1, "", "SECTION: title")

def test_processLine_templateDef():
    parser = GambitParser()

    out = checkLineType(parser, "NewVerb<Type>: Verb", "TEMPLATE", 1, 0, "", "")
    assert out['keyword'] == "NewVerb"
    assert out['param'] == "Type"

    out = checkLineType(parser, "NewVerb<Type>: Verb  // comment", "TEMPLATE", 1, 0, "", "comment")
    assert out['keyword'] == "NewVerb"
    assert out['param'] == "Type"
    # Not detected if indented.
    checkLineType(parser, "\tNewVerb<Type>: Verb", "DESC", 1, 1, "NewVerb<Type>: Verb", "")

def test_processLine_def():
    parser = GambitParser()
    
    out = checkLineType(parser, "NewVerb: Noun", "DEF", 1, 0, "", "")
    assert out['keyword'] == "NewVerb"
    assert out['types'] == ["Noun"]
    assert out['parent'] == None
    out = checkLineType(parser, "NewVerb: Noun  // comment", "DEF", 1, 0, "", "comment")
    assert out['keyword'] == "NewVerb"
    assert out['types'] == ["Noun"]
    assert out['parent'] == None

    out = checkLineType(parser, "NewVerb|Alt: Noun", "DEF", 1, 0, "", "")
    assert out['keyword'] == "NewVerb"
    assert out['types'] == ["Noun"]
    assert out['parent'] == None
    out = checkLineType(parser, "NewVerb|Alt: Noun  // comment", "DEF", 1, 0, "", "comment")
    assert out['keyword'] == "NewVerb"
    assert out['types'] == ["Noun"]
    assert out['parent'] == None

    parser.processLine("Noun1: Noun")
    parser.processLine("Noun2: Noun")
    out = checkLineType(parser, "Noun3: Noun1,Noun2", "DEF", 1, 0, "", "")
    assert out['keyword'] == "Noun3"
    assert out['types'] == ["Noun1", "Noun2"]
    assert out['parent'] == None

    out = checkLineType(parser, "Thing: Attribute of Noun1", "DEF", 1, 0, "", "")
    assert out['keyword'] == "Thing"
    assert out['types'] == ["Attribute"]
    assert out['parent'] == "Noun1"

def test_processLine_constraint():
    parser = GambitParser()
    checkLineType(parser, "! Some constraint", "CONSTRAINT", 1, 0, "Some constraint", "")
    checkLineType(parser, "\t! Some constraint", "CONSTRAINT", 1, 1, "Some constraint", "")
    checkLineType(parser, "\t\t! Some constraint", "CONSTRAINT", 1, 2, "Some constraint", "")

    checkLineType(parser, "! Some constraint  // comment", "CONSTRAINT", 1, 0, "Some constraint", "comment")

def test_processLine_description():
    parser = GambitParser()
    checkLineType(parser, "Some description", "DESC", 1, 0, "Some description", "")
    checkLineType(parser, "\tSome description", "DESC", 1, 1, "Some description", "")
    checkLineType(parser, "\t\tSome description", "DESC", 1, 2, "Some description", "")

    checkLineType(parser, "Some description  // comment", "DESC", 1, 0, "Some description", "comment")

# Process line and compare with expected values (prefix 'x').
def checkLineType(parser, line, xType, xCost, xIndent, xLine, xComment):
    out = parser.processLine(line)
    if out:
        assert out['type'] == xType
        assert out['cost'] == xCost
        assert out['indent'] == xIndent
        assert out['line'] == xLine
        assert out['comment'] == xComment
    return out
