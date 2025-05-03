#!/usr/bin/env python3
import string
import sys
from typing import List, Iterator

class Token:
    tok: str

    def __init__(self, tok: str):
        self.tok = tok

class StringToken(Token):
    pass

class DecimalToken(Token):
    pass

class ZeroDecimalToken(Token):
    pass

class UpperHexaDecimalToken(Token):
    pass

class LowerHexaDecimalToken(Token):
    pass

class ZeroUpperHexaDecimalToken(Token):
    pass

class ZeroLowerHexaDecimalToken(Token):
    pass

class PunctutationToken(Token):
    pass

def classify_token(tok: str) -> Token:
    if tok.isnumeric():
        if tok.startswith("0"):
            return ZeroDecimalToken(tok)
        return DecimalToken(tok)
    if set(tok).issubset(set(string.hexdigits)):
        if tok.isupper():
            if tok.startswith("0"):
                return ZeroUpperHexaDecimalToken(tok)
            return UpperHexaDecimalToken(tok)
        elif tok.islower():
            if tok.startswith("0"):
                return ZeroLowerHexaDecimalToken(tok)
            return LowerHexaDecimalToken(tok)
    return StringToken(tok)

def tokenize_name(name: str) -> Iterator[Token]:
    start = 0
    index = 0
    end = len(name)
    while index < end:
        if name[index] in string.punctuation:
            if index > start:
                yield classify_token(name[start:index])
            yield PunctutationToken(name[index])
            start = index + 1
        index += 1
    if index > start:
        yield classify_token(name[start:index])


def homogenize_token_stream(token_stream: List[Token]):
    token_set = set(type(x) for x in token_stream)
    if len(token_set) == 1:
        return token_stream
    max_class = StringToken
    if token_set.issubset({
        LowerHexaDecimalToken,
        ZeroLowerHexaDecimalToken,
        DecimalToken,
        ZeroDecimalToken,
     }):
        max_class = ZeroLowerHexaDecimalToken
    if token_set.issubset({
        UpperHexaDecimalToken,
        ZeroUpperHexaDecimalToken,
        DecimalToken,
        ZeroDecimalToken,
     }):
        max_class = ZeroUpperHexaDecimalToken
    if token_set == {LowerHexaDecimalToken, DecimalToken}:
        max_class = LowerHexaDecimalToken
    if token_set == {UpperHexaDecimalToken, DecimalToken}:
        max_class = UpperHexaDecimalToken
    if token_set == {ZeroDecimalToken, DecimalToken}:
        max_class = ZeroDecimalToken
    return [max_class(token.tok) for token in token_stream]


def main():
    token_strings = []
    with open(sys.argv[1], "rt") as f:
        for line in f:
            name = line.rstrip("\n")
            token_strings.append(list(tokenize_name(name)))
    it = iter(token_strings)
    first = next(it)
    length_mismatch = False
    for token_string in it:
        if len(token_string) != len(first):
            length_mismatch = True
    if length_mismatch:
        raise ValueError("Unequal token lengths. Codec unsuitable.")
    token_streams = [list(row) for row in zip(*token_strings)]
    token_streams = [homogenize_token_stream(x) for x in token_streams]
    for token_stream in token_streams:
        print(set(type(x) for x in token_stream))

if __name__ == "__main__":
    main()