import pytest

from gambit_tokenizer import GambitTokenizer

def test_tokenizer_simple():
    out = GambitTokenizer.split("Sample string")
    assert len(out) == 2
    out = GambitTokenizer.split("A sample string with more words")
    assert len(out) == 6

def test_tokenizer_string():
    out = GambitTokenizer.split('Sample line with "a" string')
    assert len(out) == 5
    assert out[3] == '"a"'

    out = GambitTokenizer.split('Sample line with "a multi word" string')
    assert len(out) == 5
    assert out[3] == '"a multi word"'

    out = GambitTokenizer.split('"A string" at the beginning')
    assert len(out) == 4
    assert out[0] == '"A string"'

    out = GambitTokenizer.split('At the end, "a string"')
    assert len(out) == 4
    assert out[3] == '"a string"'

def test_extractKeyword():
    checkExtractedKeywords("word", "", "word", "")
    checkExtractedKeywords("word.", "", "word.", "")
    checkExtractedKeywords("Word.", "", "Word", ".")
    
def checkExtractedKeywords(word, xPre, xWord, xPost):
    out = GambitTokenizer.extractKeyword(word)
    assert out[0] == xPre
    assert out[1] == xWord
    assert out[2] == xPost
