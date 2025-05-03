#!/usr/bin/env python3
import string
import struct
import sys
from typing import Iterator

class Token:
    tok: str
    data: bytes

class StringToken(Token):
    def __init__(self, tok: str):
        self.data = tok.encode("ascii")

class DecimalToken(Token):
    def __init__(self, tok: str):
        self.data = struct.pack("<I", int(tok))

class HexaDecimalToken(Token):
    def __init__(self, tok: str):
        self.data = struct.pack("<I", int(tok, 16))

class PunctutationToken(StringToken):
    pass

def classify_token(tok: str) -> Token:
    if tok.isnumeric():
        return DecimalToken(tok)
    if set(tok).issubset(set(string.hexdigits)):
        try:
            return HexaDecimalToken(tok)
        except ValueError:
            pass
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


def main():
    token_strings = []
    with open(sys.argv[1], "rt") as f:
        for line in f:
            name = line.rstrip("\n")
            token_strings.append(list(tokenize_name(name)))
    it = iter(token_strings)
    first = [type(x) for x in next(it)]
    for token_string in it:
        token_types = [type(x) for x in token_string]
        if first != token_types:
            print(f"Mismatch: {first} <-> {token_types}")

if __name__ == "__main__":
    main()