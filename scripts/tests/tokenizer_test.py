import pytest

from tokenizer import Tokenizer

def test_tokenizer_simple():
    out = Tokenizer.tokenize("Sample string")
    assert len(out) == 2
    out = Tokenizer.tokenize("A sample string with more words")
    assert len(out) == 6

def test_tokenizer_string():
    out = Tokenizer.tokenize('Sample line with "a" string')
    assert len(out) == 5
    assert out[3] == '"a"'

    out = Tokenizer.tokenize('Sample line with "a multi word" string')
    assert len(out) == 5
    assert out[3] == '"a multi word"'

    out = Tokenizer.tokenize('"A string" at the beginning')
    assert len(out) == 4
    assert out[0] == '"A string"'

    out = Tokenizer.tokenize('At the end, "a string"')
    assert len(out) == 4
    assert out[3] == '"a string"'

