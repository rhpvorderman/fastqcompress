#!/usr/bin/env python3
import argparse
import array
import io
import logging
import string
import struct
import sys
from typing import List, Iterator, Sequence, Tuple, Iterable, BinaryIO

UINT64_MAX = 0xFFFF_FFFF_FFFF_FFFF
UINT32_MAX = 0xFFFF_FFFF
UINT16_MAX = 0xFFFF
UINT8_MAX = 0xFF
INT64_MAX = 9223372036854775807
INT32_MAX = 2147483647
INT16_MAX = 32767
INT8_MAX = 127
INT64_MIN = - INT64_MAX - 1
INT32_MIN = - INT32_MAX - 1
INT16_MIN = - INT16_MAX - 1
INT8_MIN = - INT8_MAX - 1

DECIMAL =      0b0000_0000
LOWER =        0b0000_0001
UPPER =        0b0000_0010
ZERO_PREFIX =  0b0000_0100
PUNCTUATION =  0b0000_1000
DIFF_ENCODED = 0b0001_0000
STRING = UPPER | LOWER

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


def numbers_to_array(numbers: Sequence[int]) -> array.ArrayType:
    number_min = min(numbers)
    number_max = max(numbers)
    if number_min >= 0:
        if number_max > UINT64_MAX:
            raise NotImplementedError("Numbers to big")
        elif number_max > UINT32_MAX:
            array_type = "Q"
        elif number_max > UINT16_MAX:
            array_type = "I"
        elif number_max > UINT8_MAX:
            array_type = "H"
        else:
            array_type = "B"
    else:
        if number_min < INT64_MIN or number_max > INT64_MAX:
            raise NotImplementedError("Numbers to big")
        elif number_min < INT32_MIN or number_max > INT32_MAX:
            array_type = "q"
        elif number_min < INT16_MIN or number_max > INT16_MAX:
            array_type = "i"
        elif number_min < INT8_MIN or number_max > INT8_MAX:
            array_type = "h"
        else:
            array_type = "b"
    return array.array(array_type, numbers)


def array_type_to_itemsize(array_type: str) -> int:
    return {"B": 1, "H": 2, "I": 4, "Q": 8}[array_type.upper()]


def diffcompress(numbers: Iterable[int]) -> Iterator[Tuple[int, Sequence[int]]]:
    it = iter(numbers)
    first_number = next(it)
    previous_number = first_number
    following_diffs = []
    for number in it:
        diff = number - previous_number
        if diff < 0 or diff > 255:
            yield first_number, following_diffs
            first_number = number
            following_diffs = []
        else:
            following_diffs.append(diff)
        previous_number = number
    yield first_number, following_diffs


def diffdecompress(diffcompressed: Iterable[Tuple[int, Sequence[int]]]) -> Iterator[int]:
    for first_number, diffs in diffcompressed:
        yield first_number
        previous_number = first_number
        for diff in diffs:
            number = previous_number + diff
            yield number
            previous_number = number


def pack_diff_encoding(diff_compressed: Iterable[Tuple[int, Sequence[int]]]) -> bytes:
    stream = io.BytesIO()
    diff_compressed = list(diff_compressed)
    start_numbers = [start for start, diffs in diff_compressed]
    start_array = numbers_to_array(start_numbers)
    stream.write(struct.pack("<IB", len(start_array), ord(start_array.typecode)))
    stream.write(start_array.tobytes())
    diffstream = (diffs for start, diffs in diff_compressed)
    for diffs in diffstream:
        arr = numbers_to_array(diffs)
        stream.write(struct.pack("<IB", len(arr), ord(arr.typecode)))
        stream.write(arr.tobytes())
    return stream.getvalue()


def unpack_diff_encoding(stream: BinaryIO) -> Iterator[Tuple[int, Sequence[int]]]:
    start_length, start_tp = struct.unpack("<IB", stream.read(5))
    start_tp = chr(start_tp)
    array_bytes =  array_type_to_itemsize(start_tp) * start_length
    start_numbers = array.array(start_tp)
    start_numbers.frombytes(stream.read(array_bytes))
    for start in start_numbers:
        length, tp = struct.unpack("<IB", stream.read(5))
        array_type = chr(tp)
        array_bytes = array_type_to_itemsize(array_type) * length
        diffs = array.array(array_type)
        diffs.frombytes(stream.read(array_bytes))
        yield start, diffs


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
            array_size = arr.itemsize * len(arr)
            data = arr.typecode.encode("latin-1") + arr.tobytes()
            try:
                diff_compressed_bytes = pack_diff_encoding(diffcompress(arr))
                if array_size > len(diff_compressed_bytes):
                    data = diff_compressed_bytes
                    self.tp |= DIFF_ENCODED
            except ValueError:
                pass
            if self.tp & ZERO_PREFIX:
                length_set = set(len(x) for x in self.tokens)
                if len(length_set) != 1:
                    raise ValueError(f"Zero prefixed numbers should all have the same formatted length. Found {length_set}")
                formatted_length = length_set.pop()
                data = struct.pack("B", formatted_length) + data
        else:
            raise NotImplementedError(f"Unkown token type: {self.tp}")
        header = struct.pack("<BI", self.tp, number_of_tokens)
        return header + data

    @classmethod
    def from_stream(cls, stream: BinaryIO):
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
        if tp & DIFF_ENCODED:
            number_array = diffdecompress(unpack_diff_encoding(stream))
        else:
            array_type = stream.read(1).decode("latin-1")
            item_size = array_type_to_itemsize(array_type)
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


def compress(names: List[str]) -> bytes:
    token_strings = []
    for name in names:
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
    token_sets = []
    for token_stream in token_streams:
        token_sets.append(set(TOK_TYPE_TO_STRING[tok_type] for tok_type, token in token_stream))
    logging.info(f"Token types per column: {token_sets}")
    token_stores = [TokenStore.from_token_stream(token_stream)
                    for token_stream in token_streams]
    homogenized_token_order = [TOK_TYPE_TO_STRING[ts.tp] for ts in token_stores]
    logging.info(f"Homogenized token type order: {homogenized_token_order}")
    all_data = b"".join(ts.to_data() for ts in token_stores)
    return all_data


def decompress(data: bytes) -> Iterator[str]:
    stream = io.BytesIO(data)
    token_stores = []
    while stream.tell() != len(data):
        token_stores.append(TokenStore.from_stream(stream))
    name_chunks = [ts.tokens for ts in token_stores]
    for parts in zip(*name_chunks):
        yield "".join(parts)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("names", help="File with a name on each new line, or compressed file.")
    parser.add_argument("-d", "--decompress", action="store_true")
    parser.add_argument("-v", "--verbose", action="count", default=0,
                        help="If supplied will give information about the found tokens.")
    args = parser.parse_args()
    logger = logging.getLogger()
    logger.setLevel(logging.WARNING - args.verbose * 10)
    if args.decompress:
        with open(args.names, "rb") as f:
            data = f.read()
        for name in decompress(data):
            print(name)
        return

    with open(args.names, "rt") as f:
        name_block = f.read()
    data = compress(name_block.splitlines())
    sys.stdout.buffer.write(data)
    sys.stdout.buffer.flush()
    return


if __name__ == "__main__":
    main()