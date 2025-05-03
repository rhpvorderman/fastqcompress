#!/usr/bin/env python3
import string
import sys
from typing import List, Iterator, Tuple

UPPER =       0b0000010
LOWER =       0b0000001
DECIMAL =     0b0000000
ZERO_PREFIX = 0b0000100
STRING = UPPER | LOWER
PUNCTUATION = 0b0001000
TOK_TYPE_TO_STRING = [
    "DECIMAL",
    "LOWERHEXADECIMAL",
    "UPPER_HEXADECIMAL",
    "STRING",
    "DECIMAL0",
    "LOWERHEXADECIMAL0",
    "UPPERGEXADECIMAL0",
    "STRING",
    "PUNCTUATION",
]
TOK_TYPE_TO_STRING[UPPER] = "UPPERHEXADECIMAL"
TOK_TYPE_TO_STRING[LOWER] = "LOWERHEXADECIMAL"
TOK_TYPE_TO_STRING[DECIMAL] = "DECIMAL"


def classify_token(tok: str) -> int:
    tp = 0
    if tok[0] == '0':
        tp |= ZERO_PREFIX
    for char in tok:
        if char in string.digits:
            tp |= DECIMAL
        elif char in string.hexdigits:
            if char.isupper():
                tp |= UPPER
            else:
                tp |= LOWER
        else:
            return STRING
    return tp


def tokenize_name(name: str) -> Iterator[Tuple[int, str]]:
    start = 0
    index = 0
    end = len(name)
    while index < end:
        if name[index] in string.punctuation:
            if index > start:
                token = name[start:index]
                yield classify_token(token), token
            yield PUNCTUATION, name[index]
            start = index + 1
        index += 1
    if index > start:
        token = name[start:index]
        yield classify_token(token), token


def homogenize_token_stream(token_stream: List[Tuple[int, str]]):
    combined = 0
    for tp, token in token_stream:
        combined |= tp
    return [(combined, token) for tp, token in token_stream]


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
    for token_stream in token_streams:
        print(set(TOK_TYPE_TO_STRING[tp] for tp, token in token_stream))
    token_streams = [homogenize_token_stream(x) for x in token_streams]
    print([TOK_TYPE_TO_STRING[token_stream[0][0]] for token_stream in token_streams])


if __name__ == "__main__":
    main()