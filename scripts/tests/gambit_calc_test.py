import pytest

from fake_gambit_parser import FakeGambitParser
from gambit_calc import GambitCalc
from unittest import mock

def test_defHasDesc_noDescEof():
    parser = FakeGambitParser()
    parser.addDefLine("Term1", "Noun")

    calc = GambitCalc(parser, None)
    assert calc.defHasDesc(parser.lineInfo, 0) == False

def test_defHasDesc_noDescDef():
    parser = FakeGambitParser()
    parser.addDefLine("Term1", "Noun")
    parser.addDefLine("Term2", "Noun")

    calc = GambitCalc(parser, None)
    assert calc.defHasDesc(parser.lineInfo, 0) == False

def test_defHasDesc_noDescTemplate():
    parser = FakeGambitParser()
    parser.addDefLine("Term1", "Noun")
    parser.addTemplateLine("Template", "Param", "Comment")

    calc = GambitCalc(parser, None)
    assert calc.defHasDesc(parser.lineInfo, 0) == False

def test_defHasDesc_noDescBlank():
    parser = FakeGambitParser()
    parser.addDefLine("Term1", "Noun")
    parser.addBlankLine()

    calc = GambitCalc(parser, None)
    assert calc.defHasDesc(parser.lineInfo, 0) == False

def test_defHasDesc_hasDescBadIndent():
    parser = FakeGambitParser()
    parser.addDefLine("Term1", "Noun")
    parser.addDescLine(1, "Description", "Comment")

    calc = GambitCalc(parser, None)
    assert calc.defHasDesc(parser.lineInfo, 0) == True

def test_defHasDesc_invalidDef():
    parser = FakeGambitParser()
    parser.addDescLine(1, "Description", "Comment")

    calc = GambitCalc(parser, None)
    with pytest.raises(Exception):
        calc.defHasDesc(parser.lineInfo, 0)

def addTemplateLine(parser, lineNum, keyword, param, comment):
    parser.lines.append({
        'type': "TEMPLATE",
        'cost': 1,
        'indent': 0,
        'line': "",
        'comment': comment,
        'keyword': keyword,
        'param': param,
    })
