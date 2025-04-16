#!/usr/bin/env python3

import argparse
import math


def find_ranges(data: bytes, max_diff=15):
    minimum = data[0]
    maximum = data[0]
    range_start = 0
    i = 0
    for i, c in enumerate(data):
        minimum = min(c, minimum)
        maximum = max(c, maximum)
        if (minimum + max_diff) < maximum:
            yield range_start, i
            range_start = i
            minimum = c
            maximum = c

    yield range_start, len(data)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("quals")
    parser.add_argument("-e", "--encode-bits", type=int, default=4)
    args = parser.parse_args()
    encoded_length = 0
    encode_bits = args.encode_bits
    max_diff = 2 ** encode_bits - 1
    print(max_diff)
    with open(args.quals, "rb") as f:
        for line in f:
            quals = line.rstrip(b"\n")
            for start, stop in find_ranges(quals, max_diff):
                length = stop - start
                if length < 6:
                    encoded_length += length
                else:
                    while length > 0:
                        encode_length = min(length, 256)
                        encoded_length += math.ceil(2 + (encode_length * encode_bits / 8))
                        length -= encode_length
        print(f.tell())
    print(encoded_length)


if __name__ == "__main__":
    main()