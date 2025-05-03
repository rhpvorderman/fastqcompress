#!/usr/bin/env python3
import array
import io
import string
import struct
import sys
from typing import List, Iterator, Tuple

UINT64_MAX = 0xFFFF_FFFF_FFFF_FFFF
UINT32_MAX = 0xFFFF_FFFF
UINT16_MAX = 0xFFFF
UINT8_MAX = 0xFF

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


def numbers_to_array(numbers: List[int]) -> array.ArrayType:
    assert min(numbers) >= 0
    number_max = max(numbers)
    if number_max > UINT64_MAX:
        raise NotImplementedError("Numbers to big")
    if number_max > UINT32_MAX:
        array_type = "Q"
    elif number_max > UINT16_MAX:
        array_type = "I"
    elif number_max > UINT8_MAX:
        array_type = "H"
    else:
        array_type = "B"
    return array.array(array_type, numbers)


class TokenStore:
    tp: int
    tokens: List[str]

    def __init__(self, tp: int, tokens: List[str]):
        self.tp = tp
        self.tokens = tokens

    def to_data(self) -> bytes:
        number_of_tokens = len(self.tokens)
        if self.tp & PUNCTUATION:
            token_set = set(self.tokens)
            if len(token_set) != 1:
                raise NotImplementedError(
                    f"PUNCTUATION separators should be the same: {token_set}")
            separator = token_set.pop()
            if len(separator) != 1:
                raise RuntimeError(
                    f"Programmer messed up! Separator length is not 1: {separator}")
            data = separator.encode("latin-1")
        elif self.tp & STRING == STRING:
            all_string = "\x00".join(self.tokens)
            number_of_tokens = len(all_string)
            data = (all_string.encode("latin_1"))
        elif self.tp & LOWER or self.tp & UPPER or self.tp == DECIMAL or self.tp == ZERO_PREFIX:
            if self.tp & LOWER or self.tp & UPPER:
                numbers = [int(x, 16) for x in self.tokens]
            else:
                numbers = [int(x, 10) for x in self.tokens]
            arr = numbers_to_array(numbers)
            data = arr.typecode.encode("latin-1") + arr.tobytes()
            if self.tp & ZERO_PREFIX:
                length_set = set(len(x) for x in self.tokens)
                if len(length_set) != 0:
                    raise ValueError("Zero prefixed numbers should all have the same formatted length.")
                formatted_length = length_set.pop()
                data = struct.pack("B", formatted_length) + data
        else:
            raise NotImplementedError(f"Unkown token type: {self.tp}")
        header = struct.pack("<BI", self.tp, number_of_tokens)
        return header + data

    @classmethod
    def from_stream(cls, stream: io.BufferedIOBase):
        tp, number_stored = struct.unpack("<BI", stream.read(5))
        if tp & PUNCTUATION:
            character = stream.read(1).decode("latin-1")
            return cls(tp, [character for _ in range(number_stored)])
        if tp & STRING == STRING:
            all_strings = stream.read(number_stored).decode("latin-1")
            return cls(tp, all_strings.split("\x00"))
        # The rest is numbers
        if tp & UPPER:
            format_code = "X"
        elif tp & LOWER:
            format_code = "x"
        else:
            format_code = "d"
        if tp & ZERO_PREFIX:
            formatted_length, = struct.unpack("B", stream.read(1))
            format_code = f"0{formatted_length}" + format_code
        array_type = stream.read(1).decode("latin-1")
        if array_type == "B":
            item_size = 1
        elif array_type == "H":
            item_size = 2
        elif array_type == "I":
            item_size = 4
        elif array_type == "Q":
            item_size = 8
        else:
            raise ValueError(f"Unrecognized array_type: {array_type}")
        bytes_stored = number_stored * item_size
        array_bytes = stream.read(bytes_stored)
        number_array = array.array(array_type)
        number_array.frombytes(array_bytes)

        tokens = [f"%{format_code}" % number for number in number_array]
        return cls(tp, tokens)

    @classmethod
    def from_token_stream(cls, token_stream: List[tuple[int, str]]):
        combined = 0
        tokens = []
        for tp, token in token_stream:
            combined |= tp
            tokens.append(token)
        return cls(combined, tokens)


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
    token_stores = [TokenStore.from_token_stream(token_stream)
                    for token_stream in token_streams]
    all_data = b"".join(ts.to_data() for ts in token_stores)
    sys.stdout.buffer.write(all_data)


if __name__ == "__main__":
    main()