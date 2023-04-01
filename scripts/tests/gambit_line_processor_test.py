import pytest

from gambit_line_processor import GambitLineProcessor

def test_processLine_empty():
    checkLineType("", "BLANK", None, 0, "", "")
    with pytest.raises(Exception):
        checkLineType("  ", "BLANK", None, 0, "", "")
    checkLineType("\t", "BLANK", None, 0, "", "")
    with pytest.raises(Exception):
        checkLineType(" \t ", "BLANK", None, 0, "", "")

#def test_processLine_import():
#    checkLineType("#import file", "IMPORT", None, 0, "", "file")

def test_processLine_comment():
    checkLineType("// comment", "COMMENT", None, 0, "", "comment")
    checkLineType("\t// comment", "COMMENT", None, 1, "", "comment")
    checkLineType("\t\t// comment", "COMMENT", None, 2, "", "comment")
    # Check for indenting using spaces.
    checkLineType("    // comment", "COMMENT", None, 1, "", "comment")
    checkLineType("        // comment", "COMMENT", None, 2, "", "comment")
    # Invalid number of spaces.
    with pytest.raises(Exception):
        checkLineType("  // comment", "COMMENT", None, 0, "", "comment")
    # Trailing spaces.
    checkLineType("\t// comment   ", "COMMENT", None, 1, "", "comment")

def test_processLine_commentSpecial():
    checkLineType("SECTION: title", "SECTION", None, 0, "", "title")
    checkLineType("SUBSECTION: title", "SUBSECTION", None, 0, "", "title")
    checkLineType("NAME: title", "NAME", None, 0, "", "title")
    # Not detected if they are indented.
    #checkLineType("\tSECTION: title", "COMMENT", None, 1, "", "SECTION: title")

def test_processLine_templateDef():
    out = checkLineType("NewVerb<Type>: Verb", "TEMPLATE", 1, 0, "", "")
    assert out['keyword'] == "NewVerb"
    assert out['param'] == "Type"

    out = checkLineType("NewVerb<Type>: Verb  // comment", "TEMPLATE", 1, 0, "", "comment")
    assert out['keyword'] == "NewVerb"
    assert out['param'] == "Type"
    # Not detected if indented.
    checkLineType("\tNewVerb<Type>: Verb", "DESC", 1, 1, "NewVerb<Type>: Verb", "")

def test_processLine_def():
    out = checkLineType("NewVerb: Noun", "DEF", 1, 0, "", "")
    assert out['keyword'] == "NewVerb"
    assert out['types'] == ["Noun"]
    assert out['parent'] == None
    out = checkLineType("NewVerb: Noun  // comment", "DEF", 1, 0, "", "comment")
    assert out['keyword'] == "NewVerb"
    assert out['types'] == ["Noun"]
    assert out['parent'] == None

    out = checkLineType("NewVerb|Alt: Noun", "DEF", 1, 0, "", "")
    assert out['keyword'] == "NewVerb"
    assert out['alt-keyword'] == "Alt"
    assert out['types'] == ["Noun"]
    assert out['parent'] == None
    out = checkLineType("NewVerb|Alt: Noun  // comment", "DEF", 1, 0, "", "comment")
    assert out['keyword'] == "NewVerb"
    assert out['alt-keyword'] == "Alt"
    assert out['types'] == ["Noun"]
    assert out['parent'] == None

    out = checkLineType("Noun3: Noun1,Noun2", "DEF", 1, 0, "", "")
    assert out['keyword'] == "Noun3"
    assert out['types'] == ["Noun1", "Noun2"]
    assert out['parent'] == None

    out = checkLineType("Thing: Attribute of Noun1", "DEF", 1, 0, "", "")
    assert out['keyword'] == "Thing"
    assert out['types'] == ["Attribute"]
    assert out['parent'] == "Noun1"

def test_processLine_constraint():
    checkLineType("! Some constraint", "CONSTRAINT", 1, 0, "Some constraint", "")
    checkLineType("\t! Some constraint", "CONSTRAINT", 1, 1, "Some constraint", "")
    checkLineType("\t\t! Some constraint", "CONSTRAINT", 1, 2, "Some constraint", "")

    checkLineType("! Some constraint  // comment", "CONSTRAINT", 1, 0, "Some constraint", "comment")

def test_processLine_description():
    #checkLineType("Some description", "DESC", 1, 0, "Some description", "")
    checkLineType("\tSome description", "DESC", 1, 1, "Some description", "")
    checkLineType("\t\tSome description", "DESC", 1, 2, "Some description", "")

    checkLineType("\tSome description  // comment", "DESC", 1, 1, "Some description", "comment")

# Process line and compare with expected values (prefix 'x').
def checkLineType(line, xType, xCost, xIndent, xLine, xComment):
    out = GambitLineProcessor.processLine(line)
    if out:
        assert out['type'] == xType
        assert out['cost'] == xCost
        assert out['indent'] == xIndent
        assert out['line'] == xLine
        assert out['comment'] == xComment
    return out

def test_extractKeyword():
    checkExtractedKeywords("word", "", "word", "")
    checkExtractedKeywords("word.", "", "word.", "")
    checkExtractedKeywords("Word.", "", "Word", ".")
    
def checkExtractedKeywords(word, xPre, xWord, xPost):
    out = GambitLineProcessor.extractKeyword(word)
    assert out[0] == xPre
    assert out[1] == xWord
    assert out[2] == xPost
