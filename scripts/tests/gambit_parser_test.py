import pytest

from gambit_parser import GambitParser
from gambit_line_processor import GambitLineProcessor
from unittest import mock

#def mock_importFile(self, name):
#    assert name == "file"

#@mock.patch.object(GambitParser, 'importFile', new=mock_importFile)
#def test_processLine_import():
#    parser = GambitParser({})
#    checkLineType(parser, "#import file", "IMPORT", None, 0, "", "file")

#def test_processLine_commentSpecial():
#    parser = GambitParser({})
#    checkLineType(parser, "// NAME: title", "NAME", None, 0, "", "title")
#    assert parser.gameTitle == "title"

def test_processLine_templateDef():
    parser = GambitParser({})
    checkLineType(parser, "NewVerb<Type>: Verb", "TEMPLATE", 1, 0, "", "")
    checkVocab(parser, "NewVerb", ["LOCAL", "Verb", "Type"])

def test_processLine_def():
    parser = GambitParser({})
    checkLineType(parser, "NewTerm: Noun", "DEF", 1, 0, "", "")
    checkVocab(parser, "NewTerm", ["LOCAL", ["Noun"]])
    checkAlt(parser, "NewTerm", "NewTerms")

def test_processLine_defUnknownType():
    parser = GambitParser({})
    with pytest.raises(Exception):
        checkLineType(parser, "NewTerm: UnknownType", "DEF", 1, 0, "", "")

def test_processLine_defAlt():
    parser = GambitParser({})
    checkLineType(parser, "NewTerm|AltTerm: Noun", "DEF", 1, 0, "", "")
    checkVocab(parser, "NewTerm", ["LOCAL", ["Noun"]])
    checkAlt(parser, "NewTerm", "AltTerm")

def test_processLine_defMultiType():
    parser = GambitParser({})
    parser.processLine("Noun1: Noun")
    parser.processLine("Noun2: Noun")
    checkLineType(parser, "Noun3: Noun1,Noun2", "DEF", 1, 0, "", "")

def test_processLine_defParent():
    parser = GambitParser({})
    parser.processLine("Noun1: Noun")
    checkLineType(parser, "Thing: Attribute of Noun1", "DEF", 1, 0, "", "")
    checkVocab(parser, "Thing", ["LOCAL", ["Attribute"], "Noun1"])

def test_processLine_defParentUnknown():
    parser = GambitParser({})
    with pytest.raises(Exception):
        checkLineType(parser, "Thing: Attribute of Noun1", "DEF", 1, 0, "", "")

def test_processLine_constraint():
    parser = GambitParser({})
    checkLineType(parser, "! Some constraint", "CONSTRAINT", 1, 0, "Some constraint", "")

def test_processLine_description():
    parser = GambitParser({})
    checkLineType(parser, "\tSome description", "DESC", 1, 1, "Some description", "")

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

def checkVocab(parser, term, info):
    assert parser.vocab.vocab[term] == info

def checkAlt(parser, term, plural):
    assert parser.vocab.vocabPlural[plural] == term
