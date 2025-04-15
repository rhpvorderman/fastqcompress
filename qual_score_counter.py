#!/usr/bin/env python3

import sys
from collections import Counter

import dnaio


if __name__ == "__main__":
    counter = Counter()
    with dnaio.open(sys.argv[1], open_threads=4) as f:

        for record in f:
            counter.update(record.qualities)
    print(len(counter))
    for phred, count in counter.most_common():
        print(f"{ord(phred) - 33}\t{count}")
