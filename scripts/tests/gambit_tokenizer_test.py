import pytest

from gambit_tokenizer import GambitTokenizer

def checkString(out, expected):
    assert len(out) == len(expected)
    for i in range(len(out)):
    	assert out[i] == expected[i]

def test_tokenizer_simple():
    out = GambitTokenizer.split("Sample string")
    checkString(out, ["Sample", "string"])

    out = GambitTokenizer.split("A sample string with more words")
    checkString(out, ["A", "sample", "string", "with", "more", "words"])

def test_tokenizer_string():
    out = GambitTokenizer.split('Sample line with "a" string')
    checkString(out, ["Sample", "line", "with", '"a"', "string"])

    out = GambitTokenizer.split('Sample line with "a multi word" string')
    checkString(out, ["Sample", "line", "with", '"a multi word"', "string"])

    out = GambitTokenizer.split('"A string" at the beginning')
    checkString(out, ['"A string"', "at", "the", "beginning"])

    out = GambitTokenizer.split('At the end, "a string"')
    checkString(out, ["At", "the", "end,", '"a string"'])

def checkExtractedKeywords(word, xPre, xWord, xPost):
    out = GambitTokenizer.extractKeyword(word)
    assert out[0] == xPre
    assert out[1] == xWord
    assert out[2] == xPost

def test_extractKeyword():
    checkExtractedKeywords("word", "", "word", "")
    checkExtractedKeywords("word.", "", "word.", "")
    checkExtractedKeywords("Word.", "", "Word", ".")
