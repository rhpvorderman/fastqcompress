#!/usr/bin/env python3
import array
import collections
import sys

import dnaio

def qual_diff_encode(qualities: str) -> bytes:
    qualities_raw = qualities.encode('ascii')
    previous_phred = qualities_raw[0]
    assert previous_phred >= 33
    assert previous_phred <= 126
    encoded_diffs = array.array("b", bytes(len(qualities)))
    encoded_diffs[0] = previous_phred
    for i, phred in enumerate(qualities_raw[1:], start=1):
        assert phred >= 33
        assert phred <= 126
        diff = phred - previous_phred
        previous_phred = phred
        encoded_diffs[i] = diff
    return encoded_diffs


def qual_diff_decode(encoded: str):
    pass

if __name__ == "__main__":
    counter = collections.Counter()
    with dnaio.open(sys.argv[1]) as f:
        for record in f:
            counter.update(qual_diff_encode(record.qualities))
    print(len(counter))
    for diff, count in counter.most_common():
        print(f"{diff}\t{count}")

