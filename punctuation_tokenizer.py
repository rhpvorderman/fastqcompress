#!/usr/bin/env python3
import string
import struct
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


if __name__ == "__main__":
    print(list(tokenize_name("D00360:64:HBAP3ADXX:1:1114:18307:86570")))
